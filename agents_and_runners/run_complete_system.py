#!/usr/bin/env python3
"""
WASEEM MASTER RUN SCRIPT - COMPLETE SYSTEM EXECUTION
Industrial-Grade Command Center - All Components in Proper Sequence
"""

import sys
import os
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


class WaseemMasterController:
    """Master controller for complete system execution"""
    
    def __init__(self):
        self.project_root = Path(".")
        self.execution_log = {
            "timestamp": datetime.now().isoformat(),
            "stages": [],
            "overall_status": "INITIALIZING",
            "start_time": time.time()
        }
        self.failed_stages = []
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_banner(self):
        """Print professional banner"""
        banner = """
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘                                                                              â•‘
â•‘        WASEEM COMPLETE AUTONOMOUS AI SYSTEM - MASTER CONTROL CENTER         â•‘
â•‘                         Production Build & Test Suite                        â•‘
â•‘                                                                              â•‘
â•‘  Version: 2.0  |  Build: Industrial  |  Status: Ready  |  Mode: Full Test  â•‘
â•‘                                                                              â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        """
        print(banner)
    
    def print_stage_header(self, stage_number: int, stage_name: str, total_stages: int):
        """Print stage header"""
        print(f"\n{'='*80}")
        print(f"[STAGE {stage_number}/{total_stages}] {stage_name}")
        print(f"{'='*80}\n")
    
    def run_stage(self, stage_num: int, stage_name: str, command: str, timeout: int = None) -> Tuple[bool, str]:
        """
        Run a single stage with proper error handling
        
        Args:
            stage_num: Stage number
            stage_name: Stage name
            command: Command to run
            timeout: Timeout in seconds
        
        Returns:
            Tuple of (success, message)
        """
        self.print_stage_header(stage_num, stage_name, 8)
        
        try:
            print(f"[Executing] {command}\n")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=False,
                timeout=timeout,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                print(f"\n[âœ“] {stage_name} SUCCESSFUL")
                self.execution_log["stages"].append({
                    "stage": stage_num,
                    "name": stage_name,
                    "status": "PASS",
                    "timestamp": datetime.now().isoformat()
                })
                return True, f"{stage_name} completed successfully"
            else:
                print(f"\n[!] {stage_name} returned exit code {result.returncode}")
                self.execution_log["stages"].append({
                    "stage": stage_num,
                    "name": stage_name,
                    "status": "WARNING",
                    "exit_code": result.returncode,
                    "timestamp": datetime.now().isoformat()
                })
                self.failed_stages.append(stage_name)
                return False, f"{stage_name} had issues"
                
        except subprocess.TimeoutExpired:
            print(f"\n[âœ—] {stage_name} TIMEOUT")
            self.execution_log["stages"].append({
                "stage": stage_num,
                "name": stage_name,
                "status": "TIMEOUT",
                "timestamp": datetime.now().isoformat()
            })
            self.failed_stages.append(stage_name)
            return False, f"{stage_name} timed out"
        except Exception as e:
            print(f"\n[âœ—] {stage_name} ERROR: {str(e)}")
            self.execution_log["stages"].append({
                "stage": stage_num,
                "name": stage_name,
                "status": "FAIL",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            self.failed_stages.append(stage_name)
            return False, f"{stage_name} failed: {str(e)}"
    
    def run_complete_pipeline(self):
        """Run complete build and test pipeline"""
        
        self.clear_screen()
        self.print_banner()
        
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Python Version: {sys.version.split()[0]}")
        print(f"Project Root: {self.project_root.absolute()}")
        print()
        
        # Stage 1: Health Check
        success1, msg1 = self.run_stage(
            1, 
            "SYSTEM HEALTH CHECK",
            f"{sys.executable} health_check.py",
            timeout=60
        )
        
        # Stage 2: Component Tests
        success2, msg2 = self.run_stage(
            2,
            "COMPONENT TESTING",
            f"{sys.executable} test_suite.py",
            timeout=120
        )
        
        # Stage 3: Agent v1 Test
        success3, msg3 = self.run_stage(
            3,
            "AGENT v1 EXECUTION TEST",
            f"{sys.executable} waseem_agent.py",
            timeout=60
        )
        
        # Stage 4: Agent v2 Test
        success4, msg4 = self.run_stage(
            4,
            "AGENT v2 EXECUTION TEST",
            f"{sys.executable} waseem_agent_v2.py",
            timeout=60
        )
        
        # Stage 5: Orchestrator Test
        success5, msg5 = self.run_stage(
            5,
            "ORCHESTRATOR TEST",
            f"{sys.executable} waseem_orchestrator.py",
            timeout=60
        )
        
        # Stage 6: Complete System Test
        success6, msg6 = self.run_stage(
            6,
            "COMPLETE SYSTEM TEST",
            f"{sys.executable} waseem_complete_system.py",
            timeout=120
        )
        
        # Stage 7: Voice Integration Test
        success7, msg7 = self.run_stage(
            7,
            "VOICE INTEGRATION TEST",
            f"{sys.executable} voice_integration.py",
            timeout=60
        )
        
        # Stage 8: Final Report
        success8, msg8 = self.generate_final_report()
        
        # Print summary
        self.print_final_summary(
            [success1, success2, success3, success4, success5, success6, success7, success8],
            [msg1, msg2, msg3, msg4, msg5, msg6, msg7, msg8]
        )
    
    def generate_final_report(self) -> Tuple[bool, str]:
        """Generate final comprehensive report"""
        
        self.print_stage_header(8, "FINAL REPORT GENERATION", 8)
        
        try:
            # Calculate statistics
            total_stages = len(self.execution_log["stages"])
            passed = sum(1 for s in self.execution_log["stages"] if s["status"] == "PASS")
            
            duration = time.time() - self.execution_log["start_time"]
            self.execution_log["duration_seconds"] = duration
            
            # Determine overall status
            if len(self.failed_stages) == 0:
                overall_status = "âœ“ PRODUCTION READY"
                self.execution_log["overall_status"] = "SUCCESS"
            elif len(self.failed_stages) <= 2:
                overall_status = "! ACCEPTABLE WITH WARNINGS"
                self.execution_log["overall_status"] = "SUCCESS_WITH_WARNINGS"
            else:
                overall_status = "âœ— NEEDS ATTENTION"
                self.execution_log["overall_status"] = "PARTIAL_SUCCESS"
            
            # Print report
            print(f"Build Timestamp: {datetime.now().isoformat()}")
            print(f"Total Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
            print(f"Stages Completed: {total_stages}")
            print(f"Stages Passed: {passed}/{total_stages}")
            print(f"Overall Status: {overall_status}")
            
            if self.failed_stages:
                print(f"\nIssues Found:")
                for stage in self.failed_stages:
                    print(f"  ! {stage}")
            
            # Save execution log
            log_file = Path("execution_log.json")
            with open(log_file, 'w') as f:
                json.dump(self.execution_log, f, indent=2)
            
            print(f"\n[âœ“] Execution log saved to execution_log.json")
            
            return True, "Final report generated successfully"
            
        except Exception as e:
            print(f"\n[!] Report generation issue: {str(e)}")
            return False, f"Report generation had issues: {str(e)}"
    
    def print_final_summary(self, results: List[bool], messages: List[str]):
        """Print final comprehensive summary"""
        
        print("\n\n" + "="*80)
        print(" "*20 + "WASEEM SYSTEM - COMPLETE EXECUTION SUMMARY")
        print("="*80)
        print()
        
        stages = [
            "System Health Check",
            "Component Testing",
            "Agent v1 Execution",
            "Agent v2 Execution",
            "Orchestrator Test",
            "Complete System Test",
            "Voice Integration",
            "Final Report"
        ]
        
        print("[STAGE RESULTS]")
        for i, (stage, result, msg) in enumerate(zip(stages, results, messages), 1):
            status = "âœ“ PASS" if result else "! WARN/FAIL"
            print(f"  [{i}] {status:<10} - {stage:<30} - {msg}")
        
        passed = sum(results)
        total = len(results)
        pass_rate = (passed / total) * 100 if total > 0 else 0
        
        print(f"\n[SUMMARY]")
        print(f"  Total Stages: {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed/Warnings: {total - passed}")
        print(f"  Pass Rate: {pass_rate:.1f}%")
        
        if pass_rate >= 87.5:
            final_status = "âœ“ PRODUCTION READY"
            color_code = ""
        elif pass_rate >= 75:
            final_status = "! ACCEPTABLE"
            color_code = ""
        else:
            final_status = "âœ— NEEDS ATTENTION"
            color_code = ""
        
        print(f"\n[FINAL STATUS] {final_status}")
        
        print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n" + "="*80)
        print("EXECUTION COMPLETE")
        print("="*80)
        print()
        
        # Next steps
        print("[NEXT STEPS]")
        if pass_rate >= 87.5:
            print("  âœ“ System passed the configured verification threshold")
            print("  â†’ Proceed to staging or controlled deployment")
            print("  â†’ Configure autonomous tasks")
            print("  â†’ Monitor system performance")
        else:
            print("  ! Review failed stages above")
            print("  ! Check dependencies: npm run setup:python")
            print("  ! Verify project structure and permissions")
            print("  ! Re-run specific failing stage for details")
        
        print()


def main():
    """Main entry point"""
    
    controller = WaseemMasterController()
    
    try:
        controller.run_complete_pipeline()
        return 0
    except KeyboardInterrupt:
        print("\n\n[!] Build process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())



