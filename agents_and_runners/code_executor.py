#!/usr/bin/env python3
"""
WASEEM CODE EXECUTOR - Safe Code Execution with Rollback
Real code modification, test execution, validation gates
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ExecutionMode(Enum):
    """Execution modes"""
    DRY_RUN = "dry_run"       # No actual changes
    SAFE = "safe"             # Changes with rollback
    DIRECT = "direct"         # Direct changes (use with caution)


class ExecutionStatus(Enum):
    """Status of execution"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


@dataclass
class FileSnapshot:
    """Snapshot of file before modification"""
    path: str
    content: str
    checksum: str
    exists: bool
    timestamp: str


@dataclass
class ExecutionResult:
    """Result of code execution"""
    success: bool
    status: ExecutionStatus
    message: str
    files_modified: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    output: str = ""
    error: Optional[str] = None
    rollback_available: bool = False
    execution_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ValidationReport:
    """Report from validation checks"""
    passed: bool
    checks: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class SyntaxValidator:
    """Validate code syntax before execution"""
    
    @staticmethod
    def validate_python(code: str) -> Tuple[bool, Optional[str]]:
        """Validate Python syntax"""
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
    
    @staticmethod
    def validate_javascript(code: str) -> Tuple[bool, Optional[str]]:
        """Basic JavaScript validation"""
        # Check for common syntax issues
        issues = []
        
        # Check balanced braces
        if code.count('{') != code.count('}'):
            issues.append("Unbalanced braces")
        
        # Check balanced parentheses
        if code.count('(') != code.count(')'):
            issues.append("Unbalanced parentheses")
        
        # Check balanced brackets
        if code.count('[') != code.count(']'):
            issues.append("Unbalanced brackets")
        
        if issues:
            return False, "; ".join(issues)
        return True, None
    
    @staticmethod
    def validate_typescript(code: str) -> Tuple[bool, Optional[str]]:
        """Basic TypeScript validation (same as JS for now)"""
        return SyntaxValidator.validate_javascript(code)
    
    def validate(self, code: str, language: str) -> Tuple[bool, Optional[str]]:
        """Validate code based on language"""
        validators = {
            "python": self.validate_python,
            "javascript": self.validate_javascript,
            "typescript": self.validate_typescript,
            "js": self.validate_javascript,
            "ts": self.validate_typescript,
            "py": self.validate_python,
        }
        
        validator = validators.get(language.lower())
        if validator:
            return validator(code)
        
        # Unknown language - skip validation
        return True, None


class FileBackup:
    """Manage file backups for rollback"""
    
    def __init__(self, backup_dir: Path | None = None):
        self.backup_dir = backup_dir or Path(tempfile.mkdtemp(prefix="waseem_backup_"))
        self.snapshots: Dict[str, FileSnapshot] = {}
    
    def create_snapshot(self, file_path: Path) -> FileSnapshot:
        """Create snapshot of file"""
        path_str = str(file_path.resolve())
        
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
            exists = True
        else:
            content = ""
            checksum = ""
            exists = False
        
        snapshot = FileSnapshot(
            path=path_str,
            content=content,
            checksum=checksum,
            exists=exists,
            timestamp=datetime.now().isoformat()
        )
        
        self.snapshots[path_str] = snapshot
        
        # Also save to backup file
        if exists:
            backup_path = self.backup_dir / f"{checksum}_{file_path.name}"
            backup_path.write_text(content)
        
        return snapshot
    
    def restore_snapshot(self, file_path: Path) -> bool:
        """Restore file from snapshot"""
        path_str = str(file_path.resolve())
        
        if path_str not in self.snapshots:
            return False
        
        snapshot = self.snapshots[path_str]
        
        try:
            if snapshot.exists:
                file_path.write_text(snapshot.content)
            else:
                # File didn't exist, delete if created
                if file_path.exists():
                    file_path.unlink()
            
            return True
        except Exception:
            return False
    
    def restore_all(self) -> Dict[str, bool]:
        """Restore all files from snapshots"""
        results = {}
        for path_str in self.snapshots:
            results[path_str] = self.restore_snapshot(Path(path_str))
        return results
    
    def clear_snapshots(self) -> None:
        """Clear all snapshots"""
        self.snapshots.clear()
        # Clean backup directory
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir, ignore_errors=True)


class TestRunner:
    """Run tests and capture results"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def run_python_tests(
        self,
        test_path: str | None = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Run Python tests with pytest"""
        test_dir = self.project_root / "tests" if test_path is None else self.project_root / test_path
        
        if not test_dir.exists():
            return {"error": "Test directory not found", "tests_run": 0}
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=short", "-q"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.project_root)
            )
            
            output = result.stdout + result.stderr
            
            # Parse results
            passed = len(re.findall(r'(\d+) passed', output))
            failed = len(re.findall(r'(\d+) failed', output))
            errors = len(re.findall(r'(\d+) error', output))
            
            return {
                "success": result.returncode == 0,
                "tests_run": passed + failed + errors,
                "tests_passed": passed,
                "tests_failed": failed + errors,
                "output": output,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "Test execution timed out", "tests_run": 0}
        except Exception as e:
            return {"error": str(e), "tests_run": 0}
    
    def run_node_tests(
        self,
        test_path: str | None = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Run Node.js tests"""
        try:
            # Check for npm or pnpm
            package_manager = "pnpm" if (self.project_root / "pnpm-lock.yaml").exists() else "npm"
            
            cmd = [package_manager, "test"]
            if test_path:
                cmd.extend(["--", test_path])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.project_root)
            )
            
            output = result.stdout + result.stderr
            
            # Parse results (varies by test framework)
            passed = len(re.findall(r'(\d+) passing', output)) or len(re.findall(r'(\d+) passed', output))
            failed = len(re.findall(r'(\d+) failing', output)) or len(re.findall(r'(\d+) failed', output))
            
            return {
                "success": result.returncode == 0,
                "tests_run": passed + failed,
                "tests_passed": passed,
                "tests_failed": failed,
                "output": output,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "Test execution timed out", "tests_run": 0}
        except Exception as e:
            return {"error": str(e), "tests_run": 0}


class CodeExecutor:
    """
    Safe code execution with validation, backup, and rollback
    
    Features:
    - Syntax validation before execution
    - File snapshots for rollback
    - Test execution
    - Dry-run mode
    - Audit logging
    """
    
    def __init__(
        self,
        project_root: Path,
        mode: ExecutionMode = ExecutionMode.SAFE
    ):
        self.project_root = Path(project_root)
        self.mode = mode
        self.validator = SyntaxValidator()
        self.backup = FileBackup()
        self.test_runner = TestRunner(self.project_root)
        self.execution_log: List[ExecutionResult] = []
    
    def validate_code(
        self,
        code: str,
        language: str = "python"
    ) -> ValidationReport:
        """Validate code before execution"""
        report = ValidationReport(passed=True)
        
        # Syntax check
        syntax_ok, syntax_error = self.validator.validate(code, language)
        report.checks.append({
            "name": "syntax",
            "passed": syntax_ok,
            "message": syntax_error or "Syntax valid"
        })
        
        if not syntax_ok:
            report.passed = False
            report.errors.append(syntax_error)
        
        # Security checks
        security_issues = self._security_check(code, language)
        if security_issues:
            report.warnings.extend(security_issues)
            report.checks.append({
                "name": "security",
                "passed": True,  # Warnings don't fail
                "message": f"Found {len(security_issues)} potential issues"
            })
        
        # Complexity check
        complexity = self._complexity_check(code)
        if complexity > 20:
            report.warnings.append(f"High complexity: {complexity}")
        
        return report
    
    def _security_check(self, code: str, language: str) -> List[str]:
        """Basic security checks"""
        issues = []
        
        dangerous_patterns = [
            (r"eval\s*\(", "Use of eval() is dangerous"),
            (r"exec\s*\(", "Use of exec() is dangerous"),
            (r"__import__\s*\(", "Dynamic imports can be dangerous"),
            (r"subprocess\.call\s*\([^)]*shell=True", "Shell=True in subprocess"),
            (r"os\.system\s*\(", "os.system can be dangerous"),
        ]
        
        for pattern, message in dangerous_patterns:
            if re.search(pattern, code):
                issues.append(message)
        
        return issues
    
    def _complexity_check(self, code: str) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        for keyword in ['if', 'elif', 'for', 'while', 'and', 'or', 'except']:
            complexity += len(re.findall(rf'\b{keyword}\b', code))
        return complexity
    
    def write_file(
        self,
        file_path: Path,
        content: str,
        validate: bool = True,
        create_dirs: bool = True
    ) -> ExecutionResult:
        """Write content to file with safety checks"""
        start_time = time.time()
        
        # Resolve path
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        # Validate if requested
        if validate:
            language = file_path.suffix.lstrip('.')
            report = self.validate_code(content, language)
            if not report.passed:
                return ExecutionResult(
                    success=False,
                    status=ExecutionStatus.SKIPPED,
                    message="Validation failed",
                    errors=report.errors
                )
        
        # Dry run mode
        if self.mode == ExecutionMode.DRY_RUN:
            return ExecutionResult(
                success=True,
                status=ExecutionStatus.SKIPPED,
                message="Dry run - no changes made",
                rollback_available=False,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Create snapshot for rollback
        if self.mode == ExecutionMode.SAFE:
            self.backup.create_snapshot(file_path)
        
        try:
            # Create directories if needed
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            file_path.write_text(content, encoding="utf-8")
            
            result = ExecutionResult(
                success=True,
                status=ExecutionStatus.SUCCESS,
                message=f"File written: {file_path}",
                files_modified=[str(file_path)] if file_path.exists() else [],
                files_created=[str(file_path)] if not self.backup.snapshots.get(str(file_path), FileSnapshot(path="", content="", checksum="", exists=False, timestamp="")).exists else [],
                rollback_available=self.mode == ExecutionMode.SAFE,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
            self.execution_log.append(result)
            return result
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.FAILED,
                message="Failed to write file",
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def modify_file(
        self,
        file_path: Path,
        old_content: str,
        new_content: str,
        validate: bool = True
    ) -> ExecutionResult:
        """Modify specific content in file"""
        # Resolve path
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        if not file_path.exists():
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.FAILED,
                message="File does not exist",
                error=str(file_path)
            )
        
        current_content = file_path.read_text(encoding="utf-8")
        
        if old_content not in current_content:
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.FAILED,
                message="Old content not found in file"
            )
        
        modified = current_content.replace(old_content, new_content, 1)
        return self.write_file(file_path, modified, validate, create_dirs=False)
    
    def delete_file(self, file_path: Path) -> ExecutionResult:
        """Delete file with backup"""
        start_time = time.time()
        
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        if not file_path.exists():
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.SKIPPED,
                message="File does not exist"
            )
        
        # Dry run
        if self.mode == ExecutionMode.DRY_RUN:
            return ExecutionResult(
                success=True,
                status=ExecutionStatus.SKIPPED,
                message="Dry run - no changes made"
            )
        
        # Create snapshot
        if self.mode == ExecutionMode.SAFE:
            self.backup.create_snapshot(file_path)
        
        try:
            file_path.unlink()
            
            result = ExecutionResult(
                success=True,
                status=ExecutionStatus.SUCCESS,
                message=f"File deleted: {file_path}",
                files_deleted=[str(file_path)],
                rollback_available=self.mode == ExecutionMode.SAFE,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
            self.execution_log.append(result)
            return result
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.FAILED,
                message="Failed to delete file",
                error=str(e)
            )
    
    def run_tests(
        self,
        test_type: str = "python",
        test_path: str | None = None
    ) -> ExecutionResult:
        """Run tests and return results"""
        start_time = time.time()
        
        if test_type == "python":
            result = self.test_runner.run_python_tests(test_path)
        else:
            result = self.test_runner.run_node_tests(test_path)
        
        if "error" in result:
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.FAILED,
                message="Test execution failed",
                error=result["error"],
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        return ExecutionResult(
            success=result.get("success", False),
            status=ExecutionStatus.SUCCESS if result.get("success") else ExecutionStatus.FAILED,
            message=f"Tests: {result.get('tests_passed', 0)} passed, {result.get('tests_failed', 0)} failed",
            tests_run=result.get("tests_run", 0),
            tests_passed=result.get("tests_passed", 0),
            tests_failed=result.get("tests_failed", 0),
            output=result.get("output", ""),
            execution_time_ms=(time.time() - start_time) * 1000
        )
    
    def rollback(self) -> ExecutionResult:
        """Rollback all changes"""
        start_time = time.time()
        
        if not self.backup.snapshots:
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.SKIPPED,
                message="No snapshots to rollback"
            )
        
        results = self.backup.restore_all()
        
        success = all(results.values())
        restored_files = [k for k, v in results.items() if v]
        failed_files = [k for k, v in results.items() if not v]
        
        result = ExecutionResult(
            success=success,
            status=ExecutionStatus.ROLLED_BACK,
            message=f"Rolled back {len(restored_files)} files",
            files_modified=restored_files,
            error=f"Failed to restore: {failed_files}" if failed_files else None,
            execution_time_ms=(time.time() - start_time) * 1000
        )
        
        self.execution_log.append(result)
        return result
    
    def diff(self, file_path: Path) -> str:
        """Show diff between current and snapshot"""
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        path_str = str(file_path)
        if path_str not in self.backup.snapshots:
            return "No snapshot available"
        
        snapshot = self.backup.snapshots[path_str]
        current = file_path.read_text() if file_path.exists() else ""
        
        diff = difflib.unified_diff(
            snapshot.content.splitlines(keepends=True),
            current.splitlines(keepends=True),
            fromfile=f"{file_path.name} (original)",
            tofile=f"{file_path.name} (current)"
        )
        
        return "".join(diff)
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Get execution log as list of dicts"""
        return [
            {
                "success": r.success,
                "status": r.status.value,
                "message": r.message,
                "files_modified": r.files_modified,
                "timestamp": r.timestamp,
                "execution_time_ms": r.execution_time_ms
            }
            for r in self.execution_log
        ]
    
    def clear_log(self) -> None:
        """Clear execution log"""
        self.execution_log.clear()


def create_executor(
    project_root: Path | str | None = None,
    mode: ExecutionMode = ExecutionMode.SAFE
) -> CodeExecutor:
    """Create a code executor instance"""
    root = Path(project_root) if project_root else Path.cwd()
    return CodeExecutor(root, mode)


if __name__ == "__main__":
    # Demo
    print("=" * 80)
    print("WASEEM CODE EXECUTOR - SAFE CODE EXECUTION")
    print("=" * 80)
    
    # Create executor in dry-run mode
    executor = create_executor(mode=ExecutionMode.DRY_RUN)
    
    # Test validation
    test_code = '''
def hello(name: str) -> str:
    """Say hello"""
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(hello("World"))
'''
    
    print("\n[VALIDATION TEST]")
    report = executor.validate_code(test_code, "python")
    print(f"  Passed: {report.passed}")
    print(f"  Checks: {len(report.checks)}")
    if report.warnings:
        print(f"  Warnings: {report.warnings}")
    
    # Test write (dry run)
    print("\n[WRITE TEST - DRY RUN]")
    result = executor.write_file(
        Path("test_output.py"),
        test_code,
        validate=True
    )
    print(f"  Success: {result.success}")
    print(f"  Status: {result.status.value}")
    print(f"  Message: {result.message}")
    
    print("\n[DONE]")
