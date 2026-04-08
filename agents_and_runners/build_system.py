#!/usr/bin/env python3
"""
WASEEM COMPLETE BUILD & SETUP SYSTEM
Automated installation, testing, and validation - Single command build
"""

import subprocess
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple


class WaseemBuilder:
    """Complete build and deployment system"""
    
    def __init__(self):
        self.project_root = Path("d:\\latest brain")
        self.manifest_file = self.project_root / "waseem.manifest.json"
        self.manifest = self._load_manifest()
        self.build_log = []
        self.start_time = datetime.now()
    
    def _load_manifest(self) -> Dict:
        """Load project manifest"""
        if self.manifest_file.exists():
            with open(self.manifest_file) as f:
                return json.load(f)
        return {}
    
    def _log(self, message: str) -> None:
        """Log message to console and file"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        self.build_log.append(log_msg)
    
    def _run_command(self, command: str, description: str = "") -> Tuple[bool, str]:
        """Run shell command and return success status"""
        
        self._log(f"\n▶️  {description or command}")
        print(f"   Command: {command}\n")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            output = result.stdout + result.stderr
            
            if result.returncode == 0:
                self._log(f"✅ {description or command}: SUCCESS")
                return True, output
            else:
                self._log(f"❌ {description or command}: FAILED (Exit Code: {result.returncode})")
                # Print last few lines of error
                for line in output.split('\n')[-10:]:
                    if line.strip():
                        print(f"   {line}")
                return False, output
                
        except subprocess.TimeoutExpired:
            self._log(f"⏱️  {description or command}: TIMEOUT")
            return False, "Command timed out"
        except Exception as e:
            self._log(f"❌ {description or command}: ERROR - {str(e)}")
            return False, str(e)
    
    def build(self) -> bool:
        """Execute complete build and setup"""
        
        print("\n" + "="*80)
        print("WASEEM COMPLETE BUILD & SETUP SYSTEM")
        print("="*80)
        print(f"Project: {self.manifest.get('project', {}).get('name')}")
        print(f"Version: {self.manifest.get('project', {}).get('version')}")
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Get build steps from manifest
        build_steps = self.manifest.get('build', {}).get('steps', [])
        
        all_passed = True
        
        for step in build_steps:
            step_num = step.get('step')
            step_name = step.get('name')
            command = step.get('command')
            
            print(f"\n{'='*80}")
            print(f"[STEP {step_num}] {step_name}")
            print(f"{'='*80}")
            
            success, output = self._run_command(command, step_name)
            
            if not success:
                all_passed = False
                # Print detailed error
                print(f"\n⚠️  ERROR in {step_name}:")
                for line in output.split('\n'):
                    if line.strip():
                        print(f"    {line}")
        
        # Additional build steps
        if all_passed:
            print(f"\n{'='*80}")
            print("[STEP 5] Health Check & Validation")
            print(f"{'='*80}")
            
            # Quick health check
            success, _ = self._run_command(
                "py -3 -c \"import sys; print(f'Python: {sys.version}')\"",
                "Python Version Check"
            )
            
            if success:
                self._log("✅ All build steps completed successfully!")
            else:
                all_passed = False
        
        # Save build report
        self._save_build_report(all_passed)
        
        return all_passed
    
    def install_dependencies(self) -> bool:
        """Install all dependencies (Python + Node)"""
        
        print("\n" + "="*80)
        print("DEPENDENCY INSTALLATION")
        print("="*80 + "\n")
        
        all_passed = True
        
        # Python dependencies
        print("[1] Installing Python Dependencies...")
        success, _ = self._run_command(
            "py -3 -m pip install --upgrade pip setuptools wheel",
            "Upgrading pip"
        )
        
        if success:
            success, _ = self._run_command(
                "py -3 -m pip install -r requirements.txt -q",
                "Installing Python packages"
            )
            if not success:
                all_passed = False
        
        # Node dependencies
        print("\n[2] Installing Node Dependencies...")
        success, _ = self._run_command(
            "pnpm install",
            "Installing Node packages with pnpm"
        )
        
        if not success:
            # Try alternative without pnpm
            self._log("⚠️  pnpm not found, trying npm...")
            success, _ = self._run_command(
                "npm install --legacy-peer-deps",
                "Installing Node packages with npm"
            )
            if not success:
                all_passed = False
        
        return all_passed
    
    def run_tests(self) -> bool:
        """Run complete test suite"""
        
        print("\n" + "="*80)
        print("RUNNING COMPLETE TEST SUITE")
        print("="*80 + "\n")
        
        success, _ = self._run_command(
            "py -3 run_all_tests.py",
            "Running all tests"
        )
        
        return success
    
    def validate_system(self) -> bool:
        """Validate system installation"""
        
        print("\n" + "="*80)
        print("SYSTEM VALIDATION")
        print("="*80 + "\n")
        
        checks = [
            ("Python 3.11+", "py -3 --version"),
            ("pip", "pip --version"),
            ("Node.js 20+", "node --version"),
            ("pnpm", "pnpm --version"),
            ("Git", "git --version"),
        ]
        
        all_passed = True
        
        for check_name, command in checks:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True
            )
            
            status = "✅" if result.returncode == 0 else "❌"
            version = result.stdout.strip() if result.returncode == 0 else "NOT FOUND"
            
            print(f"{status} {check_name}: {version}")
            
            if result.returncode != 0:
                all_passed = False
        
        return all_passed
    
    def _save_build_report(self, success: bool) -> None:
        """Save build report to JSON"""
        
        duration = (datetime.now() - self.start_time).total_seconds()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "project": self.manifest.get('project', {}),
            "build_success": success,
            "duration_seconds": duration,
            "log": self.build_log[-50:]  # Last 50 log entries
        }
        
        report_file = self.project_root / "build_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✅ Build report saved to: build_report.json")
        print(f"Total Duration: {duration:.2f} seconds")


def main():
    """Main execution"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        command = "build"
    
    builder = WaseemBuilder()
    
    if command == "install":
        success = builder.install_dependencies()
    elif command == "test":
        success = builder.run_tests()
    elif command == "validate":
        success = builder.validate_system()
    elif command == "build":
        success = builder.build()
    elif command == "all":
        print("Running: install → build → test → validate")
        success = (
            builder.install_dependencies() and
            builder.build() and
            builder.run_tests() and
            builder.validate_system()
        )
    else:
        print(f"Unknown command: {command}")
        print("\nUsage: py -3 build_system.py [install|test|validate|build|all]")
        return 1
    
    print("\n" + "="*80)
    if success:
        print("🎉 BUILD COMPLETED SUCCESSFULLY!")
    else:
        print("❌ BUILD FAILED - Review errors above")
    print("="*80 + "\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
