from __future__ import annotations

import re
from pathlib import Path

from binliquid.computer_use.models import (
    ActionCategory,
    BrowserTaskFamily,
    ComputerUseMode,
    ProposedAction,
    RiskClass,
    TargetDescriptor,
)

_QUOTED = r'"([^"]+)"'


def parse_prompt_to_actions(
    *,
    prompt: str,
    mode: ComputerUseMode,
) -> tuple[BrowserTaskFamily, list[ProposedAction]]:
    actions: list[ProposedAction] = []
    chunks = [item.strip() for item in re.split(r"[;\n]+", prompt) if item.strip()]
    for index, chunk in enumerate(chunks, start=1):
        actions.append(_parse_line(index=index, line=chunk, mode=mode))
    if not actions:
        raise ValueError("computer-use prompt produced no executable actions")
    return BrowserTaskFamily.AUTOMATION_SEQUENCE, actions


def _parse_line(*, index: int, line: str, mode: ComputerUseMode) -> ProposedAction:
    lowered = line.lower().strip()
    if lowered.startswith("launch "):
        app_name = _strip_quotes(line[7:])
        return _desktop_action(
            index=index,
            action_id="launch_app",
            app_name=app_name,
            expected_effect=f"Launch and foreground {app_name}.",
            mode=mode,
            category=ActionCategory.NAVIGATION,
            risk=RiskClass.LOW,
        )
    if lowered.startswith("focus "):
        app_name = _strip_quotes(line[6:])
        return _desktop_action(
            index=index,
            action_id="focus_window",
            app_name=app_name,
            expected_effect=f"Focus the active window for {app_name}.",
            mode=mode,
            category=ActionCategory.NAVIGATION,
            risk=RiskClass.LOW,
        )
    if lowered.startswith("open "):
        url = _strip_quotes(line[5:])
        return _browser_action(
            index=index,
            action_id="open_url",
            selector="document",
            expected_effect=f"Open {url}.",
            mode=mode,
            url=url,
            category=ActionCategory.NAVIGATION,
            risk=RiskClass.LOW,
            verification_kind="url",
            verification_value=url,
        )
    if lowered.startswith("new_tab "):
        url = _strip_quotes(line[8:])
        return _browser_action(
            index=index,
            action_id="switch_tab",
            selector="document",
            expected_effect=f"Open a new tab for {url}.",
            mode=mode,
            url=url,
            category=ActionCategory.NAVIGATION,
            risk=RiskClass.LOW,
            verification_kind="url",
            verification_value=url,
            new_tab=True,
        )
    if lowered.startswith("click "):
        selector = _extract_first_quoted(line)
        if selector is None:
            raise ValueError(f"click action requires a quoted selector: {line}")
        return _browser_action(
            index=index,
            action_id="click",
            selector=selector,
            expected_effect=f"Click {selector}.",
            mode=mode,
            category=ActionCategory.MUTATION,
            risk=_risk_for_selector(selector),
            verification_kind="selector_present",
            verification_value=selector,
        )
    if lowered.startswith("type "):
        match = re.match(rf'type {_QUOTED} into {_QUOTED}$', line, flags=re.IGNORECASE)
        if match is None:
            raise ValueError(f'type action must match: type "text" into "selector": {line}')
        text, selector = match.groups()
        return _browser_action(
            index=index,
            action_id="type_text",
            selector=selector,
            expected_effect=f"Type text into {selector}.",
            mode=mode,
            category=ActionCategory.INPUT,
            risk=RiskClass.MEDIUM,
            parameters={"text": text},
            verification_kind="value",
            verification_value=text,
        )
    if lowered.startswith("select "):
        match = re.match(rf'select {_QUOTED} in {_QUOTED}$', line, flags=re.IGNORECASE)
        if match is None:
            raise ValueError(f'select action must match: select "value" in "selector": {line}')
        value, selector = match.groups()
        return _browser_action(
            index=index,
            action_id="select_option",
            selector=selector,
            expected_effect=f"Select {value} in {selector}.",
            mode=mode,
            category=ActionCategory.INPUT,
            risk=RiskClass.MEDIUM,
            parameters={"value": value},
            verification_kind="value",
            verification_value=value,
        )
    if lowered.startswith("scroll "):
        match = re.match(
            rf'scroll (?:(?P<amount>-?\d+)|{_QUOTED} to (?P<selector_amount>-?\d+))$',
            line,
            flags=re.IGNORECASE,
        )
        if match is None:
            raise ValueError(
                'scroll action must match either: scroll 400 or scroll "#selector" to 400'
            )
        selector = match.group(2) or "window"
        amount = match.group("amount") or match.group("selector_amount") or "0"
        return _browser_action(
            index=index,
            action_id="scroll",
            selector=selector,
            expected_effect=f"Scroll {selector} to {amount}.",
            mode=mode,
            category=ActionCategory.NAVIGATION,
            risk=RiskClass.LOW,
            parameters={"amount": int(amount)},
            verification_kind="scroll",
            verification_value=str(amount),
        )
    if lowered.startswith("upload "):
        match = re.match(rf'upload {_QUOTED} to {_QUOTED}$', line, flags=re.IGNORECASE)
        if match is None:
            raise ValueError(
                f'upload action must match: upload "/path/file" to "selector": {line}'
            )
        path, selector = match.groups()
        resolved = str(Path(path).expanduser())
        return _browser_action(
            index=index,
            action_id="upload_file",
            selector=selector,
            expected_effect=f"Upload {resolved} using {selector}.",
            mode=mode,
            category=ActionCategory.FILE_OPS,
            risk=RiskClass.MEDIUM,
            parameters={"path": resolved},
            verification_kind="file_selected",
            verification_value=Path(resolved).name,
        )
    if lowered.startswith("download "):
        match = re.match(
            rf'download {_QUOTED}(?: to {_QUOTED})?$',
            line,
            flags=re.IGNORECASE,
        )
        if match is None:
            raise ValueError(
                'download action must match: download "selector" or download "selector" '
                f'to "/path": {line}'
            )
        selector, output = match.groups()
        parameters: dict[str, str] = {}
        if output:
            parameters["output_path"] = str(Path(output).expanduser())
        return _browser_action(
            index=index,
            action_id="download_file",
            selector=selector,
            expected_effect=f"Download the file exposed by {selector}.",
            mode=mode,
            category=ActionCategory.FILE_OPS,
            risk=RiskClass.MEDIUM,
            parameters=parameters,
            verification_kind="download",
            verification_value=parameters.get("output_path", ""),
        )
    if lowered.startswith("wait "):
        seconds = _strip_quotes(line[5:])
        return _browser_action(
            index=index,
            action_id="wait",
            selector="document",
            expected_effect=f"Wait for {seconds} seconds.",
            mode=mode,
            category=ActionCategory.READ_ONLY,
            risk=RiskClass.LOW,
            parameters={"seconds": float(seconds)},
        )

    raise ValueError(f"unsupported computer-use action: {line}")


def _browser_action(
    *,
    index: int,
    action_id: str,
    selector: str,
    expected_effect: str,
    mode: ComputerUseMode,
    category: ActionCategory,
    risk: RiskClass,
    url: str = "about:blank",
    parameters: dict[str, object] | None = None,
    verification_kind: str | None = None,
    verification_value: str | None = None,
    new_tab: bool = False,
) -> ProposedAction:
    parameters = dict(parameters or {})
    if new_tab:
        parameters["new_tab"] = True
    if action_id == "open_url" or new_tab:
        parameters["url"] = url
    return ProposedAction(
        action_id=action_id,
        category=category,
        risk_class=risk,
        target_descriptor=TargetDescriptor(
            target_ref=selector if selector != "document" else url,
            window_identity="browser:safari:front",
            app_identity="browser:safari",
            selector_source="dom",
            selector=selector,
            expected_effect=expected_effect,
            current_url=url,
        ),
        window_identity="browser:safari:front",
        app_identity="browser:safari",
        selector_source="dom",
        expected_effect=expected_effect,
        approval_required=mode == ComputerUseMode.STEP_APPROVAL
        or risk in {RiskClass.HIGH, RiskClass.CRITICAL},
        dry_run_preview=expected_effect,
        parameters=parameters,
        verification_kind=verification_kind,
        verification_value=verification_value,
    )


def _desktop_action(
    *,
    index: int,
    action_id: str,
    app_name: str,
    expected_effect: str,
    mode: ComputerUseMode,
    category: ActionCategory,
    risk: RiskClass,
) -> ProposedAction:
    return ProposedAction(
        action_id=action_id,
        category=category,
        risk_class=risk,
        target_descriptor=TargetDescriptor(
            target_ref=app_name,
            window_identity=f"app:{app_name}",
            app_identity=f"desktop:{app_name}",
            selector_source="desktop",
            selector=app_name,
            expected_effect=expected_effect,
            current_url="desktop://front",
        ),
        window_identity=f"app:{app_name}",
        app_identity=f"desktop:{app_name}",
        selector_source="desktop",
        expected_effect=expected_effect,
        approval_required=mode == ComputerUseMode.STEP_APPROVAL,
        dry_run_preview=expected_effect,
        parameters={"app_name": app_name},
        verification_kind="frontmost_app",
        verification_value=app_name,
    )


def _risk_for_selector(selector: str) -> RiskClass:
    lowered = selector.lower()
    if any(token in lowered for token in {"submit", "send", "delete", "remove", "confirm"}):
        return RiskClass.HIGH
    return RiskClass.MEDIUM


def _extract_first_quoted(text: str) -> str | None:
    match = re.search(_QUOTED, text)
    if match is None:
        return None
    return match.group(1)


def _strip_quotes(text: str) -> str:
    normalized = text.strip()
    if normalized.startswith('"') and normalized.endswith('"'):
        return normalized[1:-1]
    return normalized
