"""Plan context-compression experiments without inventing a measurement.

Three families stay separate:

- A, KV compression: fewer bytes per cached element. llama.cpp q4_0, q8_0, and f16.
- B, context selection: drop or skip tokens. Not selected automatically.
- C, semantic compression: rewrite history into a shorter text. Not a KV substitute.

The production baseline stays q4_0 KV on the existing Qwen3.8-27B recipe.
Compression is off unless the caller turns it on. Nothing here changes weights.
"""

from __future__ import annotations

import math
from typing import Any

QUALITY_NOT_VERIFIED = "NOT_VERIFIED"
QUALITY_MEASURED_DELTA = "MEASURED_DELTA"
QUALITY_ZERO_LOSS = "ZERO_QUALITY_LOSS"

# A 2 point drop is an orientation recorded before any compression run.
# It is not an automatic pass. ZERO_QUALITY_LOSS also needs the uncertainty
# bound below and zero misses on names, numbers, code, citations, and instructions.
ORIENTATION_SUCCESS_DROP = 0.02
MIN_PAIRED_TRIALS = 2400
CRITICAL_CHECKS = (
    "names",
    "numbers",
    "instructions",
    "code",
    "citations",
    "long_context_start",
    "long_context_middle",
    "long_context_end",
)
TASK_SUITES = (
    "reasoning",
    "coding",
    "factual_long_document",
    "exact_numbers_and_quotes",
    "instruction_following",
    "long_context_retrieval",
    "multi_hop",
    "position_retention",
)

# P5 measured anchors. Recurrent state stayed 149.62 MiB at c2048 and c8192.
# Quality for every anchor is NOT_RUN. See docs/KV_TRADEOFF.md.
KV_MIB_AT_8192 = {"q4_0": 144.0, "q8_0": 272.0, "f16": 512.0}
P5_Q4_C8192_PEAK_MIB = 7641.0
P5_Q4_C8192_KV_MIB = 144.0
RECURRENT_STATE_MIB = 149.62
CARD_VRAM_MIB = 8151.0
INTERACTIVE_RESERVE_MIB = 512.0
BASELINE_KV = "q4_0"
CONTEXTS = (8192, 16384, 32768, 65536)

# Higher fidelity first. Token-dropping methods are absent on purpose.
FIDELITY_ORDER = ("f16", "q8_0", "q4_0")
TASK_PREFERENCE = {
    "code": ("f16", "q8_0", "q4_0"),
    "document": ("q8_0", "f16", "q4_0"),
    "dialogue": ("q8_0", "q4_0", "f16"),
}


def classify_quality(
    *,
    uncompressed_success: float | None,
    compressed_success: float | None,
    n_paired: int | None,
    critical_misses: int | None,
) -> str:
    """Return NOT_VERIFIED, MEASURED_DELTA, or ZERO_QUALITY_LOSS."""
    if (
        uncompressed_success is None
        or compressed_success is None
        or n_paired is None
        or critical_misses is None
        or n_paired <= 0
    ):
        return QUALITY_NOT_VERIFIED
    drop = uncompressed_success - compressed_success
    if n_paired < MIN_PAIRED_TRIALS or critical_misses > 0:
        return QUALITY_MEASURED_DELTA
    # Conservative half-width for a difference of two proportions near one half.
    half_width = 1.96 * math.sqrt(0.5 / n_paired)
    if drop + half_width <= 0 and critical_misses == 0:
        return QUALITY_ZERO_LOSS
    return QUALITY_MEASURED_DELTA


def estimate_kv_mib(kv: str, context_tokens: int) -> dict[str, Any]:
    if kv not in KV_MIB_AT_8192:
        raise ValueError(f"unknown KV type {kv}")
    if context_tokens <= 0:
        raise ValueError("context_tokens must be positive")
    measured = KV_MIB_AT_8192[kv]
    if context_tokens == 8192:
        evidence = "measured_anchor"
        mib = measured
    else:
        evidence = "ESTIMATED"
        mib = measured * (context_tokens / 8192)
    return {
        "kv": kv,
        "context_tokens": context_tokens,
        "kv_mib": mib,
        "recurrent_state_mib": RECURRENT_STATE_MIB,
        "evidence_class": "MEASURED" if evidence == "measured_anchor" else "ESTIMATED",
        "note": (
            "Recurrent state is the P5 constant. It is not scaled with context. "
            "A longer hybrid state would make this estimate too small."
        ),
    }


def estimate_peak_vram_mib(kv: str, context_tokens: int) -> dict[str, Any]:
    """Extrapolate the P5 q4 c8192 peak by swapping only the KV term."""
    kv_estimate = estimate_kv_mib(kv, context_tokens)
    peak = P5_Q4_C8192_PEAK_MIB - P5_Q4_C8192_KV_MIB + kv_estimate["kv_mib"]
    measured_anchor = kv == "q4_0" and context_tokens == 8192
    return {
        **kv_estimate,
        "peak_vram_mib": peak,
        "card_vram_mib": CARD_VRAM_MIB,
        "estimated_free_vram_mib": CARD_VRAM_MIB - peak,
        "fits_card": peak <= CARD_VRAM_MIB,
        "fits_interactive_reserve": CARD_VRAM_MIB - peak >= INTERACTIVE_RESERVE_MIB,
        "evidence_class": "MEASURED" if measured_anchor else "ESTIMATED",
        "quality_status": QUALITY_NOT_VERIFIED,
        "prefill_tokens_per_second": None,
        "decode_tokens_per_second": None,
        "ttft_seconds": None,
    }


def select_representation(
    *,
    task: str,
    context_tokens: int,
    compression_enabled: bool,
    mode: str = "INTERACTIVE",
    accuracy_required: bool = True,
) -> dict[str, Any]:
    """Choose a KV type, or the untouched baseline. Does not drop tokens."""
    if task not in TASK_PREFERENCE:
        raise ValueError(f"task must be one of {tuple(TASK_PREFERENCE)}")
    if mode not in {"INTERACTIVE", "BENCHMARK"}:
        raise ValueError("mode must be INTERACTIVE or BENCHMARK")
    baseline = {
        "compression_enabled": False,
        "family": "A",
        "kv": BASELINE_KV,
        "reason": "Production baseline. Weights and the q4_0 runtime stay in place.",
        "token_eviction": False,
        "semantic_rewrite": False,
        "quality_status": QUALITY_NOT_VERIFIED,
    }
    if not compression_enabled:
        choice = baseline
    else:
        order = TASK_PREFERENCE[task]
        if accuracy_required and task == "code":
            order = FIDELITY_ORDER
        selected = None
        rejected: list[dict[str, Any]] = []
        for kv in order:
            estimate = estimate_peak_vram_mib(kv, context_tokens)
            if mode == "INTERACTIVE":
                fits = estimate["fits_interactive_reserve"]
            else:
                fits = estimate["fits_card"]
            if fits:
                selected = kv
                break
            rejected.append(
                {
                    "kv": kv,
                    "estimated_peak_vram_mib": estimate["peak_vram_mib"],
                    "estimated_free_vram_mib": estimate["estimated_free_vram_mib"],
                }
            )
        if selected is None:
            choice = {
                **baseline,
                "compression_enabled": True,
                "kv": BASELINE_KV,
                "fits": False,
                "reason": (
                    "No llama.cpp KV type leaves the interactive reserve, or none fits the card. "
                    "The baseline stays available and can be switched off. "
                    "Tokens are not discarded."
                ),
                "rejected": rejected,
            }
        else:
            choice = {
                "compression_enabled": True,
                "family": "A",
                "kv": selected,
                "fits": True,
                "token_eviction": False,
                "semantic_rewrite": False,
                "quality_status": QUALITY_NOT_VERIFIED,
                "reason": (
                    "Highest-fidelity llama.cpp KV type in the task order that this mode's "
                    "VRAM check still accepts. Quality is NOT_VERIFIED. "
                    "This is not a win over q4_0."
                ),
                "rejected": rejected,
            }
    estimate = None
    if choice.get("kv"):
        estimate = estimate_peak_vram_mib(choice["kv"], context_tokens)
    return {
        "schema_version": 1,
        "track": "context-compression",
        "blocks_p9": False,
        "weights_modified": False,
        "fine_tune": False,
        "task": task,
        "context_tokens": context_tokens,
        "occupied_context_tokens": None,
        "choice": choice,
        "estimate": estimate,
        "quality_status": QUALITY_NOT_VERIFIED,
        "suites": list(TASK_SUITES),
        "critical_checks": list(CRITICAL_CHECKS),
        "orientation_success_drop": ORIENTATION_SUCCESS_DROP,
        "disable": "Pass compression_enabled false to stay on the q4_0 baseline.",
    }


def comparison_matrix() -> list[dict[str, Any]]:
    """Estimated peaks for the three measured KV types. Speed and quality stay null."""
    rows = []
    for context in CONTEXTS:
        for kv in FIDELITY_ORDER:
            rows.append(estimate_peak_vram_mib(kv, context))
    return rows


def relax_after_quality(kv: str, quality_status: str, critical_misses: int) -> str:
    """Step back toward the baseline when a real delta is worse. Never invent a pass."""
    if kv not in FIDELITY_ORDER and kv != "off":
        raise ValueError(f"unknown KV type {kv}")
    if quality_status == QUALITY_NOT_VERIFIED:
        return BASELINE_KV
    if quality_status == QUALITY_ZERO_LOSS and critical_misses == 0:
        return kv
    if quality_status != QUALITY_MEASURED_DELTA:
        raise ValueError(f"unknown quality status {quality_status}")
    if critical_misses > 0 or kv == BASELINE_KV:
        return "off"
    index = FIDELITY_ORDER.index(kv)
    if index + 1 >= len(FIDELITY_ORDER):
        return "off"
    return FIDELITY_ORDER[index + 1]
