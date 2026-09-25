"""Tests for echo-engine-pipeline-probe TimeoutStartSec (ECHO R&D rnd-10).

Stdlib unittest only — importable in the CertForge offline sandbox (no pytest,
no third-party deps, 90s wall). Slow probes are *simulated* (no real sleep) so
a mocked 100s run stays well under the sandbox budget.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = REPO_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from echo_pipeline_probe.timeout_policy import (  # noqa: E402
    DEFAULT_SYSTEMD_TIMEOUT_START_SEC,
    DROPIN_REL_PATH,
    TARGET_TIMEOUT_START_SEC,
    UNIT_REL_PATH,
    evaluate_probe_start,
    load_unit_timeout_start_sec,
    parse_timeout_start_sec,
    probe_completes_within_timeout,
)


class TestParseTimeoutStartSec(unittest.TestCase):
    def test_parses_integer_seconds(self) -> None:
        text = "[Service]\nTimeoutStartSec=300\nNice=10\n"
        self.assertEqual(parse_timeout_start_sec(text), 300)

    def test_last_declaration_wins(self) -> None:
        text = "TimeoutStartSec=90\nTimeoutStartSec=300\n"
        self.assertEqual(parse_timeout_start_sec(text), 300)

    def test_missing_returns_none(self) -> None:
        self.assertIsNone(parse_timeout_start_sec("[Service]\nNice=10\n"))


class TestSlowProbeUnit(unittest.TestCase):
    """Unit: mocked probe taking 100s completes under TimeoutStartSec=300."""

    def test_mocked_100s_probe_succeeds_with_timeout_300(self) -> None:
        # Simulated wall time — do NOT sleep(100); CertForge budget is 90s.
        mocked_probe_duration_sec = 100.0
        self.assertTrue(
            probe_completes_within_timeout(
                mocked_probe_duration_sec, TARGET_TIMEOUT_START_SEC
            )
        )
        outcome = evaluate_probe_start(
            mocked_probe_duration_sec, TARGET_TIMEOUT_START_SEC
        )
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.result, "success")
        self.assertIsNone(outcome.exit_signal)
        self.assertEqual(outcome.as_dict()["unit_active"], 1)

    def test_mocked_100s_probe_fails_under_default_90(self) -> None:
        mocked_probe_duration_sec = 100.0
        self.assertFalse(
            probe_completes_within_timeout(
                mocked_probe_duration_sec, DEFAULT_SYSTEMD_TIMEOUT_START_SEC
            )
        )
        outcome = evaluate_probe_start(
            mocked_probe_duration_sec, DEFAULT_SYSTEMD_TIMEOUT_START_SEC
        )
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.result, "timeout")
        self.assertEqual(outcome.exit_signal, "SIGTERM")
        self.assertEqual(outcome.as_dict()["unit_active"], 0)


class TestIntegrationVersionedUnit(unittest.TestCase):
    """Integration: versioned unit/drop-in prevent result=timeout under load."""

    def test_versioned_unit_declares_timeout_300(self) -> None:
        unit_path = REPO_ROOT / UNIT_REL_PATH
        dropin_path = REPO_ROOT / DROPIN_REL_PATH
        self.assertTrue(unit_path.is_file(), f"missing {unit_path}")
        self.assertTrue(dropin_path.is_file(), f"missing {dropin_path}")

        unit_text = unit_path.read_text(encoding="utf-8")
        dropin_text = dropin_path.read_text(encoding="utf-8")
        self.assertEqual(parse_timeout_start_sec(unit_text), TARGET_TIMEOUT_START_SEC)
        self.assertEqual(parse_timeout_start_sec(dropin_text), TARGET_TIMEOUT_START_SEC)

        effective = load_unit_timeout_start_sec(REPO_ROOT)
        self.assertEqual(effective, TARGET_TIMEOUT_START_SEC)

    def test_normal_load_does_not_timeout(self) -> None:
        # Observed successful runs complete well under 90s wall; use a
        # conservative "normal load" mock of 60s against the new 300s budget.
        normal_load_sec = 60.0
        timeout = load_unit_timeout_start_sec(REPO_ROOT)
        outcome = evaluate_probe_start(normal_load_sec, timeout)
        self.assertEqual(outcome.result, "success")
        self.assertNotEqual(outcome.result, "timeout")
        self.assertTrue(outcome.ok)

    def test_slow_687_item_cycle_fits_new_budget(self) -> None:
        # Hypothesis case: workload that exceeds the old ~90s default but fits 300.
        slow_cycle_sec = 100.0
        timeout = load_unit_timeout_start_sec(REPO_ROOT)
        self.assertEqual(timeout, 300)
        outcome = evaluate_probe_start(slow_cycle_sec, timeout)
        self.assertEqual(outcome.result, "success")
        self.assertIsNone(outcome.exit_signal)


class TestInputValidation(unittest.TestCase):
    def test_negative_duration_rejected(self) -> None:
        with self.assertRaises(ValueError):
            probe_completes_within_timeout(-1.0, 300)

    def test_non_positive_timeout_rejected(self) -> None:
        with self.assertRaises(ValueError):
            probe_completes_within_timeout(10.0, 0)


def load_tests(loader, tests, pattern):  # noqa: ARG001
    """unittest discovery hook used by certforge_testkit."""
    suite = unittest.TestSuite()
    for case in (
        TestParseTimeoutStartSec,
        TestSlowProbeUnit,
        TestIntegrationVersionedUnit,
        TestInputValidation,
    ):
        suite.addTests(loader.loadTestsFromTestCase(case))
    return suite


if __name__ == "__main__":
    unittest.main(verbosity=2)
