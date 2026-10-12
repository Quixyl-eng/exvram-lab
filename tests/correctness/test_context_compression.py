import unittest

from exvram.context_compression import (
    MIN_PAIRED_TRIALS,
    QUALITY_MEASURED_DELTA,
    QUALITY_NOT_VERIFIED,
    QUALITY_ZERO_LOSS,
    classify_quality,
    comparison_matrix,
    estimate_peak_vram_mib,
    relax_after_quality,
    select_representation,
)
from exvram.resource_guard import HostSnapshot, assess_host, parse_nvidia_smi_csv


class ContextCompressionTests(unittest.TestCase):
    def test_equal_scores_are_not_zero_loss_inside_the_uncertainty_bound(self):
        status = classify_quality(
            uncompressed_success=0.80,
            compressed_success=0.80,
            n_paired=MIN_PAIRED_TRIALS,
            critical_misses=0,
        )
        self.assertEqual(status, QUALITY_MEASURED_DELTA)

    def test_missing_measurements_stay_unverified(self):
        self.assertEqual(
            classify_quality(
                uncompressed_success=None,
                compressed_success=None,
                n_paired=None,
                critical_misses=None,
            ),
            QUALITY_NOT_VERIFIED,
        )

    def test_a_critical_miss_blocks_zero_loss(self):
        status = classify_quality(
            uncompressed_success=0.70,
            compressed_success=0.90,
            n_paired=MIN_PAIRED_TRIALS,
            critical_misses=1,
        )
        self.assertEqual(status, QUALITY_MEASURED_DELTA)

    def test_zero_loss_requires_a_clear_non_inferior_result(self):
        status = classify_quality(
            uncompressed_success=0.70,
            compressed_success=0.80,
            n_paired=MIN_PAIRED_TRIALS,
            critical_misses=0,
        )
        self.assertEqual(status, QUALITY_ZERO_LOSS)

    def test_small_samples_cannot_claim_zero_loss(self):
        status = classify_quality(
            uncompressed_success=0.70,
            compressed_success=0.90,
            n_paired=50,
            critical_misses=0,
        )
        self.assertEqual(status, QUALITY_MEASURED_DELTA)

    def test_compression_off_keeps_the_q4_baseline(self):
        plan = select_representation(task="code", context_tokens=8192, compression_enabled=False)
        self.assertEqual(plan["choice"]["kv"], "q4_0")
        self.assertFalse(plan["choice"]["compression_enabled"])
        self.assertFalse(plan["weights_modified"])
        self.assertFalse(plan["blocks_p9"])
        self.assertIsNone(plan["occupied_context_tokens"])

    def test_interactive_mode_does_not_pick_a_tighter_kv_at_8k(self):
        plan = select_representation(
            task="code",
            context_tokens=8192,
            compression_enabled=True,
            mode="INTERACTIVE",
        )
        self.assertFalse(plan["choice"]["token_eviction"])
        self.assertFalse(plan["choice"].get("fits", True))
        self.assertEqual(plan["quality_status"], QUALITY_NOT_VERIFIED)

    def test_sixty_four_k_q4_estimate_does_not_fit_the_card(self):
        row = estimate_peak_vram_mib("q4_0", 65536)
        self.assertEqual(row["evidence_class"], "ESTIMATED")
        self.assertFalse(row["fits_card"])
        self.assertIsNone(row["decode_tokens_per_second"])
        self.assertGreater(row["kv_mib"], row["recurrent_state_mib"])

    def test_q4_8k_peak_stays_on_the_published_anchor(self):
        row = estimate_peak_vram_mib("q4_0", 8192)
        self.assertEqual(row["evidence_class"], "MEASURED")
        self.assertEqual(row["peak_vram_mib"], 7641.0)
        self.assertEqual(row["quality_status"], QUALITY_NOT_VERIFIED)

    def test_matrix_covers_four_lengths_without_speed_claims(self):
        rows = comparison_matrix()
        self.assertEqual(len(rows), 12)
        self.assertTrue(all(row["ttft_seconds"] is None for row in rows))

    def test_unverified_quality_returns_to_baseline(self):
        self.assertEqual(relax_after_quality("f16", QUALITY_NOT_VERIFIED, 0), "q4_0")

    def test_measured_loss_steps_back_and_a_critical_miss_turns_compression_off(self):
        self.assertEqual(relax_after_quality("f16", QUALITY_MEASURED_DELTA, 0), "q8_0")
        self.assertEqual(relax_after_quality("q8_0", QUALITY_MEASURED_DELTA, 2), "off")

    def test_plan_json_has_no_invented_rates(self):
        plan = select_representation(
            task="document", context_tokens=32768, compression_enabled=True
        )
        estimate = plan["estimate"]
        self.assertIsNone(estimate["prefill_tokens_per_second"])
        self.assertIsNone(estimate["decode_tokens_per_second"])
        self.assertIsNone(estimate["ttft_seconds"])
        self.assertEqual(plan["quality_status"], QUALITY_NOT_VERIFIED)


class ResourceGuardTests(unittest.TestCase):
    def test_benchmark_without_permission_is_refused(self):
        decision = assess_host(
            HostSnapshot(telemetry_complete=True, vram_free_mib=7000, ram_free_mib=8000),
            "BENCHMARK",
            allow_exclusive=False,
        )
        self.assertEqual(decision["action"], "REFUSE")
        self.assertFalse(decision["kills_processes"])
        self.assertFalse(decision["changes_system_settings"])

    def test_interactive_pauses_for_a_user_gpu_app_and_does_not_kill_it(self):
        decision = assess_host(
            HostSnapshot(
                telemetry_complete=True,
                user_gpu_busy=True,
                gpu_util_percent=95,
                vram_free_mib=4000,
                ram_free_mib=8000,
            ),
            "INTERACTIVE",
        )
        self.assertEqual(decision["action"], "PAUSE")
        self.assertNotIn("kill", " ".join(decision["reasons"]).lower())

    def test_low_free_vram_refuses_instead_of_dropping_tokens(self):
        decision = assess_host(
            HostSnapshot(telemetry_complete=True, vram_free_mib=200, ram_free_mib=8000),
            "INTERACTIVE",
            projected_peak_vram_mib=7000,
        )
        self.assertEqual(decision["action"], "REFUSE")
        self.assertIn("not dropped", " ".join(decision["reasons"]).lower())

    def test_exclusive_refusal_survives_incomplete_telemetry(self):
        decision = assess_host(
            HostSnapshot(telemetry_complete=False),
            "BENCHMARK",
            allow_exclusive=False,
        )
        self.assertEqual(decision["action"], "REFUSE")
        self.assertFalse(decision["kills_processes"])

    def test_incomplete_telemetry_defers(self):
        decision = assess_host(HostSnapshot(telemetry_complete=False), "INTERACTIVE")
        self.assertEqual(decision["action"], "DEFER")

    def test_nvidia_smi_csv_parser(self):
        parsed = parse_nvidia_smi_csv("12, 6400, 1700, 61, 88.5")
        self.assertEqual(parsed["vram_free_mib"], 1700)
        self.assertEqual(parsed["gpu_temp_c"], 61)
