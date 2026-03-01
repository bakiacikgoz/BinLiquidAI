from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


@dataclass(slots=True)
class EnergyMeasurement:
    mode: str
    ok: bool
    wh: float | None
    detail: str
    confidence: float
    error_reason: str | None
    notes: str


def measure_energy_wh(duration_s: int = 6) -> EnergyMeasurement:
    cmd = [
        "powermetrics",
        "-n",
        "1",
        "-i",
        str(max(duration_s * 1000, 1000)),
        "--samplers",
        "cpu_power",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=duration_s + 5,
        )
    except FileNotFoundError:
        return EnergyMeasurement(
            mode="measured",
            ok=False,
            wh=None,
            detail="powermetrics command not found",
            confidence=0.0,
            error_reason="tool_not_found",
            notes="powermetrics binary missing from PATH",
        )
    except subprocess.TimeoutExpired:
        return EnergyMeasurement(
            mode="measured",
            ok=False,
            wh=None,
            detail="powermetrics timed out",
            confidence=0.0,
            error_reason="timeout",
            notes="powermetrics did not return in expected window",
        )

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        if "permission" in stderr.lower() or "root" in stderr.lower() or "sudo" in stderr.lower():
            detail = "powermetrics requires elevated permission"
            error_reason = "permission_denied"
        else:
            detail = stderr or "powermetrics failed"
            error_reason = "tool_failure"
        return EnergyMeasurement(
            mode="measured",
            ok=False,
            wh=None,
            detail=detail,
            confidence=0.05,
            error_reason=error_reason,
            notes="measurement command returned non-zero exit code",
        )

    watts = _extract_cpu_watts(proc.stdout)
    if watts is None:
        return EnergyMeasurement(
            mode="measured",
            ok=False,
            wh=None,
            detail="could not parse cpu power output",
            confidence=0.1,
            error_reason="parse_error",
            notes="powermetrics output did not include CPU power lines",
        )

    wh = watts * (duration_s / 3600)
    return EnergyMeasurement(
        mode="measured",
        ok=True,
        wh=round(wh, 6),
        detail=f"parsed {watts:.3f} W from powermetrics",
        confidence=0.75,
        error_reason=None,
        notes="single-sample cpu_power reading",
    )


def _extract_cpu_watts(output: str) -> float | None:
    patterns = [
        r"CPU Power:\s*([0-9]+\.?[0-9]*)\s*W",
        r"Combined Power.*?([0-9]+\.?[0-9]*)\s*W",
    ]
    for pattern in patterns:
        match = re.search(pattern, output, flags=re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None
