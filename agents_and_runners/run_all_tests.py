#!/usr/bin/env python3
"""
WASEEM COMPLETE TEST RUNNER
Unified testing framework - runs ALL tests at once with detailed reporting
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class WaseemTestRunner:
    """Complete test orchestration and reporting"""
    
    def __init__(self):
        self.project_root = Path("d:\\latest brain")
        self.results = []
        self.start_time = datetime.now()
        self.manifest = self._load_manifest()
    
    def _load_manifest(self) -> Dict:
        """Load project manifest"""
        manifest_file = self.project_root / "waseem.manifest.json"
        if manifest_file.exists():
            with open(manifest_file) as f:
                return json.load(f)
        return {}
    
    def run_all_tests(self) -> None:
        """Run all test suites"""
        
        print("\n" + "="*80)
        print("WASEEM COMPLETE TEST SUITE")
        print("="*80)
        print(f"\nProject: {self.manifest.get('project', {}).get('name')}")
        print(f"Version: {self.manifest.get('project', {}).get('version')}")
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Generate test plan from manifest
        test_suites = self.manifest.get('tests', {}).get('suites', [])
        
        print(f"[CONFIGURATION] Found {len(test_suites)} test suites\n")
        
        # Run each suite
        for i, suite in enumerate(test_suites, 1):
            print(f"\n{'='*80}")
            print(f"[{i}/{len(test_suites)}] {suite.get('name')}")
            print(f"{'='*80}")
            
            result = self._run_test_suite(suite)
            self.results.append(result)
        
        # Generate summary
        self._print_summary()
        self._save_results()
    
    def _run_test_suite(self, suite: Dict) -> Dict:
        """Run individual test suite"""
        
        suite_name = suite.get('name')
        command = suite.get('command')
        
        print(f"\nCommand: {command}")
        print(f"Expected Pass Rate: {suite.get('expected_pass_rate')}%\n")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse output
            output = result.stdout + result.stderr
            
            # Check for success indicators
            passed = result.returncode == 0
            
            suite_result = {
                "suite": suite_name,
                "command": command,
                "status": "PASSED" if passed else "FAILED",
                "exit_code": result.returncode,
                "output_lines": len(output.split('\n')),
                "timestamp": datetime.now().isoformat()
            }
            
            # Print output excerpt
            lines = output.split('\n')
            for line in lines[-20:]:  # Last 20 lines
                if line.strip():
                    print(f"  {line}")
            
            if passed:
                print(f"\n✅ {suite_name}: PASSED")
            else:
                print(f"\n❌ {suite_name}: FAILED")
            
            return suite_result
            
        except subprocess.TimeoutExpired:
            print(f"⏱️ {suite_name}: TIMEOUT")
            return {
                "suite": suite_name,
                "status": "TIMEOUT",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ {suite_name}: ERROR - {str(e)}")
            return {
                "suite": suite_name,
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _print_summary(self) -> None:
        """Print comprehensive test summary"""
        
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        passed = sum(1 for r in self.results if r.get('status') == 'PASSED')
        failed = sum(1 for r in self.results if r.get('status') == 'FAILED')
        timeout = sum(1 for r in self.results if r.get('status') == 'TIMEOUT')
        error = sum(1 for r in self.results if r.get('status') == 'ERROR')
        
        total = len(self.results)
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}\n")
        
        print(f"Total Suites:        {total}")
        print(f"Passed:              {passed} ✅")
        print(f"Failed:              {failed} ❌")
        print(f"Timeout:             {timeout} ⏱️")
        print(f"Errors:              {error} ⚠️")
        print(f"\nPass Rate:           {pass_rate:.1f}%")
        print(f"Duration:            {duration:.2f} seconds")
        print(f"End Time:            {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Detailed results
        print(f"\n{'='*80}")
        print("DETAILED RESULTS")
        print(f"{'='*80}\n")
        
        for result in self.results:
            status_icon = {
                'PASSED': '✅',
                'FAILED': '❌',
                'TIMEOUT': '⏱️',
                'ERROR': '⚠️'
            }.get(result.get('status'), '❓')
            
            print(f"{status_icon} {result.get('suite')}")
            print(f"   Status: {result.get('status')}")
            if result.get('exit_code') is not None:
                print(f"   Exit Code: {result.get('exit_code')}")
            print()
        
        # Health check
        print(f"{'='*80}")
        print("SYSTEM HEALTH")
        print(f"{'='*80}\n")
        
        health = self.manifest.get('health', {})
        checks = health.get('checks', [])
        
        for check in checks:
            status_icon = "✅" if check.get('status') in ['active', 'installed', 'passing', 'available'] else "❌"
            print(f"{status_icon} {check.get('name')}")
            print(f"   Status: {check.get('status')}")
            if check.get('count'):
                print(f"   Count: {check.get('count')}")
            if check.get('version'):
                print(f"   Version: {check.get('version')}")
            print()
        
        # Final status
        if failed == 0 and timeout == 0 and error == 0:
            print(f"\n🎉 ALL TESTS PASSED! System is healthy.")
        else:
            print(f"\n⚠️ Some tests failed. Review output above.")
        
        print("\n" + "="*80 + "\n")
    
    def _save_results(self) -> None:
        """Save test results to JSON"""
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "project": self.manifest.get('project', {}),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "results": self.results,
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.get('status') == 'PASSED'),
                "failed": sum(1 for r in self.results if r.get('status') == 'FAILED'),
                "pass_rate": f"{(sum(1 for r in self.results if r.get('status') == 'PASSED') / len(self.results) * 100):.1f}%" if self.results else "N/A"
            }
        }
        
        output_file = self.project_root / "test_results.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Test results saved to: test_results.json\n")


def main():
    """Main execution"""
    
    runner = WaseemTestRunner()
    runner.run_all_tests()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
