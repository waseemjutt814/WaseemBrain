#!/usr/bin/env python
"""
WaseemBrain - Professional Test Runner
Runs all tests with comprehensive reporting and statistics.

Usage:
    python run_all_professional.py
    python run_all_professional.py --verbose
    python run_all_professional.py --failfast
    python run_all_professional.py --coverage
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class TestFile:
    """Test file information."""
    path: str
    name: str
    category: str
    test_count: int = 0
    passed: int = 0
    failed: int = 0
    duration: float = 0.0
    status: str = "pending"


@dataclass
class TestReport:
    """Comprehensive test report."""
    total_files: int = 0
    total_tests: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_duration: float = 0.0
    files: List[TestFile] = field(default_factory=list)
    categories: dict[str, dict] = field(default_factory=dict)
    
    def add_file(self, file_info: TestFile) -> None:
        self.files.append(file_info)
        self.total_files += 1
        self.total_tests += file_info.test_count
        self.total_passed += file_info.passed
        self.total_failed += file_info.failed
        self.total_duration += file_info.duration
        
        if file_info.category not in self.categories:
            self.categories[file_info.category] = {
                "files": 0,
                "tests": 0,
                "passed": 0,
                "failed": 0,
                "duration": 0.0
            }
        
        cat = self.categories[file_info.category]
        cat["files"] += 1
        cat["tests"] += file_info.test_count
        cat["passed"] += file_info.passed
        cat["failed"] += file_info.failed
        cat["duration"] += file_info.duration
    
    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.total_passed / self.total_tests) * 100


def discover_test_files(test_dir: Path) -> List[TestFile]:
    """Discover all test files in the project."""
    test_files: List[TestFile] = []
    
    # Direct test files (not patterns)
    direct_files = [
        ("types", "test_types.py"),
        ("config", "test_config.py"),
        ("normalizer", "test_normalizer.py"),
        ("memory", "test_memory.py"),
        ("components", "test_components.py"),
        ("learning", "test_learning.py"),
        ("router", "test_router_grpc.py"),
        ("reasoning", "test_reasoning_enhancement.py"),
        ("quality", "test_quality_gates.py"),
        ("bootstrap", "test_bootstrap_and_learning.py"),
        ("runtime", "test_runtime_service.py"),
        ("skill", "test_skill_sync.py"),
        ("knowledge", "test_knowledge_builder.py"),
        ("experts", "test_experts_simple.py"),
        ("unified", "test_unified.py"),
    ]
    
    for category, filename in direct_files:
        file_path = test_dir / filename
        if file_path.exists():
            test_files.append(TestFile(
                path=str(file_path),
                name=filename,
                category=category
            ))
    
    return test_files


def run_pytest(test_file: str, verbose: bool = False, failfast: bool = False) -> tuple[int, float, int, int]:
    """Run pytest on a specific test file."""
    # Use py -3.11 on Windows, python on other systems
    python_cmd = "py" if os.name == "nt" else "python"
    python_args = ["-3.11"] if os.name == "nt" else []
    
    cmd = [
        python_cmd,
        *python_args,
        "-m", "pytest",
        test_file,
        "-v" if verbose else "-q",
        "--tb=no",
        "--no-header",
    ]
    
    if failfast:
        cmd.append("-x")
    
    start_time = time.time()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    duration = time.time() - start_time
    
    # Parse results
    output = result.stdout + result.stderr
    # Look for pytest summary line like "85 passed"
    import re
    match = re.search(r'(\d+)\s+passed', output)
    if match:
        passed = int(match.group(1))
    else:
        passed = output.count(" PASSED") + output.count(" passed")
    
    match = re.search(r'(\d+)\s+failed', output)
    if match:
        failed = int(match.group(1))
    else:
        failed = output.count(" FAILED") + output.count(" failed")
    
    total = passed + failed
    
    return result.returncode, duration, passed, failed


def generate_report(report: TestReport, output_file: str) -> None:
    """Generate professional test report."""
    report_data = {
        "summary": {
            "total_files": report.total_files,
            "total_tests": report.total_tests,
            "passed": report.total_passed,
            "failed": report.total_failed,
            "pass_rate": round(report.pass_rate, 2),
            "duration_seconds": round(report.total_duration, 2),
        },
        "categories": report.categories,
        "files": [
            {
                "path": f.path,
                "name": f.name,
                "category": f.category,
                "tests": f.test_count,
                "passed": f.passed,
                "failed": f.failed,
                "duration": round(f.duration, 2),
                "status": f.status
            }
            for f in report.files
        ]
    }
    
    with open(output_file, "w") as f:
        json.dump(report_data, f, indent=2)


def print_header() -> None:
    """Print professional header."""
    print("\n" + "=" * 80)
    print("WASEEM BRAIN - PROFESSIONAL TEST SUITE")
    print("=" * 80)
    print(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def print_summary(report: TestReport) -> None:
    """Print professional summary."""
    print("\n" + "=" * 80)
    print("TEST EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Total Files:     {report.total_files}")
    print(f"Total Tests:     {report.total_tests}")
    print(f"Passed:          {report.total_passed} ({report.pass_rate:.1f}%)")
    print(f"Failed:          {report.total_failed}")
    print(f"Duration:        {report.total_duration:.2f} seconds")
    print()
    
    if report.categories:
        print("BY CATEGORY:")
        print("-" * 80)
        for category, stats in sorted(report.categories.items()):
            cat_pass_rate = (stats["passed"] / stats["tests"] * 100) if stats["tests"] > 0 else 0
            print(f"{category:20} | Files: {stats['files']:3} | Tests: {stats['tests']:4} | "
                  f"Passed: {stats['passed']:4} | Failed: {stats['failed']:2} | "
                  f"Rate: {cat_pass_rate:5.1f}% | Time: {stats['duration']:6.2f}s")
    
    print()
    
    if report.total_failed > 0:
        print("FAILED FILES:")
        print("-" * 80)
        for f in report.files:
            if f.failed > 0:
                print(f"  - {f.name:40} ({f.failed} failures)")
    
    print()
    print("=" * 80)
    print(f"Report saved to: tests/python/test_report_professional.json")
    print("=" * 80 + "\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run all WaseemBrain tests with professional reporting"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "-x", "--failfast",
        action="store_true",
        help="Stop on first failure"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Enable coverage reporting"
    )
    
    args = parser.parse_args()
    
    # Setup
    project_root = Path(__file__).parent.parent
    test_dir = project_root / "tests" / "python"
    os.environ.setdefault("EMOTION_TEXT_BACKEND", "heuristic")
    
    print_header()
    
    # Discover test files
    print("Discovering test files...")
    test_files = discover_test_files(test_dir)
    print(f"Found {len(test_files)} test files\n")
    
    # Run tests
    report = TestReport()
    
    for i, test_file in enumerate(test_files, 1):
        print(f"[{i}/{len(test_files)}] Running {test_file.name}...", end=" ", flush=True)
        
        try:
            exit_code, duration, passed, failed = run_pytest(
                test_file.path,
                verbose=args.verbose,
                failfast=args.failfast
            )
            
            test_file.test_count = passed + failed
            test_file.passed = passed
            test_file.failed = failed
            test_file.duration = duration
            test_file.status = "PASS" if exit_code == 0 else "FAIL"
            
            report.add_file(test_file)
            
            status = "✓ PASS" if exit_code == 0 else "✗ FAIL"
            print(f"{status} ({passed}p/{failed}f) [{duration:.2f}s]")
            
            if args.failfast and exit_code != 0:
                print("\nStopping on first failure (--failfast)")
                break
                
        except Exception as e:
            print(f"✗ ERROR: {e}")
            test_file.status = "ERROR"
            report.add_file(test_file)
    
    # Generate report
    report_path = test_dir / "test_report_professional.json"
    generate_report(report, str(report_path))
    
    # Print summary
    print_summary(report)
    
    return 0 if report.total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
