# rnd-10 — Increase TimeoutStartSec for `echo-engine-pipeline-probe.service`

ECHO R&D Division proposal **#10** (risk class A). Ships through PR + CertForge
only — this document does **not** authorize live `systemctl` changes from the
builder sandbox.

## Problem

`echo-engine-pipeline-probe.service` failed with `result=timeout` / exit 15
(SIGTERM). The oneshot probe verifies ~687 engine routes; under load, wall time
can exceed systemd's default `TimeoutStartSec` (~90s) even when CPU time is low.

## Change

Versioned unit + drop-in set:

```ini
TimeoutStartSec=300
```

Files:

- `systemd/echo-engine-pipeline-probe.service`
- `systemd/echo-engine-pipeline-probe.service.d/10-timeout-start.conf`
- `systemd/echo-engine-pipeline-probe.timer` (unchanged schedule; tracked for completeness)

Policy helpers + tests live under `python/echo_pipeline_probe/` and
`tests/python/test_pipeline_probe_timeout.py`.

## Apply (ops — after merge / certification)

```bash
sudo install -d /etc/systemd/system/echo-engine-pipeline-probe.service.d
sudo cp systemd/echo-engine-pipeline-probe.service /etc/systemd/system/
sudo cp systemd/echo-engine-pipeline-probe.service.d/10-timeout-start.conf \
  /etc/systemd/system/echo-engine-pipeline-probe.service.d/
sudo systemctl daemon-reload
systemctl show echo-engine-pipeline-probe.service -p TimeoutStartUSec
```

Do **not** restart production from this PR workflow; the oneshot timer will pick
up the new budget on the next start after `daemon-reload`.

## Rollback

1. Remove or revert `TimeoutStartSec=300` in
   `/etc/systemd/system/echo-engine-pipeline-probe.service` and delete
   `/etc/systemd/system/echo-engine-pipeline-probe.service.d/10-timeout-start.conf`
   (or restore the previous value).
2. `sudo systemctl daemon-reload`
3. `sudo systemctl restart echo-engine-pipeline-probe.service` (optional; next
   timer tick also applies).

## Success metric

`unit_active({"unit": "echo-engine-pipeline-probe.service"})` → 1
(higher_is_better, tolerance 1.0%).

## Verification

```bash
python3 -B scripts/rnd_10_journey.py
python3 -B scripts/certforge_testkit.py tests/python/test_pipeline_probe_timeout.py --sys-path python
```
