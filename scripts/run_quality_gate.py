#!/usr/bin/env python3
"""Unified CASAN Quality Gate Orchestrator (EPIC R10 - Quality Assurance).

Runs all verification gates to validate architecture, security, single responsibility,
and test suite compliance before merging PRs or cutting a release.

Verification Stages (CASAN):
  1. [C] Clean Architecture Guard (scripts/check_imports.py)
  2. [A] Atomic & Secrets Audit (scripts/audit_security.py)
  3. [S] Single Responsibility / LOC Guard (scripts/check_loc.py)
  4. [O] Orphan Module Guard (scripts/check_orphan_modules.py)
  5. [A/N] Automated Tests & No-Regression Suite (pytest)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Ensure stdout handles UTF-8 on Windows consoles without codec crash
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_stage(title: str, cmd: List[str], cwd: Path) -> Tuple[bool, float, str]:
    """Execute a single quality gate command and measure elapsed duration.

    Returns:
        A tuple of (success_boolean, elapsed_seconds, combined_output)
    """
    print(f"\n>> Running Gate: {title} ...")
    start_time = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        elapsed = time.time() - start_time
        success = proc.returncode == 0
        output = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
        return success, elapsed, output
    except Exception as exc:
        elapsed = time.time() - start_time
        return False, elapsed, f"Exception occurred while running {cmd}: {exc}"


def main() -> int:
    """Main CLI orchestrator for CASAN quality gates."""
    parser = argparse.ArgumentParser(description="Run CASAN Quality Gates on the repository.")
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running pytest (run static and architectural guards only)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed command output for passing gates as well",
    )

    args = parser.parse_args()

    print("=" * 75)
    print("COWORK LOCAL - CASAN QUALITY GATE RUNNER")
    print("=" * 75)

    stages = [
        (
            "C - Clean Architecture Boundary Check",
            [sys.executable, str(REPO_ROOT / "scripts" / "check_imports.py")],
        ),
        (
            "A - Secrets & Plaintext Credentials Audit",
            [sys.executable, str(REPO_ROOT / "scripts" / "audit_security.py")],
        ),
        (
            "S - Single Responsibility LOC Limit (<= 400 LOC)",
            [sys.executable, str(REPO_ROOT / "scripts" / "check_loc.py"), "--max-lines", "400"],
        ),
        # Ba cổng trên không cổng nào bắt được mã chết: một file không ai import
        # vẫn đúng chiều phụ thuộc, vẫn không có credential, vẫn dưới 400 dòng.
        # Cổng O đi tìm đúng khoảng trống đó.
        (
            "O - Orphan Module Guard (moi module phai co noi import)",
            [sys.executable, str(REPO_ROOT / "scripts" / "check_orphan_modules.py")],
        ),
    ]

    if not args.skip_tests:
        stages.append(
            (
                "A/N - Automated Pytest Suite (No-Regression)",
                [sys.executable, "-m", "pytest", "-q"],
            )
        )

    results = []
    all_passed = True
    total_start = time.time()

    for title, cmd in stages:
        success, elapsed, output = run_stage(title, cmd, cwd=REPO_ROOT)
        results.append((title, success, elapsed, output))

        if success:
            print(f"  [PASS] {title} ({elapsed:.2f}s)")
            if args.verbose:
                print(output.strip())
        else:
            all_passed = False
            print(f"  [FAIL] {title} ({elapsed:.2f}s)")
            print("\n--- Output ---")
            print(output.strip())
            print("--------------")

    total_elapsed = time.time() - total_start

    print("\n" + "=" * 75)
    print("QUALITY GATE SUMMARY REPORT")
    print("=" * 75)
    for title, success, elapsed, _ in results:
        status_str = "[PASS]" if success else "[FAIL]"
        print(f"  {status_str:<8} | {elapsed:>6.2f}s | {title}")

    print("-" * 75)
    print(f"Total Execution Time: {total_elapsed:.2f}s")

    if all_passed:
        print("\nALL CASAN QUALITY GATES PASSED! Ready for PR merge or release.")
        return 0
    else:
        print("\nQUALITY GATE FAILED! Please resolve the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
