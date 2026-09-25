"""TimeoutStartSec policy for echo-engine-pipeline-probe.service (rnd-10).

Models systemd oneshot start budgeting without touching live units. Used by
unit/integration tests and the CertForge rnd journey. Stdlib-first so the
offline CertForge sandbox (no third-party packages) can import it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from loguru import logger as _raw_logger

    class _CompatLogger:
        """%-format bridge so the same call sites work under loguru or stdlib."""

        def debug(self, msg: str, *args: object) -> None:
            _raw_logger.debug(msg % args if args else msg)

        def info(self, msg: str, *args: object) -> None:
            _raw_logger.info(msg % args if args else msg)

        def warning(self, msg: str, *args: object) -> None:
            _raw_logger.warning(msg % args if args else msg)

    logger = _CompatLogger()
except ImportError:  # CertForge / minimal sandboxes
    import logging

    logger = logging.getLogger("echo_pipeline_probe.timeout_policy")
    if not logger.handlers:
        _handler = logging.StreamHandler()
        _handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(_handler)
        logger.setLevel(logging.INFO)

# systemd default when TimeoutStartSec is unset (DefaultTimeoutStartSec=90s
# on typical Debian/Ubuntu fleet images).
DEFAULT_SYSTEMD_TIMEOUT_START_SEC = 90

# ECHO R&D proposal #10 target: enough headroom for the 687-item probe cycle.
TARGET_TIMEOUT_START_SEC = 300

UNIT_REL_PATH = Path("systemd/echo-engine-pipeline-probe.service")
DROPIN_REL_PATH = Path(
    "systemd/echo-engine-pipeline-probe.service.d/10-timeout-start.conf"
)

_TIMEOUT_RE = re.compile(
    r"(?im)^\s*TimeoutStartSec\s*=\s*([0-9]+)\s*(?:s)?\s*$"
)


def parse_timeout_start_sec(unit_text: str) -> Optional[int]:
    """Return the last TimeoutStartSec integer in a unit/drop-in body, if any."""
    matches = _TIMEOUT_RE.findall(unit_text)
    if not matches:
        return None
    return int(matches[-1])


def load_unit_timeout_start_sec(repo_root: Path) -> int:
    """Load effective TimeoutStartSec from the versioned unit + drop-in.

    Drop-in values override the base unit (systemd semantics). Falls back to
    the systemd default when neither file declares the key.
    """
    root = Path(repo_root)
    base = root / UNIT_REL_PATH
    dropin = root / DROPIN_REL_PATH

    effective: Optional[int] = None
    if base.is_file():
        effective = parse_timeout_start_sec(base.read_text(encoding="utf-8"))
        logger.debug(
            "base unit TimeoutStartSec=%r from %s", effective, base
        )
    if dropin.is_file():
        dropin_val = parse_timeout_start_sec(dropin.read_text(encoding="utf-8"))
        if dropin_val is not None:
            effective = dropin_val
            logger.debug(
                "drop-in TimeoutStartSec=%s from %s", effective, dropin
            )

    if effective is None:
        logger.warning(
            "TimeoutStartSec unset in versioned unit files; using systemd default %s",
            DEFAULT_SYSTEMD_TIMEOUT_START_SEC,
        )
        return DEFAULT_SYSTEMD_TIMEOUT_START_SEC
    return effective


def probe_completes_within_timeout(
    probe_duration_sec: float,
    timeout_start_sec: float,
) -> bool:
    """True when a oneshot probe finishes before systemd would SIGTERM it."""
    if probe_duration_sec < 0:
        raise ValueError("probe_duration_sec must be >= 0")
    if timeout_start_sec <= 0:
        raise ValueError("timeout_start_sec must be > 0")
    return float(probe_duration_sec) <= float(timeout_start_sec)


@dataclass(frozen=True)
class ProbeStartResult:
    """Simulated systemd oneshot start outcome for the pipeline probe."""

    ok: bool
    result: str  # "success" | "timeout"
    probe_duration_sec: float
    timeout_start_sec: float
    exit_signal: Optional[str]

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "result": self.result,
            "probe_duration_sec": self.probe_duration_sec,
            "timeout_start_sec": self.timeout_start_sec,
            "exit_signal": self.exit_signal,
            "unit_active": 1 if self.ok else 0,
        }


def evaluate_probe_start(
    probe_duration_sec: float,
    timeout_start_sec: float,
) -> ProbeStartResult:
    """Simulate whether systemd would mark the oneshot as success or timeout.

    Mirrors the failure mode that motivated rnd-10: result=timeout, exit=15
    (SIGTERM) when wall time exceeds TimeoutStartSec.
    """
    completes = probe_completes_within_timeout(probe_duration_sec, timeout_start_sec)
    if completes:
        logger.info(
            "probe start ok duration=%ss timeout=%ss",
            probe_duration_sec,
            timeout_start_sec,
        )
        return ProbeStartResult(
            ok=True,
            result="success",
            probe_duration_sec=float(probe_duration_sec),
            timeout_start_sec=float(timeout_start_sec),
            exit_signal=None,
        )
    logger.warning(
        "probe start timeout duration=%ss timeout=%ss -> SIGTERM",
        probe_duration_sec,
        timeout_start_sec,
    )
    return ProbeStartResult(
        ok=False,
        result="timeout",
        probe_duration_sec=float(probe_duration_sec),
        timeout_start_sec=float(timeout_start_sec),
        exit_signal="SIGTERM",
    )
