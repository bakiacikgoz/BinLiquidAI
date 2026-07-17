from __future__ import annotations

from copy import deepcopy
from typing import Any

from imperaos.artifacts.errors import ArtifactDomainError, ArtifactErrorCode
from imperaos.artifacts.models import ArtifactKind


def require_scoped_replacement(
    kind: ArtifactKind,
    base: dict[str, Any],
    proposed: dict[str, Any],
    selection: dict[str, Any],
) -> None:
    if selection.get("kind") != kind.value:
        _deny()
    validators = {
        ArtifactKind.DOCUMENT: _document,
        ArtifactKind.FORM: _json_pointer,
        ArtifactKind.CODE: _code,
        ArtifactKind.FLOW: _flow,
        ArtifactKind.SPREADSHEET: _spreadsheet,
        ArtifactKind.CANVAS: _canvas,
        ArtifactKind.SLIDES: _slides,
    }
    try:
        valid = validators[kind](base, proposed, selection)
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        _deny()


def _same_except(base: dict[str, Any], proposed: dict[str, Any], key: str) -> bool:
    left, right = deepcopy(base), deepcopy(proposed)
    left.pop(key, None)
    right.pop(key, None)
    return left == right


def _document(base: dict[str, Any], proposed: dict[str, Any], selection: dict[str, Any]) -> bool:
    ids = set(selection["blockIds"])
    left, right = base["blocks"], proposed["blocks"]
    return (
        bool(ids)
        and _same_except(base, proposed, "blocks")
        and ids.issubset({item.get("id") for item in left})
        and ids.issubset({item.get("id") for item in right})
        and [item for item in left if item.get("id") not in ids]
        == [item for item in right if item.get("id") not in ids]
    )


def _json_pointer(
    base: dict[str, Any], proposed: dict[str, Any], selection: dict[str, Any]
) -> bool:
    left, right = deepcopy(base), deepcopy(proposed)
    for pointer in selection["fieldPaths"]:
        parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]
        for root in (left, right):
            parent: Any = root
            for part in parts[:-1]:
                parent = parent[int(part)] if isinstance(parent, list) else parent[part]
            if isinstance(parent, list):
                parent[int(parts[-1])] = "__ARTIFACT_SELECTED__"
            else:
                parent[parts[-1]] = "__ARTIFACT_SELECTED__"
    return left == right


def _code(base: dict[str, Any], proposed: dict[str, Any], selection: dict[str, Any]) -> bool:
    if not _same_except(base, proposed, "text"):
        return False
    text = base["text"]
    start = _line_offset(text, selection["startLineNumber"], selection["startColumn"])
    end = _line_offset(text, selection["endLineNumber"], selection["endColumn"])
    return proposed["text"].startswith(text[:start]) and proposed["text"].endswith(text[end:])


def _line_offset(text: str, line: int, column: int) -> int:
    lines = text.splitlines(keepends=True)
    if line > len(lines):
        raise ValueError
    return sum(len(value) for value in lines[: line - 1]) + column - 1


def _flow(base: dict[str, Any], proposed: dict[str, Any], selection: dict[str, Any]) -> bool:
    if not _same_except(_without(base, "nodes"), _without(proposed, "nodes"), "edges"):
        return False
    node_ids, edge_ids = set(selection.get("nodeIds", [])), set(selection.get("edgeIds", []))
    return (
        [item for item in base["nodes"] if item.get("id") not in node_ids]
        == [item for item in proposed["nodes"] if item.get("id") not in node_ids]
        and [item for item in base["edges"] if item.get("id") not in edge_ids]
        == [item for item in proposed["edges"] if item.get("id") not in edge_ids]
    )


def _spreadsheet(base: dict[str, Any], proposed: dict[str, Any], selection: dict[str, Any]) -> bool:
    if not _same_except(base, proposed, "sheets"):
        return False
    sheet_id = selection["sheetId"]
    allowed = _expanded_ranges(selection["ranges"])
    return _strip_cells(base["sheets"], sheet_id, allowed) == _strip_cells(
        proposed["sheets"], sheet_id, allowed
    )


def _canvas(base: dict[str, Any], proposed: dict[str, Any], selection: dict[str, Any]) -> bool:
    ids = set(selection["objectIds"])
    key = "objects" if "objects" in base else "shapes"
    return _same_except(base, proposed, key) and [
        item for item in base[key] if item.get("id") not in ids
    ] == [item for item in proposed[key] if item.get("id") not in ids]


def _slides(base: dict[str, Any], proposed: dict[str, Any], selection: dict[str, Any]) -> bool:
    if not _same_except(base, proposed, "slides"):
        return False
    slide_id, element_id = selection["slideId"], selection.get("elementId")
    if element_id is None:
        return [item for item in base["slides"] if item.get("id") != slide_id] == [
            item for item in proposed["slides"] if item.get("id") != slide_id
        ]
    left, right = deepcopy(base["slides"]), deepcopy(proposed["slides"])
    for slides in (left, right):
        slide = next(item for item in slides if item.get("id") == slide_id)
        slide["elements"] = [item for item in slide["elements"] if item.get("id") != element_id]
    return left == right


def _without(value: dict[str, Any], key: str) -> dict[str, Any]:
    result = deepcopy(value)
    result.pop(key, None)
    return result


def _strip_cells(
    sheets: list[dict[str, Any]], sheet_id: str, allowed: set[str]
) -> list[dict[str, Any]]:
    result = deepcopy(sheets)
    sheet = next(item for item in result if item.get("id") == sheet_id)
    sheet["cells"] = {
        address: value
        for address, value in sheet.get("cells", {}).items()
        if address not in allowed
    }
    return result


def _expanded_ranges(ranges: list[str]) -> set[str]:
    result: set[str] = set()
    for value in ranges:
        start, _, end = value.partition(":")
        end = end or start
        start_col, start_row = _cell(start)
        end_col, end_row = _cell(end)
        if (end_row - start_row + 1) * (end_col - start_col + 1) > 10_000:
            raise ValueError
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                result.add(f"{_column(col)}{row}")
    return result


def _cell(value: str) -> tuple[int, int]:
    letters = "".join(char for char in value if char.isalpha())
    row = int(value[len(letters) :])
    col = 0
    for char in letters:
        col = col * 26 + ord(char) - 64
    return col, row


def _column(value: int) -> str:
    result = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _deny() -> None:
    raise ArtifactDomainError(
        ArtifactErrorCode.ARTIFACT_PERMISSION_DENIED,
        "artifact proposal changes content outside the trusted selection",
        details={"reasonCode": "ARTIFACT_PROPOSAL_SCOPE_EXCEEDED"},
    )
