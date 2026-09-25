#!/usr/bin/env python3
"""CertForge journey for ECHO R&D proposal #10 (rnd-10).

Verifies the versioned echo-engine-pipeline-probe TimeoutStartSec=300 change
and runs the stdlib unittest suite via certforge_testkit. Offline-safe:
stdlib only, no live systemctl, no production edits.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    suffix = f" — {detail}" if detail and not condition else ""
    print(f"[{status}] {name}{suffix}")
    if not condition:
        FAILURES.append(name)


def main() -> int:
    unit = REPO_ROOT / "systemd" / "echo-engine-pipeline-probe.service"
    dropin = (
        REPO_ROOT
        / "systemd"
        / "echo-engine-pipeline-probe.service.d"
        / "10-timeout-start.conf"
    )
    timer = REPO_ROOT / "systemd" / "echo-engine-pipeline-probe.timer"
    test_file = REPO_ROOT / "tests" / "python" / "test_pipeline_probe_timeout.py"
    policy = REPO_ROOT / "python" / "echo_pipeline_probe" / "timeout_policy.py"
    cert = REPO_ROOT / ".echo" / "certification.json"

    check("unit file exists", unit.is_file())
    check("drop-in exists", dropin.is_file())
    check("timer file exists", timer.is_file())
    check("timeout policy module exists", policy.is_file())
    check("rnd-10 test module exists", test_file.is_file())

    if unit.is_file():
        text = unit.read_text(encoding="utf-8")
        check("unit declares TimeoutStartSec=300", "TimeoutStartSec=300" in text)
        check("unit remains Type=oneshot", "Type=oneshot" in text)
        check(
            "unit still invokes ops_engine_pipeline_probe.py",
            "ops_engine_pipeline_probe.py" in text,
        )

    if dropin.is_file():
        check(
            "drop-in declares TimeoutStartSec=300",
            "TimeoutStartSec=300" in dropin.read_text(encoding="utf-8"),
        )

    if cert.is_file():
        data = json.loads(cert.read_text(encoding="utf-8"))
        rnd = data.get("rnd") or {}
        check("certification.json has rnd.proposal_id == 10", rnd.get("proposal_id") == 10)
        check(
            "certification.json rnd.policy_version",
            rnd.get("policy_version") == "certforge.rnd-staging.v1",
        )
        journey = rnd.get("journey") or []
        check(
            "certification.json rnd.journey points at rnd_10_journey.py",
            journey == ["python3", "-B", "scripts/rnd_10_journey.py"],
        )
        # Existing keys must remain for other pipelines.
        check("certification.json keeps version key", "version" in data)
        check("certification.json keeps top-level journey", "journey" in data)

    # Run the discriminating test suite (mocked 100s probe, integration checks).
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        import certforge_testkit  # noqa: WPS433
    except ImportError as exc:
        check("certforge_testkit importable", False, str(exc))
    else:
        rc = certforge_testkit.run_suite(
            test_file,
            sys_paths=["python"],
        )
        check("rnd-10 unittest suite green", rc == 0, f"exit={rc}")

    print()
    if FAILURES:
        print(f"RND-10 JOURNEY: FAIL ({len(FAILURES)} check(s) failed)")
        for name in FAILURES:
            print(f"  - {name}")
        return 1
    print("RND-10 JOURNEY: PASS (all checks green)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
