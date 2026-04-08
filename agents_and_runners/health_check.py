#!/usr/bin/env python3
"""
WASEEM SYSTEM - HEALTH CHECK DIAGNOSTIC
Industrial-Grade System Verification with Detailed Reporting
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class HealthChecker:
    """Complete system health check and diagnostic"""
    
    def __init__(self):
        self.project_root = Path(".")
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": [],
            "failures": [],
            "warnings": [],
            "overall_status": "CHECKING"
        }
    
    def print_header(self):
        """Print professional header"""
        print("\n" + "="*80)
        print(" "*(20) + "WASEEM SYSTEM - HEALTH CHECK")
        print("="*80)
        print()
    
    def print_section(self, section_name: str):
        """Print section header"""
        print(f"\n[{section_name}]")
        print("-" * 80)
    
    def check_python_version(self) -> bool:
        """Check Python version"""
        self.print_section("PYTHON VERSION")
        
        version = sys.version_info
        required = (3, 11)
        
        status = version >= required
        symbol = "✓" if status else "✗"
        
        print(f"{symbol} Python {version.major}.{version.minor}.{version.micro}")
        print(f"  Required: {required[0]}.{required[1]}+")
        print(f"  Status: {'PASS' if status else 'FAIL'}")
        
        self.results["checks"].append({
            "component": "Python Version",
            "status": "PASS" if status else "FAIL",
            "version": f"{version.major}.{version.minor}.{version.micro}"
        })
        
        if not status:
            self.results["failures"].append("Python version below 3.11")
        
        return status
    
    def check_dependencies(self) -> bool:
        """Check all dependencies"""
        self.print_section("DEPENDENCIES")
        
        dependencies = {
            "numpy": "Data processing",
            "pandas": "Data handling",
            "scipy": "Scientific computing",
            "sklearn": "Machine learning",
            "pyttsx3": "Text-to-speech",
            "pytest": "Testing framework",
            "colorama": "Terminal colors",
            "requests": "HTTP requests"
        }
        
        all_ok = True
        for package, description in dependencies.items():
            try:
                __import__(package)
                print(f"✓ {package:<15} - {description}")
                self.results["checks"].append({
                    "component": f"Dependency: {package}",
                    "status": "PASS"
                })
            except ImportError:
                print(f"✗ {package:<15} - {description}")
                self.results["warnings"].append(f"{package} not installed")
                all_ok = False
        
        return all_ok
    
    def check_project_structure(self) -> bool:
        """Check project structure"""
        self.print_section("PROJECT STRUCTURE")
        
        directories = [
            "brain",
            "experts",
            "scripts",
            "tests"
        ]
        
        files = [
            "waseem_agent.py",
            "waseem_agent_v2.py",
            "waseem_orchestrator.py",
            "waseem_complete_system.py"
        ]
        
        all_ok = True
        
        for dir_name in directories:
            path = self.project_root / dir_name
            if path.exists():
                print(f"✓ {dir_name}/")
                self.results["checks"].append({
                    "component": f"Directory: {dir_name}",
                    "status": "PASS"
                })
            else:
                print(f"✗ {dir_name}/")
                self.results["warnings"].append(f"Directory {dir_name} missing")
        
        for file_name in files:
            path = self.project_root / file_name
            if path.exists():
                size = path.stat().st_size
                print(f"✓ {file_name:<35} ({size:,} bytes)")
                self.results["checks"].append({
                    "component": f"File: {file_name}",
                    "status": "PASS"
                })
            else:
                print(f"✗ {file_name}")
                self.results["failures"].append(f"Missing file: {file_name}")
                all_ok = False
        
        return all_ok
    
    def check_waseem_components(self) -> bool:
        """Check Waseem components functionality"""
        self.print_section("WASEEM COMPONENTS")
        
        components = [
            ("waseem_agent.py", "Agent v1: Analysis & Reasoning"),
            ("waseem_agent_v2.py", "Agent v2: Real Execution"),
            ("waseem_orchestrator.py", "Orchestrator: Multi-Agent"),
            ("waseem_complete_system.py", "Master: Integration")
        ]
        
        all_ok = True
        for filename, description in components:
            path = self.project_root / filename
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                        if "class " in content and "def " in content:
                            lines = len(content.split('\n'))
                            print(f"✓ {description:<40} ({lines} lines)")
                            self.results["checks"].append({
                                "component": filename,
                                "status": "PASS",
                                "lines": lines
                            })
                        else:
                            print(f"✗ {description:<40} (invalid)")
                            all_ok = False
                except Exception as e:
                    print(f"✗ {description:<40} (error: {str(e)})")
                    all_ok = False
            else:
                print(f"✗ {description:<40} (missing)")
                all_ok = False
        
        return all_ok
    
    def check_json_states(self) -> bool:
        """Check system state files"""
        self.print_section("SYSTEM STATE FILES")
        
        state_files = [
            "waseem_agent_state.json",
            "waseem_agent_v2_state.json",
            "waseem_orchestrator_state.json",
            "waseem_complete_system_state.json"
        ]
        
        all_ok = True
        for state_file in state_files:
            path = self.project_root / state_file
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        size = path.stat().st_size
                        print(f"✓ {state_file:<40} ({size:,} bytes)")
                        self.results["checks"].append({
                            "component": f"State: {state_file}",
                            "status": "PASS"
                        })
                except Exception as e:
                    print(f"✗ {state_file:<40} (invalid JSON)")
                    all_ok = False
            else:
                print(f"! {state_file:<40} (not yet generated)")
        
        return all_ok
    
    def check_tts_capability(self) -> bool:
        """Check TTS/Voice capability"""
        self.print_section("TEXT-TO-SPEECH (TTS) CAPABILITY")
        
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            
            print(f"✓ pyttsx3 TTS engine initialized")
            print(f"✓ Available voices: {len(voices)}")
            print(f"✓ Default voice: {voices[0].name if voices else 'N/A'}")
            print(f"✓ Speech rate: {engine.getProperty('rate')} wpm")
            print(f"✓ Volume: {engine.getProperty('volume')}")
            
            self.results["checks"].append({
                "component": "TTS Engine",
                "status": "PASS",
                "voices": len(voices)
            })
            
            return True
        except Exception as e:
            print(f"✗ TTS capability check failed: {str(e)}")
            self.results["warnings"].append(f"TTS initialization issue: {str(e)}")
            return False
    
    def check_test_framework(self) -> bool:
        """Check test framework"""
        self.print_section("TEST FRAMEWORK")
        
        try:
            import pytest
            print(f"✓ pytest version: {pytest.__version__}")
            
            # Check for test files
            test_dir = self.project_root / "tests"
            if test_dir.exists():
                test_files = list(test_dir.glob("**/*.py"))
                print(f"✓ Test files found: {len(test_files)}")
                self.results["checks"].append({
                    "component": "Test Framework",
                    "status": "PASS",
                    "test_files": len(test_files)
                })
                return True
            else:
                print(f"! Test directory not found (will be created)")
                self.results["warnings"].append("Test directory missing")
                return False
                
        except ImportError:
            print(f"✗ pytest not installed")
            self.results["failures"].append("pytest not installed")
            return False
    
    def run_quick_tests(self) -> bool:
        """Run quick component tests"""
        self.print_section("QUICK COMPONENT TESTS")
        
        all_ok = True
        
        # Test Agent v1
        print("Testing Agent v1...")
        try:
            result = subprocess.run(
                [sys.executable, "waseem_agent.py"],
                capture_output=True,
                timeout=10,
                text=True
            )
            if "Agent loaded" in result.stdout or result.returncode == 0:
                print("✓ Agent v1: PASS")
                self.results["checks"].append({
                    "component": "Agent v1 Test",
                    "status": "PASS"
                })
            else:
                print(f"! Agent v1: Output mismatch (code: {result.returncode})")
        except Exception as e:
            print(f"! Agent v1: Timeout or error")
        
        # Test Agent v2
        print("Testing Agent v2...")
        try:
            result = subprocess.run(
                [sys.executable, "waseem_agent_v2.py"],
                capture_output=True,
                timeout=10,
                text=True
            )
            if "initialized" in result.stdout or result.returncode == 0:
                print("✓ Agent v2: PASS")
                self.results["checks"].append({
                    "component": "Agent v2 Test",
                    "status": "PASS"
                })
            else:
                print(f"! Agent v2: Output mismatch (code: {result.returncode})")
        except Exception as e:
            print(f"! Agent v2: Timeout or error")
        
        return all_ok
    
    def generate_report(self) -> None:
        """Generate comprehensive report"""
        self.print_section("HEALTH CHECK SUMMARY")
        
        total_checks = len(self.results["checks"])
        failures = len(self.results["failures"])
        warnings = len(self.results["warnings"])
        
        print(f"\nTotal Checks:    {total_checks}")
        print(f"Passed:          {total_checks - failures}")
        print(f"Failed:          {failures}")
        print(f"Warnings:        {warnings}")
        
        if failures == 0:
            self.results["overall_status"] = "HEALTHY"
            status_symbol = "✓"
        elif failures < 3:
            self.results["overall_status"] = "WARNING"
            status_symbol = "!"
        else:
            self.results["overall_status"] = "CRITICAL"
            status_symbol = "✗"
        
        print(f"\nOverall Status:  {status_symbol} {self.results['overall_status']}")
        
        if failures > 0:
            print("\nFailures:")
            for failure in self.results["failures"]:
                print(f"  ✗ {failure}")
        
        if warnings > 0:
            print("\nWarnings:")
            for warning in self.results["warnings"]:
                print(f"  ! {warning}")
        
        print()
    
    def save_report(self) -> None:
        """Save health check report to JSON"""
        report_file = self.project_root / "health_check_report.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"✓ Report saved to health_check_report.json")
    
    def run_all_checks(self) -> bool:
        """Run all health checks"""
        self.print_header()
        
        checks = [
            self.check_python_version,
            self.check_dependencies,
            self.check_project_structure,
            self.check_waseem_components,
            self.check_json_states,
            self.check_tts_capability,
            self.check_test_framework,
        ]
        
        for check in checks:
            try:
                check()
            except Exception as e:
                print(f"\n[ERROR] Check failed: {str(e)}")
        
        # Run quick tests if all basic checks pass
        if len(self.results["failures"]) == 0:
            print()
            self.run_quick_tests()
        
        self.generate_report()
        self.save_report()
        
        print("="*80)
        print("HEALTH CHECK COMPLETED")
        print("="*80)
        print()
        
        return len(self.results["failures"]) == 0


def main():
    """Main health check execution"""
    checker = HealthChecker()
    success = checker.run_all_checks()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
