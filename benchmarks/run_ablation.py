from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchmarks.energy.macos_powermetrics import measure_energy_wh
from benchmarks.eval.report import write_report
from benchmarks.run_smoke import run_smoke_benchmark


def run_ablation_benchmark(
    profile: str = "balanced",
    mode: str = "all",
    output_path: str | None = None,
    report_path: str | None = None,
    task_limit: int | None = None,
    provider: str | None = None,
    fallback_provider: str | None = None,
) -> dict[str, Any]:
    payload = run_smoke_benchmark(
        profile=profile,
        mode=mode,
        output_path=output_path,
        task_limit=task_limit,
        provider=provider,
        fallback_provider=fallback_provider,
    )

    if report_path is None:
        out_json = Path(payload["output_path"])
        report_path = str(out_json.with_suffix(".md"))
    md_path = write_report(payload, report_path)
    payload["report_path"] = md_path
    return payload


def run_energy_benchmark(
    profile: str = "balanced",
    energy_mode: str = "measured",
    task_limit: int | None = 2,
    output_path: str | None = None,
    provider: str | None = None,
    fallback_provider: str | None = None,
) -> dict[str, Any]:
    mode = energy_mode.strip().lower()
    if mode not in {"measured", "estimated"}:
        raise ValueError("energy_mode must be one of: measured, estimated")

    baseline = run_smoke_benchmark(
        profile=profile,
        mode="A",
        output_path=None,
        task_limit=task_limit,
        provider=provider,
        fallback_provider=fallback_provider,
    )
    estimated_wh = float(baseline["results"]["A"].get("energy_estimate_wh", 0.0))

    measured = None
    if mode == "measured":
        measured = measure_energy_wh(duration_s=6)

    payload: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "profile": profile,
        "energy_mode": mode,
        "estimated_wh": estimated_wh,
        "measured": {
            "ok": measured.ok if measured else False,
            "wh": measured.wh if measured else None,
            "detail": measured.detail if measured else "not requested",
        },
        "source_benchmark": baseline.get("output_path"),
    }

    destination = Path(output_path) if output_path else _default_output_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    payload["output_path"] = str(destination)
    return payload


def _default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("benchmarks") / "results" / f"energy_{timestamp}.json"


if __name__ == "__main__":
    result = run_ablation_benchmark()
    print(json.dumps(result, indent=2, ensure_ascii=False))
