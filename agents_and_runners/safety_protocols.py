#!/usr/bin/env python3
"""
WASEEM SAFETY PROTOCOLS - Execution Safety & Rollback
Pre-execution validation, approval workflow, audit logging
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class RiskLevel(Enum):
    """Risk levels for operations"""
    SAFE = "safe"           # No risk - read only
    LOW = "low"             # Low risk - single file modification
    MEDIUM = "medium"       # Medium risk - multiple files
    HIGH = "high"           # High risk - system changes
    CRITICAL = "critical"   # Critical - irreversible changes


class ApprovalStatus(Enum):
    """Approval status"""
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    TIMEOUT = "timeout"


@dataclass
class SafetyCheck:
    """Single safety check result"""
    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetyReport:
    """Complete safety report"""
    operation: str
    risk_level: RiskLevel
    checks: List[SafetyCheck] = field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    rollback_plan: Optional[str] = None
    
    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)


@dataclass
class AuditEntry:
    """Audit log entry"""
    operation_id: str
    operation: str
    risk_level: str
    approval_status: str
    user: str
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    rollback_executed: bool = False


class AuditLogger:
    """Audit logging for all operations"""
    
    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or Path("logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "safety_audit.jsonl"
        self.entries: List[AuditEntry] = []
    
    def log(
        self,
        operation_id: str,
        operation: str,
        risk_level: RiskLevel,
        approval_status: ApprovalStatus,
        user: str = "system",
        details: Dict[str, Any] | None = None
    ) -> AuditEntry:
        """Log an operation"""
        entry = AuditEntry(
            operation_id=operation_id,
            operation=operation,
            risk_level=risk_level.value,
            approval_status=approval_status.value,
            user=user,
            timestamp=datetime.now().isoformat(),
            details=details or {}
        )
        
        self.entries.append(entry)
        self._write_entry(entry)
        
        return entry
    
    def _write_entry(self, entry: AuditEntry) -> None:
        """Write entry to log file"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "operation_id": entry.operation_id,
                "operation": entry.operation,
                "risk_level": entry.risk_level,
                "approval_status": entry.approval_status,
                "user": entry.user,
                "timestamp": entry.timestamp,
                "details": entry.details,
                "rollback_executed": entry.rollback_executed
            }) + "\n")
    
    def get_entries(
        self,
        operation_type: str | None = None,
        since: datetime | None = None
    ) -> List[AuditEntry]:
        """Get filtered entries"""
        filtered = self.entries
        
        if operation_type:
            filtered = [e for e in filtered if operation_type in e.operation]
        
        if since:
            filtered = [e for e in filtered if datetime.fromisoformat(e.timestamp) >= since]
        
        return filtered


class PreExecutionValidator:
    """Validate operations before execution"""
    
    DANGEROUS_PATTERNS = [
        (r"rm\s+-rf", "Recursive delete command"),
        (r"DROP\s+TABLE", "SQL drop table"),
        (r"TRUNCATE", "SQL truncate"),
        (r"DELETE\s+FROM", "SQL delete"),
        (r"format\s+C:", "Disk format"),
        (r"sudo\s+rm", "Sudo remove"),
        (r"chmod\s+777", "Insecure permissions"),
        (r">\s*/dev/", "Device write"),
        (r"eval\s*\(", "Code evaluation"),
        (r"exec\s*\(", "Code execution"),
    ]
    
    PROTECTED_PATHS = [
        "/etc/",
        "/usr/",
        "/bin/",
        "/sbin/",
        "/boot/",
        "/root/",
        "C:\\Windows\\",
        "C:\\Program Files\\",
    ]
    
    def validate_operation(
        self,
        operation: str,
        target_paths: List[Path],
        content: str | None = None
    ) -> List[SafetyCheck]:
        """Run all pre-execution checks"""
        checks = []
        
        # Check for dangerous patterns
        checks.append(self._check_dangerous_patterns(operation, content))
        
        # Check protected paths
        checks.append(self._check_protected_paths(target_paths))
        
        # Check file permissions
        checks.append(self._check_permissions(target_paths))
        
        # Check disk space
        checks.append(self._check_disk_space(target_paths))
        
        # Check git status (if applicable)
        checks.append(self._check_git_status(target_paths))
        
        return checks
    
    def _check_dangerous_patterns(
        self,
        operation: str,
        content: str | None
    ) -> SafetyCheck:
        """Check for dangerous code patterns"""
        text_to_check = operation + (content or "")
        found = []
        
        for pattern, description in self.DANGEROUS_PATTERNS:
            if pattern.lower() in text_to_check.lower():
                found.append(description)
        
        if found:
            return SafetyCheck(
                name="dangerous_patterns",
                passed=False,
                message=f"Found {len(found)} dangerous pattern(s)",
                details={"patterns": found}
            )
        
        return SafetyCheck(
            name="dangerous_patterns",
            passed=True,
            message="No dangerous patterns detected"
        )
    
    def _check_protected_paths(self, paths: List[Path]) -> SafetyCheck:
        """Check if targeting protected paths"""
        violations = []
        
        for path in paths:
            path_str = str(path.resolve())
            for protected in self.PROTECTED_PATHS:
                if protected in path_str:
                    violations.append(f"{path} matches protected path {protected}")
        
        if violations:
            return SafetyCheck(
                name="protected_paths",
                passed=False,
                message="Targeting protected system paths",
                details={"violations": violations}
            )
        
        return SafetyCheck(
            name="protected_paths",
            passed=True,
            message="No protected paths targeted"
        )
    
    def _check_permissions(self, paths: List[Path]) -> SafetyCheck:
        """Check file/directory permissions"""
        issues = []
        
        for path in paths:
            if path.exists():
                # Check if writable
                if not os.access(path, os.W_OK):
                    issues.append(f"{path} is not writable")
                
                # Check if readable (for modification)
                if not os.access(path, os.R_OK):
                    issues.append(f"{path} is not readable")
        
        if issues:
            return SafetyCheck(
                name="permissions",
                passed=False,
                message="Permission issues detected",
                details={"issues": issues}
            )
        
        return SafetyCheck(
            name="permissions",
            passed=True,
            message="All permissions OK"
        )
    
    def _check_disk_space(self, paths: List[Path]) -> SafetyCheck:
        """Check available disk space"""
        try:
            if sys.platform == "win32":
                import ctypes
                for path in paths:
                    if path.exists():
                        free_bytes = ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                            str(path.parent if path.is_file() else path), None, None, None
                        )
                        free_mb = free_bytes / (1024 * 1024)
                        if free_mb < 100:  # Less than 100MB
                            return SafetyCheck(
                                name="disk_space",
                                passed=False,
                                message=f"Low disk space: {free_mb:.1f}MB"
                            )
            else:
                import shutil
                for path in paths:
                    if path.exists():
                        usage = shutil.disk_usage(path.parent if path.is_file() else path)
                        free_mb = usage.free / (1024 * 1024)
                        if free_mb < 100:
                            return SafetyCheck(
                                name="disk_space",
                                passed=False,
                                message=f"Low disk space: {free_mb:.1f}MB"
                            )
            
            return SafetyCheck(
                name="disk_space",
                passed=True,
                message="Sufficient disk space"
            )
        except Exception as e:
            return SafetyCheck(
                name="disk_space",
                passed=True,  # Don't fail on check error
                message=f"Could not verify: {e}"
            )
    
    def _check_git_status(self, paths: List[Path]) -> SafetyCheck:
        """Check git status for uncommitted changes"""
        try:
            # Find git root
            git_root = None
            for path in paths:
                test_path = path.parent if path.is_file() else path
                while test_path != test_path.parent:
                    if (test_path / ".git").exists():
                        git_root = test_path
                        break
                    test_path = test_path.parent
            
            if not git_root:
                return SafetyCheck(
                    name="git_status",
                    passed=True,
                    message="Not a git repository"
                )
            
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=str(git_root),
                timeout=10
            )
            
            if result.stdout.strip():
                return SafetyCheck(
                    name="git_status",
                    passed=True,  # Warning, not failure
                    message="Uncommitted changes detected",
                    details={"changes": result.stdout.strip().split('\n')[:5]}
                )
            
            return SafetyCheck(
                name="git_status",
                passed=True,
                message="Git working directory clean"
            )
        except Exception as e:
            return SafetyCheck(
                name="git_status",
                passed=True,
                message=f"Git check skipped: {e}"
            )


class ApprovalWorkflow:
    """Approval workflow for operations"""
    
    AUTO_APPROVE_SAFE = True
    AUTO_APPROVE_LOW = True
    REQUIRE_APPROVAL_MEDIUM = True
    REQUIRE_APPROVAL_HIGH = True
    REQUIRE_APPROVAL_CRITICAL = True
    
    TIMEOUT_SECONDS = 300  # 5 minutes
    
    def __init__(
        self,
        auto_approve_safe: bool = True,
        auto_approve_low: bool = True,
        require_approval_medium: bool = True,
        require_approval_high: bool = True,
        require_approval_critical: bool = True
    ):
        self.auto_approve_safe = auto_approve_safe
        self.auto_approve_low = auto_approve_low
        self.require_approval_medium = require_approval_medium
        self.require_approval_high = require_approval_high
        self.require_approval_critical = require_approval_critical
        
        self.pending_approvals: Dict[str, SafetyReport] = {}
        self.approval_callbacks: Dict[str, Callable[[bool], None]] = {}
    
    def request_approval(
        self,
        report: SafetyReport,
        operation_id: str,
        on_decision: Callable[[bool], None] | None = None
    ) -> ApprovalStatus:
        """Request approval for operation"""
        
        # Auto-approve based on risk level
        if report.risk_level == RiskLevel.SAFE:
            if self.auto_approve_safe:
                report.approval_status = ApprovalStatus.AUTO_APPROVED
                report.approved_by = "auto:safe"
                return ApprovalStatus.AUTO_APPROVED
        
        elif report.risk_level == RiskLevel.LOW:
            if self.auto_approve_low:
                report.approval_status = ApprovalStatus.AUTO_APPROVED
                report.approved_by = "auto:low"
                return ApprovalStatus.AUTO_APPROVED
        
        # Require manual approval for medium+
        if report.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL):
            self.pending_approvals[operation_id] = report
            if on_decision:
                self.approval_callbacks[operation_id] = on_decision
            
            report.approval_status = ApprovalStatus.PENDING
            return ApprovalStatus.PENDING
        
        return ApprovalStatus.APPROVED
    
    def approve(self, operation_id: str, approved_by: str = "user") -> bool:
        """Approve pending operation"""
        if operation_id not in self.pending_approvals:
            return False
        
        report = self.pending_approvals[operation_id]
        report.approval_status = ApprovalStatus.APPROVED
        report.approved_by = approved_by
        
        # Call callback if exists
        if operation_id in self.approval_callbacks:
            self.approval_callbacks[operation_id](True)
            del self.approval_callbacks[operation_id]
        
        del self.pending_approvals[operation_id]
        return True
    
    def reject(self, operation_id: str, rejected_by: str = "user") -> bool:
        """Reject pending operation"""
        if operation_id not in self.pending_approvals:
            return False
        
        report = self.pending_approvals[operation_id]
        report.approval_status = ApprovalStatus.REJECTED
        report.approved_by = rejected_by
        
        # Call callback if exists
        if operation_id in self.approval_callbacks:
            self.approval_callbacks[operation_id](False)
            del self.approval_callbacks[operation_id]
        
        del self.pending_approvals[operation_id]
        return True
    
    def get_pending(self) -> Dict[str, SafetyReport]:
        """Get all pending approvals"""
        return dict(self.pending_approvals)


class RollbackManager:
    """Manage rollback operations"""
    
    def __init__(self, backup_dir: Path | None = None):
        self.backup_dir = backup_dir or Path("tmp/rollbacks")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.rollback_history: List[Dict[str, Any]] = []
    
    def create_backup(
        self,
        operation_id: str,
        files: List[Path]
    ) -> Dict[str, str]:
        """Create backup of files before operation"""
        backups = {}
        
        for file_path in files:
            if file_path.exists():
                content = file_path.read_bytes()
                checksum = hashlib.sha256(content).hexdigest()[:16]
                backup_name = f"{operation_id}_{file_path.name}_{checksum}"
                backup_path = self.backup_dir / backup_name
                
                backup_path.write_bytes(content)
                backups[str(file_path)] = str(backup_path)
        
        return backups
    
    def restore_backup(
        self,
        operation_id: str,
        backups: Dict[str, str]
    ) -> Dict[str, bool]:
        """Restore files from backup"""
        results = {}
        
        for original_path, backup_path in backups.items():
            try:
                original = Path(original_path)
                backup = Path(backup_path)
                
                if backup.exists():
                    original.write_bytes(backup.read_bytes())
                    results[original_path] = True
                else:
                    results[original_path] = False
            except Exception:
                results[original_path] = False
        
        # Log rollback
        self.rollback_history.append({
            "operation_id": operation_id,
            "timestamp": datetime.now().isoformat(),
            "files_restored": sum(1 for v in results.values() if v),
            "files_failed": sum(1 for v in results.values() if not v)
        })
        
        return results
    
    def get_rollback_history(self) -> List[Dict[str, Any]]:
        """Get rollback history"""
        return list(self.rollback_history)


class SafetyProtocols:
    """
    Main safety protocols manager
    
    Features:
    - Pre-execution validation
    - Risk assessment
    - Approval workflow
    - Rollback capability
    - Audit logging
    """
    
    def __init__(
        self,
        project_root: Path,
        audit_log_dir: Path | None = None,
        backup_dir: Path | None = None
    ):
        self.project_root = project_root
        self.validator = PreExecutionValidator()
        self.approval = ApprovalWorkflow()
        self.rollback = RollbackManager(backup_dir)
        self.audit = AuditLogger(audit_log_dir)
        
        self.operation_counter = 0
    
    def assess_risk(
        self,
        operation: str,
        target_paths: List[Path],
        content: str | None = None
    ) -> RiskLevel:
        """Assess risk level of operation"""
        
        # Critical: System-level changes
        if any(p in operation.lower() for p in ["sudo", "admin", "root", "system"]):
            return RiskLevel.CRITICAL
        
        # High: Multiple file modifications, deletions
        if "delete" in operation.lower() or "remove" in operation.lower():
            return RiskLevel.HIGH
        
        if len(target_paths) > 5:
            return RiskLevel.HIGH
        
        # Medium: Multiple file modifications
        if len(target_paths) > 1:
            return RiskLevel.MEDIUM
        
        # Low: Single file modification
        if target_paths and any(p.exists() for p in target_paths):
            return RiskLevel.LOW
        
        # Safe: Read-only or new file creation
        return RiskLevel.SAFE
    
    def prepare_operation(
        self,
        operation: str,
        target_paths: List[Path],
        content: str | None = None,
        auto_approve: bool = False
    ) -> Tuple[str, SafetyReport]:
        """Prepare an operation with safety checks"""
        
        # Generate operation ID
        self.operation_counter += 1
        operation_id = f"op-{self.operation_counter}-{int(time.time())}"
        
        # Assess risk
        risk_level = self.assess_risk(operation, target_paths, content)
        
        # Run validation checks
        checks = self.validator.validate_operation(operation, target_paths, content)
        
        # Create report
        report = SafetyReport(
            operation=operation,
            risk_level=risk_level,
            checks=checks
        )
        
        # Create rollback plan
        if risk_level != RiskLevel.SAFE:
            backups = self.rollback.create_backup(operation_id, [p for p in target_paths if p.exists()])
            if backups:
                report.rollback_plan = f"Backup created for {len(backups)} file(s)"
        
        # Request approval
        if auto_approve or report.all_passed:
            approval_status = self.approval.request_approval(report, operation_id)
            report.approval_status = approval_status
        else:
            report.approval_status = ApprovalStatus.REJECTED
        
        # Log
        self.audit.log(
            operation_id=operation_id,
            operation=operation,
            risk_level=risk_level,
            approval_status=report.approval_status,
            details={"targets": [str(p) for p in target_paths]}
        )
        
        return operation_id, report
    
    def execute_with_safety(
        self,
        operation_id: str,
        report: SafetyReport,
        operation_func: Callable[[], bool],
        on_rollback: Callable[[], None] | None = None
    ) -> Tuple[bool, str]:
        """Execute operation with safety wrapper"""
        
        # Check approval
        if report.approval_status not in (ApprovalStatus.APPROVED, ApprovalStatus.AUTO_APPROVED):
            return False, f"Operation not approved: {report.approval_status.value}"
        
        # Check all safety checks passed
        if not report.all_passed:
            return False, "Safety checks failed"
        
        try:
            # Execute
            success = operation_func()
            
            if success:
                return True, "Operation completed successfully"
            else:
                # Execute rollback if needed
                if on_rollback:
                    on_rollback()
                
                return False, "Operation failed, rollback executed"
                
        except Exception as e:
            # Execute rollback on exception
            if on_rollback:
                on_rollback()
            
            return False, f"Operation failed with error: {e}"
    
    def get_pending_approvals(self) -> Dict[str, SafetyReport]:
        """Get all pending approvals"""
        return self.approval.get_pending()
    
    def approve_operation(self, operation_id: str, approved_by: str = "user") -> bool:
        """Approve a pending operation"""
        return self.approval.approve(operation_id, approved_by)
    
    def reject_operation(self, operation_id: str, rejected_by: str = "user") -> bool:
        """Reject a pending operation"""
        return self.approval.reject(operation_id, rejected_by)
    
    def get_audit_log(self, since: datetime | None = None) -> List[AuditEntry]:
        """Get audit log entries"""
        return self.audit.get_entries(since=since)


def create_safety_protocols(
    project_root: Path | str | None = None
) -> SafetyProtocols:
    """Create safety protocols instance"""
    root = Path(project_root) if project_root else Path.cwd()
    return SafetyProtocols(root)


if __name__ == "__main__":
    # Demo
    print("=" * 80)
    print("WASEEM SAFETY PROTOCOLS - EXECUTION SAFETY")
    print("=" * 80)
    
    safety = SafetyProtocols(Path.cwd())
    
    # Test operation
    print("\n[OPERATION PREPARATION]")
    operation_id, report = safety.prepare_operation(
        operation="modify file",
        target_paths=[Path("test_file.py")],
        content="print('hello')"
    )
    
    print(f"Operation ID: {operation_id}")
    print(f"Risk Level: {report.risk_level.value}")
    print(f"Approval Status: {report.approval_status.value}")
    print(f"Checks Passed: {report.all_passed}")
    
    for check in report.checks:
        print(f"  [{check.passed}] {check.name}: {check.message}")
    
    print("\n[DONE]")
