"""Host resource decisions for experimental runs.

The guard never terminates another process and never changes a system setting.
INTERACTIVE means a person is using the machine. BENCHMARK means an exclusive
run that the operator explicitly allowed. Missing telemetry is not a free pass.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

INTERACTIVE = "INTERACTIVE"
BENCHMARK = "BENCHMARK"
MODES = (INTERACTIVE, BENCHMARK)

# Measured occupied-8192 q4_0 peak on the RTX 5060 was 7767 MiB of 8151.
# That is the production baseline, not a new result. Interactive mode keeps
# a reserve so a start is refused when the desktop would have almost no VRAM.
CARD_VRAM_MIB = 8151.0
BASELINE_PEAK_VRAM_MIB = 7767.0
INTERACTIVE_VRAM_RESERVE_MIB = 512.0
INTERACTIVE_RAM_RESERVE_MIB = 1024.0
GPU_BUSY_UTIL_PERCENT = 40.0
CPU_BUSY_UTIL_PERCENT = 85.0
GPU_TEMP_LIMIT_C = 85.0


@dataclass(frozen=True)
class HostSnapshot:
    gpu_util_percent: float | None = None
    vram_used_mib: float | None = None
    vram_free_mib: float | None = None
    cpu_util_percent: float | None = None
    ram_free_mib: float | None = None
    ram_total_mib: float | None = None
    commit_used_mib: float | None = None
    commit_limit_mib: float | None = None
    gpu_temp_c: float | None = None
    gpu_power_w: float | None = None
    user_gpu_busy: bool = False
    telemetry_complete: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_nvidia_smi_csv(line: str) -> dict[str, float | None]:
    """Parse one nvidia-smi CSV line: util, memory.used, memory.free, temp, power."""
    fields = [field.strip() for field in line.split(",")]
    if len(fields) < 5:
        raise ValueError("nvidia-smi line needs utilization, used, free, temperature, power")

    def _number(value: str) -> float | None:
        if value in {"", "[N/A]", "N/A"}:
            return None
        return float(value)

    return {
        "gpu_util_percent": _number(fields[0]),
        "vram_used_mib": _number(fields[1]),
        "vram_free_mib": _number(fields[2]),
        "gpu_temp_c": _number(fields[3]),
        "gpu_power_w": _number(fields[4]),
    }


def assess_host(
    snapshot: HostSnapshot,
    mode: str,
    *,
    allow_exclusive: bool = False,
    projected_peak_vram_mib: float | None = None,
) -> dict[str, Any]:
    """Return PROCEED, DEFER, PAUSE, or REFUSE. Never a kill instruction."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    reasons: list[str] = []
    action = "PROCEED"
    rank = {"PROCEED": 0, "DEFER": 1, "PAUSE": 2, "REFUSE": 3}

    def _set(next_action: str) -> None:
        nonlocal action
        if rank[next_action] >= rank[action]:
            action = next_action

    if mode == BENCHMARK and not allow_exclusive:
        _set("REFUSE")
        reasons.append("BENCHMARK mode requires an explicit exclusive-run permission.")
    if not snapshot.telemetry_complete:
        _set("DEFER")
        reasons.append("Host telemetry is incomplete, so the run stays deferred.")
    if snapshot.user_gpu_busy or (
        snapshot.gpu_util_percent is not None and snapshot.gpu_util_percent >= GPU_BUSY_UTIL_PERCENT
    ):
        if mode == INTERACTIVE:
            _set("PAUSE")
            reasons.append(
                "A GPU-heavy application is active. Inference pauses at a safe boundary "
                "and does not close that application."
            )
    if snapshot.gpu_temp_c is not None and snapshot.gpu_temp_c >= GPU_TEMP_LIMIT_C:
        _set("DEFER")
        reasons.append("GPU temperature is at or above the defer limit.")
    if snapshot.cpu_util_percent is not None and snapshot.cpu_util_percent >= CPU_BUSY_UTIL_PERCENT:
        if mode == INTERACTIVE:
            _set("DEFER")
            reasons.append("CPU utilization is too high for a background calibration or prefill.")
    free_vram = snapshot.vram_free_mib
    if free_vram is not None and free_vram < INTERACTIVE_VRAM_RESERVE_MIB and mode == INTERACTIVE:
        _set("REFUSE")
        reasons.append(
            f"Free VRAM {free_vram:.0f} MiB is below the {INTERACTIVE_VRAM_RESERVE_MIB:.0f} MiB "
            "interactive reserve. The 27B baseline already peaks near "
            f"{BASELINE_PEAK_VRAM_MIB:.0f} of {CARD_VRAM_MIB:.0f} MiB, so a hitch-free desktop "
            "cannot be promised while another GPU workload is resident."
        )
    if (
        projected_peak_vram_mib is not None
        and free_vram is not None
        and projected_peak_vram_mib
        > free_vram - (INTERACTIVE_VRAM_RESERVE_MIB if mode == INTERACTIVE else 0)
    ):
        _set("REFUSE")
        reasons.append(
            "Projected peak VRAM does not fit in the free memory left for this mode. "
            "Use a shorter context or leave compression off. Tokens are not dropped to force a fit."
        )
    if snapshot.ram_free_mib is not None and snapshot.ram_free_mib < INTERACTIVE_RAM_RESERVE_MIB:
        if mode == INTERACTIVE:
            _set("DEFER")
            reasons.append("Free RAM is below the interactive reserve.")
    if (
        snapshot.commit_used_mib is not None
        and snapshot.commit_limit_mib is not None
        and snapshot.commit_limit_mib > 0
        and snapshot.commit_used_mib / snapshot.commit_limit_mib >= 0.90
    ):
        _set("DEFER")
        reasons.append("Commit charge is at or above 90 percent of the limit.")
    if not reasons:
        reasons.append("Telemetry is inside the limits for this mode.")
    if mode == BENCHMARK and action == "PROCEED":
        reasons.append(
            "Exclusive mode was permitted. A full prefill can still peg the GPU. "
            "That is not an interactive-safety claim."
        )
    return {
        "schema_version": 1,
        "mode": mode,
        "action": action,
        "kills_processes": False,
        "changes_system_settings": False,
        "reasons": reasons,
        "snapshot": snapshot.to_dict(),
        "projected_peak_vram_mib": projected_peak_vram_mib,
    }
