#!/usr/bin/env python
"""
Unified Test Runner for WaseemBrain
Runs all tests with proper configuration and reporting.

Usage:
    python -m tests.python.run_all_tests
    python -m tests.python.run_all_tests --verbose
    python -m tests.python.run_all_tests --coverage
    python -m tests.python.run_all_tests --fast
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple


class TestSuite(NamedTuple):
    """Test suite configuration."""
    name: str
    path: str
    min_tests: int


# All test suites in the project
TEST_SUITES = [
    TestSuite("Types", "tests/python/test_types.py", 1),
    TestSuite("Normalizer", "tests/python/test_normalizer.py", 1),
    TestSuite("Memory", "tests/python/test_memory.py", 1),
    TestSuite("Emotion", "tests/python/test_emotion.py", 0),  # Empty file
    TestSuite("Experts", "tests/python/test_experts.py", 0),  # Empty file
    TestSuite("Internet", "tests/python/test_internet.py", 0),  # Empty file
    TestSuite("Coordinator", "tests/python/test_coordinator.py", 0),  # Empty file
    TestSuite("Components", "tests/python/test_components.py", 5),
    TestSuite("Expert Modules", "tests/python/test_expert_modules.py", 5),
    TestSuite("Experts Simple", "tests/python/test_experts_simple.py", 3),
    TestSuite("Experts Comprehensive", "tests/python/test_experts_comprehensive.py", 5),
    TestSuite("Learning", "tests/python/test_learning.py", 5),
    TestSuite("Router gRPC", "tests/python/test_router_grpc.py", 3),
    TestSuite("Bootstrap & Learning", "tests/python/test_bootstrap_and_learning.py", 3),
    TestSuite("Runtime Service", "tests/python/test_runtime_service.py", 1),
    TestSuite("Runtime Integrations", "tests/python/test_runtime_integrations.py", 5),
    TestSuite("Quality Gates", "tests/python/test_quality_gates.py", 2),
    TestSuite("Skill Sync", "tests/python/test_skill_sync.py", 2),
    TestSuite("Knowledge Builder", "tests/python/test_knowledge_builder.py", 1),
    TestSuite("Reasoning Enhancement", "tests/python/test_reasoning_enhancement.py", 3),
    TestSuite("All Phases", "tests/python/test_all_phases.py", 5),
    TestSuite("Complete System", "tests/python/test_complete_system.py", 5),
]


def setup_environment() -> None:
    """Setup test environment variables."""
    os.environ.setdefault("EMOTION_TEXT_BACKEND", "heuristic")
    os.environ.setdefault("PROJECT_ROOT", str(Path(__file__).parent.parent.parent))
    os.environ.setdefault("TEST_MODE", "true")


def run_pytest(
    test_path: str,
    verbose: bool = False,
    coverage: bool = False,
    fast: bool = False,
) -> tuple[int, float, int, int]:
    """
    Run pytest on a specific test file.
    
    Returns:
        Tuple of (exit_code, duration_seconds, passed, failed)
    """
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "-v" if verbose else "-q",
        "--tb=short",
        "--no-header",
    ]
    
    if coverage:
        cmd.extend(["--cov=brain", "--cov-report=term-missing"])
    
    if fast:
        cmd.extend(["-x", "--failfast"])
    
    start_time = time.time()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent),
    )
    duration = time.time() - start_time
    
    # Parse results
    output = result.stdout + result.stderr
    passed = output.count(" passed")
    failed = output.count(" failed")
    
    return result.returncode, duration, passed, failed


def run_all_tests(
    verbose: bool = False,
    coverage: bool = False,
    fast: bool = False,
) -> int:
    """
    Run all test suites and report results.
    
    Returns:
        Total number of failures
    """
    setup_environment()
    
    print("=" * 70)
    print("WASEEM BRAIN - UNIFIED TEST SUITE")
    print("=" * 70)
    print()
    
    total_passed = 0
    total_failed = 0
    total_duration = 0.0
    suite_results = []
    
    for suite in TEST_SUITES:
        test_file = Path(__file__).parent.parent.parent / suite.path
        
        if not test_file.exists():
            print(f"[SKIP] {suite.name}: File not found")
            continue
        
        # Check if file is empty
        if test_file.stat().st_size == 0:
            print(f"[EMPTY] {suite.name}: No tests defined")
            continue
        
        print(f"[RUN] {suite.name}...", end=" ", flush=True)
        
        exit_code, duration, passed, failed = run_pytest(
            str(test_file),
            verbose=verbose,
            coverage=coverage,
            fast=fast,
        )
        
        total_duration += duration
        total_passed += passed
        total_failed += failed
        
        status = "PASS" if exit_code == 0 else "FAIL"
        print(f"[{status}] {passed} passed, {failed} failed ({duration:.2f}s)")
        
        suite_results.append({
            "name": suite.name,
            "status": status,
            "passed": passed,
            "failed": failed,
            "duration": duration,
        })
    
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Suites: {len([r for r in suite_results if r['status'] == 'PASS'])}/{len(suite_results)}")
    print(f"Total Tests:  {total_passed} passed, {total_failed} failed")
    print(f"Total Time:   {total_duration:.2f} seconds")
    print()
    
    if total_failed > 0:
        print("FAILED SUITES:")
        for r in suite_results:
            if r["status"] == "FAIL":
                print(f"  - {r['name']}: {r['failed']} failures")
        print()
    
    # Generate test report file
    report_path = Path(__file__).parent / "test_report.txt"
    with open(report_path, "w") as f:
        f.write("WASEEM BRAIN TEST REPORT\n")
        f.write("=" * 50 + "\n\n")
        for r in suite_results:
            f.write(f"{r['name']}: {r['status']} ({r['passed']}p/{r['failed']}f) {r['duration']:.2f}s\n")
        f.write(f"\nTotal: {total_passed} passed, {total_failed} failed\n")
    
    print(f"Report saved to: {report_path}")
    
    return total_failed


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run all WaseemBrain tests"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Enable coverage reporting"
    )
    parser.add_argument(
        "-f", "--fast",
        action="store_true",
        help="Stop on first failure"
    )
    
    args = parser.parse_args()
    
    failures = run_all_tests(
        verbose=args.verbose,
        coverage=args.coverage,
        fast=args.fast,
    )
    
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
