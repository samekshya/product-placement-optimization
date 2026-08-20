"""
run_verifications.py

Runs the project's three verification mechanisms in sequence and records the
outcome, with a timestamp, to reports/verification_status.json:

    scripts/verify_thesis_numbers.py    every reported figure against a source
    etl/quality_checks.py               the warehouse against OLTP and thesis
    reproduce_all_results.py            artifact regeneration end to end

    python scripts/run_verifications.py

Why the JSON exists: the dashboard shows verification status ("77 of 77
figures verified"). A count typed into the dashboard would go stale the moment
anything changed, which is exactly the class of error the project documents.
So the dashboard reads this file instead, and displays WHEN it was produced,
so a stale pass can never be mistaken for a current one.

The pass counts are parsed from the scripts' own [PASS]/[FAIL] lines and
summary output, not re-stated here. Exit code 0 only if all three passed.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPORTS = os.path.join(ROOT, "reports")
os.makedirs(REPORTS, exist_ok=True)

STATUS_PATH = os.path.join(REPORTS, "verification_status.json")

SCRIPTS = [
    ("verify_thesis_numbers", os.path.join(ROOT, "scripts", "verify_thesis_numbers.py"),
     "Every reported figure checked against a live source"),
    ("quality_checks", os.path.join(ROOT, "etl", "quality_checks.py"),
     "Warehouse checked against the OLTP source and the thesis figures"),
    ("reproduce_all_results", os.path.join(ROOT, "reproduce_all_results.py"),
     "Artifacts regenerated and every stage re-checked"),
]


def run_one(name, path, description):
    proc = subprocess.run(
        [sys.executable, path], capture_output=True, text=True, cwd=ROOT
    )
    out = proc.stdout + proc.stderr
    passed = len(re.findall(r"\[PASS\]", out))
    failed = len(re.findall(r"\[FAIL\]", out))

    result = {
        "description": description,
        "passed": passed,
        "failed": failed,
        "total": passed + failed,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
    }

    # Script-specific detail, parsed from their own summaries.
    m = re.search(r"VERIFIED: (\d+) of (\d+) checkable figures match", out)
    if m:
        result["verified"] = int(m.group(1))
        result["checkable"] = int(m.group(2))
    m = re.search(r"NOT AUTO-CHECKABLE: (\d+)", out)
    if m:
        result["not_auto_checkable"] = int(m.group(1))
    stages = len(re.findall(r"^STEP \d+", out, flags=re.MULTILINE))
    if stages:
        result["stages"] = stages
    return result


def main():
    started = datetime.now()
    print("=" * 74)
    print("RUN ALL VERIFICATIONS")
    print("=" * 74)

    checks = {}
    for name, path, description in SCRIPTS:
        print(f"\n  running {os.path.relpath(path, ROOT)} ...", flush=True)
        checks[name] = run_one(name, path, description)
        r = checks[name]
        state = "OK" if r["ok"] else "FAILED"
        print(f"    {state}: {r['passed']} passed, {r['failed']} failed "
              f"(exit {r['exit_code']})")

    all_ok = all(r["ok"] for r in checks.values())
    status = {
        "generated_at": started.isoformat(timespec="seconds"),
        "generated_at_human": started.strftime("%d %b %Y, %H:%M"),
        "duration_seconds": round((datetime.now() - started).total_seconds(), 1),
        "all_passed": all_ok,
        "checks": checks,
    }
    with open(STATUS_PATH, "w", encoding="utf-8") as fh:
        json.dump(status, fh, indent=2)

    print()
    print("=" * 74)
    print(f"{'ALL VERIFICATIONS PASSED' if all_ok else 'ONE OR MORE VERIFICATIONS FAILED'}")
    print(f"Status written to {os.path.relpath(STATUS_PATH, ROOT)}")
    print("=" * 74)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
