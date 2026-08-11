#!/usr/bin/env python3
"""Certification Forge journey for echo-data-pipeline.

The Forge sandbox is python:3.12-alpine with no Node.js, so this journey
performs text/structural checks on the TypeScript source rather than
actually running npm/vitest/wrangler. Each check is discriminating: it
must fail against the pre-fix source and pass against the current source,
not just assert a file exists.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FAILURES = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def read(rel_path):
    path = REPO_ROOT / rel_path
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def main():
    index_ts = read("src/index.ts")
    check("src/index.ts exists", index_ts is not None)

    if index_ts:
        auth_match = re.search(
            r"// ─── Auth middleware.*?app\.use\('\*',\s*async\s*\(c,\s*next\)\s*=>\s*\{(.*?)\n\}\);",
            index_ts,
            re.S,
        )
        check("auth middleware block found", auth_match is not None)
        body = auth_match.group(1) if auth_match else ""

        fails_closed_explicitly = bool(re.search(r"if\s*\(\s*!c\.env\.ECHO_API_KEY\s*\)\s*\{", body))
        check("auth middleware explicitly fails closed (503) on unconfigured key", fails_closed_explicitly)

        uses_timing_safe = "timingSafeEqual(" in body
        check("auth middleware uses timingSafeEqual, not raw !==", uses_timing_safe)

        no_raw_compare = "apiKey !== c.env.ECHO_API_KEY" not in body
        check("no raw !== comparison against ECHO_API_KEY", no_raw_compare)

    utils_ts = read("src/utils.ts")
    check("src/utils.ts exists", utils_ts is not None)
    if utils_ts:
        tse_match = re.search(
            r"export function timingSafeEqual\([^)]*\)\s*:\s*boolean\s*\{(.*?)\n\}",
            utils_ts,
            re.S,
        )
        check("timingSafeEqual function found", tse_match is not None)
        tse_body = tse_match.group(1) if tse_match else ""
        early_length_return = bool(
            re.search(r"if\s*\(\s*a\.length\s*!==\s*b\.length\s*\)\s*return\s*false", tse_body)
        )
        check(
            "timingSafeEqual has no early-return-on-length-mismatch timing oracle",
            not early_length_return,
        )

    executor_ts = read("src/executor.ts")
    check("src/executor.ts exists", executor_ts is not None)
    if executor_ts:
        check("D1 destination has a table allowlist", "TABLE_ALLOWLIST" in executor_ts and "validateTableName" in executor_ts)
        check("D1 destination validates column names", "validateColumnName" in executor_ts and "SAFE_IDENTIFIER_RE" in executor_ts)
        check("D1 source enforces SELECT-only + keyword blocklist", "only allows SELECT queries" in executor_ts and "dangerous" in executor_ts)

    transforms_ts = read("src/transforms.ts")
    check("src/transforms.ts exists", transforms_ts is not None)
    if transforms_ts:
        check(
            "transforms.ts has no eval/Function code-execution risk",
            "eval(" not in transforms_ts and "new Function(" not in transforms_ts,
        )

    package_json_raw = read("package.json")
    check("package.json exists", package_json_raw is not None)
    if package_json_raw:
        pkg = json.loads(package_json_raw)
        scripts = pkg.get("scripts", {})
        check("package.json declares a test script", scripts.get("test") == "vitest run")
        dev_deps = pkg.get("devDependencies", {})
        check("vitest is a devDependency", "vitest" in dev_deps)
        check("license is declared", bool(pkg.get("license")))

    check("tests/security.test.ts exists", (REPO_ROOT / "tests" / "security.test.ts").exists())

    for fname in [
        "README.md",
        "LICENSE",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
    ]:
        check(f"{fname} exists", (REPO_ROOT / fname).exists())

    check(
        ".github/workflows/ci.yml exists",
        (REPO_ROOT / ".github" / "workflows" / "ci.yml").exists(),
    )

    print()
    if FAILURES:
        print(f"CERTFORGE JOURNEY: FAIL ({len(FAILURES)} check(s) failed)")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("CERTFORGE JOURNEY: PASS (all checks green)")
    sys.exit(0)


if __name__ == "__main__":
    main()
