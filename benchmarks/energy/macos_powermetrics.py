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
        )
    except subprocess.TimeoutExpired:
        return EnergyMeasurement(
            mode="measured",
            ok=False,
            wh=None,
            detail="powermetrics timed out",
        )

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        if "permission" in stderr.lower() or "root" in stderr.lower() or "sudo" in stderr.lower():
            detail = "powermetrics requires elevated permission"
        else:
            detail = stderr or "powermetrics failed"
        return EnergyMeasurement(mode="measured", ok=False, wh=None, detail=detail)

    watts = _extract_cpu_watts(proc.stdout)
    if watts is None:
        return EnergyMeasurement(
            mode="measured",
            ok=False,
            wh=None,
            detail="could not parse cpu power output",
        )

    wh = watts * (duration_s / 3600)
    return EnergyMeasurement(
        mode="measured",
        ok=True,
        wh=round(wh, 6),
        detail=f"parsed {watts:.3f} W from powermetrics",
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
