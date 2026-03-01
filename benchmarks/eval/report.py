from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Benchmark Report",
        "",
        f"- Timestamp: {payload.get('timestamp', 'unknown')}",
        f"- Profile: {payload.get('profile', 'unknown')}",
        f"- Mode: {payload.get('mode', 'unknown')}",
        "",
        "## Results",
        "",
        "| Mode | Success | p50(ms) | p95(ms) | Peak RAM (MB) | Fallback |",
        "| Wrong Route | Expert Call | Memory Write | Energy (Wh) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    results = payload.get("results", {})
    for mode_name, row in sorted(results.items()):
        lines.append(
            (
                "| {mode} | {success} | {p50} | {p95} | {ram} | "
                "{fallback} | {wrong} | {expert} | {memory} | {energy} |"
            ).format(
                mode=mode_name,
                success=row.get("success_rate", 0),
                p50=row.get("p50_latency_ms", 0),
                p95=row.get("p95_latency_ms", 0),
                ram=row.get("peak_ram_mb", 0),
                fallback=row.get("fallback_rate", 0),
                wrong=row.get("wrong_route_rate", 0),
                expert=row.get("expert_call_rate", 0),
                memory=row.get("memory_write_rate", 0),
                energy=row.get("energy_estimate_wh", 0),
            )
        )
    lines.append("")
    return "\n".join(lines)


def write_report(payload: dict[str, Any], output_path: str | Path) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_markdown_report(payload), encoding="utf-8")
    return str(path)


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
