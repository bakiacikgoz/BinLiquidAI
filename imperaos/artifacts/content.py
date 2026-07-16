from __future__ import annotations

import json
import re
from typing import Annotated, ClassVar, Literal

from pydantic import Field, JsonValue, StringConstraints, field_validator, model_validator

from imperaos.artifacts.errors import ArtifactDomainError, ArtifactErrorCode
from imperaos.artifacts.models import (
    ARTIFACT_CONTENT_LIMITS_BYTES,
    ArtifactKind,
    ArtifactModel,
    BoundedId,
)


class ArtifactContentModel(ArtifactModel):
    schema_version: Literal[1] = 1


def _contains_remote_url(value: JsonValue) -> bool:
    if isinstance(value, str):
        return value.strip().lower().startswith(("http://", "https://", "//"))
    if isinstance(value, dict):
        return any(_contains_remote_url(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_remote_url(item) for item in value)
    return False


class DocumentContentV1(ArtifactContentModel):
    kind: Literal["document"] = "document"
    language: Annotated[
        str, StringConstraints(min_length=2, max_length=16, pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
    ]
    page_mode: Literal["document", "paginated"] = "document"
    blocks: list[dict[str, JsonValue]] = Field(max_length=10_000)

    @field_validator("blocks")
    @classmethod
    def reject_remote_content(cls, value: list[dict[str, JsonValue]]) -> list[dict[str, JsonValue]]:
        if _contains_remote_url(value):
            raise ValueError("document contains a remote URL")
        return value


_FORM_ALLOWED_KEYS = {
    "$schema",
    "$ref",
    "$defs",
    "definitions",
    "title",
    "description",
    "type",
    "properties",
    "required",
    "enum",
    "const",
    "oneOf",
    "items",
    "additionalProperties",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minItems",
    "maxItems",
    "uniqueItems",
    "pattern",
    "format",
    "default",
    "examples",
}
_FORM_TYPES = {"object", "array", "string", "number", "integer", "boolean", "null"}
_FORM_FORMATS = {"date", "date-time", "email", "hostname", "ipv4", "ipv6", "uri-reference", "uuid"}
_NESTED_QUANTIFIER = re.compile(r"\([^)]*[+*][^)]*\)[+*{]")
_FORM_MAX_FIELDS = 100
_FORM_MAX_DEPTH = 6
_FORM_MAX_BYTES = 512 * 1024


def _validate_form_schema(schema: dict[str, JsonValue]) -> None:
    field_count = 0

    def visit(node: JsonValue, depth: int) -> None:
        nonlocal field_count
        if depth > _FORM_MAX_DEPTH:
            raise ValueError(f"form schema depth exceeds {_FORM_MAX_DEPTH}")
        if not isinstance(node, dict):
            return
        unknown = set(node) - _FORM_ALLOWED_KEYS
        if unknown:
            raise ValueError(f"form schema contains unsupported keys: {sorted(unknown)}")
        raw_ref = node.get("$ref")
        if isinstance(raw_ref, str) and not raw_ref.startswith(("#/definitions/", "#/$defs/")):
            raise ValueError("remote refs are forbidden")
        raw_type = node.get("type")
        if isinstance(raw_type, str) and raw_type not in _FORM_TYPES:
            raise ValueError(f"unsupported form type: {raw_type}")
        raw_format = node.get("format")
        if isinstance(raw_format, str) and raw_format not in _FORM_FORMATS:
            raise ValueError(f"unsupported form format: {raw_format}")
        pattern = node.get("pattern")
        if isinstance(pattern, str):
            if len(pattern) > 256 or _NESTED_QUANTIFIER.search(pattern):
                raise ValueError("unsafe pattern in form schema")
            try:
                re.compile(pattern)
            except re.error as error:
                raise ValueError("invalid pattern in form schema") from error
        one_of = node.get("oneOf")
        if isinstance(one_of, list):
            if len(one_of) > 20:
                raise ValueError("form oneOf exceeds 20 branches")
            for item in one_of:
                visit(item, depth + 1)
        properties = node.get("properties")
        if isinstance(properties, dict):
            field_count += len(properties)
            if field_count > _FORM_MAX_FIELDS:
                raise ValueError(f"form schema exceeds {_FORM_MAX_FIELDS} fields")
            for child in properties.values():
                visit(child, depth + 1)
        for definitions_key in ("definitions", "$defs"):
            definitions = node.get(definitions_key)
            if isinstance(definitions, dict):
                for child in definitions.values():
                    visit(child, depth + 1)
        items = node.get("items")
        if isinstance(items, dict):
            visit(items, depth + 1)
        additional = node.get("additionalProperties")
        if isinstance(additional, dict):
            raise ValueError("schema-valued additionalProperties is not allowed")

    serialized = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    if len(serialized.encode("utf-8")) > _FORM_MAX_BYTES:
        raise ValueError(f"form schema exceeds {_FORM_MAX_BYTES} bytes")
    visit(schema, 1)


_UI_KEYS = {"ui:widget", "ui:options", "ui:placeholder", "ui:help", "ui:title", "ui:description"}
_UI_WIDGETS = {"text", "textarea", "select", "checkbox", "radio", "date", "hidden"}
_UI_FORBIDDEN_KEYS = {"src", "url", "href", "html", "dangerouslysetinnerhtml", "script"}


def _validate_ui_schema(value: JsonValue) -> None:
    if isinstance(value, str) and _contains_remote_url(value):
        raise ValueError("uiSchema contains a remote URL")
    if isinstance(value, list):
        for item in value:
            _validate_ui_schema(item)
        return
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        lowered = key.lower()
        if key.startswith("ui:") and key not in _UI_KEYS:
            raise ValueError(f"uiSchema contains unsupported directive: {key}")
        if lowered in _UI_FORBIDDEN_KEYS or lowered.startswith("on"):
            raise ValueError(f"uiSchema contains forbidden key: {key}")
        if key == "ui:widget" and item not in _UI_WIDGETS:
            raise ValueError(f"uiSchema contains unsupported widget: {item}")
        _validate_ui_schema(item)


class FormBehavior(ArtifactModel):
    submit_mode: Literal["explicit"] = "explicit"
    external_continuation: Literal["deny", "approval_required"] = "deny"


class FormContentV1(ArtifactContentModel):
    kind: Literal["form"] = "form"
    json_schema: dict[str, JsonValue] = Field(alias="schema")
    ui_schema: dict[str, JsonValue] = Field(default_factory=dict)
    behavior: FormBehavior = Field(default_factory=FormBehavior)
    sensitive_paths: list[
        Annotated[str, StringConstraints(pattern=r"^/(?:[^/~]|~[01])+(?:/(?:[^/~]|~[01])+)*$")]
    ] = Field(
        default_factory=list,
        max_length=100,
    )

    @field_validator("json_schema")
    @classmethod
    def validate_schema(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        _validate_form_schema(value)
        return value

    @field_validator("ui_schema")
    @classmethod
    def validate_ui_schema(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        _validate_ui_schema(value)
        return value


class CodeContentV1(ArtifactContentModel):
    kind: Literal["code"] = "code"
    filename: Annotated[
        str,
        StringConstraints(min_length=1, max_length=255, pattern=r"^[^/\\:\x00]+$", strict=True),
    ]
    language: Annotated[
        str, StringConstraints(min_length=1, max_length=64, pattern=r"^[a-z0-9_+-]+$")
    ]
    text: Annotated[str, StringConstraints(max_length=5 * 1024 * 1024, strict=True)]
    line_ending: Literal["lf", "crlf"] = "lf"
    execution_policy: Literal["deny"] = "deny"


class FlowPosition(ArtifactModel):
    x: float
    y: float


class FlowNode(ArtifactModel):
    id: BoundedId
    type: Literal["input", "output", "process", "decision", "note", "group", "artifact"]
    position: FlowPosition
    data: dict[str, JsonValue] = Field(default_factory=dict)


class FlowEdge(ArtifactModel):
    id: BoundedId
    source: BoundedId
    target: BoundedId
    label: Annotated[str, StringConstraints(max_length=200, strict=True)] | None = None


class FlowViewport(ArtifactModel):
    x: float
    y: float
    zoom: float = Field(ge=0.05, le=8.0)


class FlowContentV1(ArtifactContentModel):
    kind: Literal["flow"] = "flow"
    nodes: list[FlowNode] = Field(max_length=5_000)
    edges: list[FlowEdge] = Field(max_length=10_000)
    viewport: FlowViewport

    @model_validator(mode="after")
    def validate_graph(self) -> FlowContentV1:
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("flow contains duplicate node ids")
        edge_ids = [edge.id for edge in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("flow contains duplicate edge ids")
        known = set(node_ids)
        for edge in self.edges:
            if edge.source not in known:
                raise ValueError(f"flow edge has unknown source: {edge.source}")
            if edge.target not in known:
                raise ValueError(f"flow edge has unknown target: {edge.target}")
        return self


class SpreadsheetCell(ArtifactModel):
    value: JsonValue
    style: dict[str, JsonValue] = Field(default_factory=dict)


class SpreadsheetSheet(ArtifactModel):
    id: BoundedId
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    cells: dict[str, SpreadsheetCell] = Field(default_factory=dict)
    columns: list[dict[str, JsonValue]] = Field(default_factory=list, max_length=16_384)

    @field_validator("cells")
    @classmethod
    def validate_cell_addresses(
        cls, value: dict[str, SpreadsheetCell]
    ) -> dict[str, SpreadsheetCell]:
        invalid = [key for key in value if re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]{0,6}", key) is None]
        if invalid:
            raise ValueError(f"invalid spreadsheet cell address: {invalid[0]}")
        return value


class SpreadsheetContentV1(ArtifactContentModel):
    kind: Literal["spreadsheet"] = "spreadsheet"
    calculation_mode: Literal["disabled"] = "disabled"
    sheets: list[SpreadsheetSheet] = Field(min_length=1, max_length=1_024)

    @model_validator(mode="after")
    def validate_workbook(self) -> SpreadsheetContentV1:
        sheet_ids = [sheet.id for sheet in self.sheets]
        if len(sheet_ids) != len(set(sheet_ids)):
            raise ValueError("spreadsheet contains duplicate sheet ids")
        non_empty_cells = sum(len(sheet.cells) for sheet in self.sheets)
        if non_empty_cells > 100_000:
            raise ValueError("spreadsheet exceeds 100000 non-empty cells")
        return self


class CanvasContentV1(ArtifactContentModel):
    kind: Literal["canvas"] = "canvas"
    snapshot: dict[str, JsonValue]
    asset_ids: list[BoundedId] = Field(default_factory=list, max_length=10_000)
    embeds: Literal["deny"] = "deny"
    remote_assets: Literal["deny"] = "deny"

    @field_validator("snapshot")
    @classmethod
    def validate_snapshot(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if _contains_remote_url(value):
            raise ValueError("canvas snapshot contains a remote URL")
        return value


class SlidesContentV1(ArtifactContentModel):
    kind: Literal["slides"] = "slides"
    theme: dict[str, JsonValue] = Field(default_factory=dict)
    slides: list[dict[str, JsonValue]] = Field(max_length=200)
    allowed_element_types: ClassVar[set[str]] = {"text", "image", "shape", "line", "table", "chart"}

    @field_validator("slides")
    @classmethod
    def validate_slides(cls, value: list[dict[str, JsonValue]]) -> list[dict[str, JsonValue]]:
        ids: set[str] = set()
        for slide in value:
            slide_id = slide.get("id")
            if not isinstance(slide_id, str) or not slide_id or slide_id in ids:
                raise ValueError("slides require unique string ids")
            ids.add(slide_id)
            elements = slide.get("elements", [])
            if not isinstance(elements, list):
                raise ValueError("slide elements must be an array")
            element_ids: set[str] = set()
            for element in elements:
                if not isinstance(element, dict):
                    raise ValueError("slide element must be an object")
                element_id = element.get("id")
                if not isinstance(element_id, str) or not element_id or element_id in element_ids:
                    raise ValueError("slide elements require unique string ids")
                element_ids.add(element_id)
                if element.get("type") not in cls.allowed_element_types:
                    raise ValueError(f"unsupported slide element type: {element.get('type')}")
                if _contains_remote_url(element):
                    raise ValueError("slide element contains a remote URL")
        return value


ArtifactContent = (
    DocumentContentV1
    | FormContentV1
    | CodeContentV1
    | FlowContentV1
    | SpreadsheetContentV1
    | CanvasContentV1
    | SlidesContentV1
)

ARTIFACT_CONTENT_MODEL_BY_KIND: dict[ArtifactKind, type[ArtifactContentModel]] = {
    ArtifactKind.DOCUMENT: DocumentContentV1,
    ArtifactKind.FORM: FormContentV1,
    ArtifactKind.CODE: CodeContentV1,
    ArtifactKind.FLOW: FlowContentV1,
    ArtifactKind.SPREADSHEET: SpreadsheetContentV1,
    ArtifactKind.CANVAS: CanvasContentV1,
    ArtifactKind.SLIDES: SlidesContentV1,
}


class SafeJsonPatchOperation(ArtifactModel):
    op: Literal["add", "remove", "replace", "test"]
    path: Annotated[
        str, StringConstraints(min_length=1, max_length=512, pattern=r"^/", strict=True)
    ]
    value: JsonValue | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        segments = value[1:].split("/")
        decoded = [segment.replace("~1", "/").replace("~0", "~") for segment in segments]
        if any(segment in {"__proto__", "prototype", "constructor"} for segment in decoded):
            raise ValueError("unsafe JSON Pointer segment")
        if any("~" in segment.replace("~0", "").replace("~1", "") for segment in segments):
            raise ValueError("invalid JSON Pointer escape")
        return value

    @model_validator(mode="after")
    def validate_value_presence(self) -> SafeJsonPatchOperation:
        if self.op in {"add", "replace", "test"} and "value" not in self.model_fields_set:
            raise ValueError(f"{self.op} operation requires value")
        if self.op == "remove" and "value" in self.model_fields_set:
            raise ValueError("remove operation cannot include value")
        return self


class SafeJsonPatch(ArtifactModel):
    operations: list[SafeJsonPatchOperation] = Field(min_length=1, max_length=100)


def validate_artifact_content(kind: ArtifactKind, payload: object) -> ArtifactContentModel:
    model = ARTIFACT_CONTENT_MODEL_BY_KIND[kind]
    content = model.model_validate(payload)
    serialized = json.dumps(
        content.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    limit = ARTIFACT_CONTENT_LIMITS_BYTES[kind]
    if len(serialized) > limit:
        raise ArtifactDomainError(
            ArtifactErrorCode.ARTIFACT_CONTENT_TOO_LARGE,
            f"{kind.value} content exceeds {limit} bytes",
            details={"kind": kind.value, "limitBytes": limit, "observedBytes": len(serialized)},
        )
    return content
