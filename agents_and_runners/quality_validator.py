#!/usr/bin/env python3
"""
WASEEM QUALITY VALIDATOR - Google/NASA Code Standards
PEP 8, type hints, complexity, documentation, test coverage
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class QualityIssue:
    """Single quality issue"""
    rule_id: str
    severity: str  # error, warning, info
    message: str
    location: str
    line: int
    column: int = 0
    suggestion: Optional[str] = None


@dataclass
class QualityReport:
    """Complete quality report"""
    file_path: str
    passed: bool
    score: float  # 0-100
    issues: List[QualityIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""


class PEP8Validator:
    """PEP 8 style validation"""
    
    MAX_LINE_LENGTH = 100
    INDENT_SIZE = 4
    
    # Naming conventions
    CLASS_PATTERN = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
    FUNCTION_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')
    CONSTANT_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]*$')
    PRIVATE_PATTERN = re.compile(r'^_[a-z][a-z0-9_]*$')
    
    def validate(self, code: str, file_path: str) -> List[QualityIssue]:
        """Validate PEP 8 compliance"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Line length
            if len(line) > self.MAX_LINE_LENGTH:
                issues.append(QualityIssue(
                    rule_id="E501",
                    severity="warning",
                    message=f"Line too long ({len(line)} > {self.MAX_LINE_LENGTH})",
                    location=file_path,
                    line=i,
                    suggestion="Break line or use shorter names"
                ))
            
            # Trailing whitespace
            if line.rstrip() != line and line.strip():
                issues.append(QualityIssue(
                    rule_id="W291",
                    severity="warning",
                    message="Trailing whitespace",
                    location=file_path,
                    line=i
                ))
            
            # Mixed tabs and spaces
            if '\t' in line and line.startswith(' '):
                issues.append(QualityIssue(
                    rule_id="E101",
                    severity="error",
                    message="Indentation contains mixed spaces and tabs",
                    location=file_path,
                    line=i
                ))
        
        return issues
    
    def validate_naming(self, code: str, file_path: str) -> List[QualityIssue]:
        """Validate naming conventions"""
        issues = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # Class names
                if isinstance(node, ast.ClassDef):
                    if not self.CLASS_PATTERN.match(node.name):
                        issues.append(QualityIssue(
                            rule_id="N801",
                            severity="error",
                            message=f"Class name '{node.name}' should use CapWords convention",
                            location=file_path,
                            line=node.lineno
                        ))
                
                # Function names
                elif isinstance(node, ast.FunctionDef):
                    if not self.FUNCTION_PATTERN.match(node.name) and not node.name.startswith('_'):
                        issues.append(QualityIssue(
                            rule_id="N802",
                            severity="error",
                            message=f"Function name '{node.name}' should be lowercase",
                            location=file_path,
                            line=node.lineno
                        ))
                
                # Variable names in assignments
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            name = target.id
                            # Check for camelCase (should be snake_case)
                            if re.search(r'[a-z][A-Z]', name) and not name.startswith('_'):
                                issues.append(QualityIssue(
                                    rule_id="N816",
                                    severity="warning",
                                    message=f"Variable '{name}' should be snake_case",
                                    location=file_path,
                                    line=node.lineno
                                ))
        except SyntaxError:
            pass
        
        return issues


class TypeHintValidator:
    """Type hint validation"""
    
    def validate(self, code: str, file_path: str) -> List[QualityIssue]:
        """Validate type hints presence"""
        issues = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check return type hint
                    if node.returns is None and not node.name.startswith('_'):
                        # Skip __init__ and private methods
                        if node.name != '__init__':
                            issues.append(QualityIssue(
                                rule_id="T001",
                                severity="warning",
                                message=f"Function '{node.name}' missing return type hint",
                                location=file_path,
                                line=node.lineno,
                                suggestion="Add -> ReturnType annotation"
                            ))
                    
                    # Check parameter type hints
                    for arg in node.args.args:
                        if arg.annotation is None and arg.arg != 'self' and arg.arg != 'cls':
                            issues.append(QualityIssue(
                                rule_id="T002",
                                severity="info",
                                message=f"Parameter '{arg.arg}' in '{node.name}' missing type hint",
                                location=file_path,
                                line=node.lineno,
                                suggestion=f"Add type: {arg.arg}: Type"
                            ))
        except SyntaxError:
            pass
        
        return issues
    
    def calculate_coverage(self, code: str) -> float:
        """Calculate type hint coverage percentage"""
        try:
            tree = ast.parse(code)
            total_params = 0
            typed_params = 0
            total_returns = 0
            typed_returns = 0
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Count parameters
                    for arg in node.args.args:
                        if arg.arg not in ('self', 'cls'):
                            total_params += 1
                            if arg.annotation is not None:
                                typed_params += 1
                    
                    # Count returns
                    if node.name != '__init__':
                        total_returns += 1
                        if node.returns is not None:
                            typed_returns += 1
            
            if total_params + total_returns == 0:
                return 100.0
            
            coverage = (typed_params + typed_returns) / (total_params + total_returns) * 100
            return round(coverage, 1)
        except SyntaxError:
            return 0.0


class ComplexityValidator:
    """Code complexity validation"""
    
    MAX_CYCLOMATIC = 10
    MAX_COGNITIVE = 15
    MAX_FUNCTION_LINES = 50
    MAX_CLASS_LINES = 300
    MAX_NESTING = 4
    
    def validate(self, code: str, file_path: str) -> List[QualityIssue]:
        """Validate complexity limits"""
        issues = []
        
        try:
            tree = ast.parse(code)
            lines = code.split('\n')
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Function length
                    func_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
                    if func_lines > self.MAX_FUNCTION_LINES:
                        issues.append(QualityIssue(
                            rule_id="C001",
                            severity="warning",
                            message=f"Function '{node.name}' too long ({func_lines} lines)",
                            location=file_path,
                            line=node.lineno,
                            suggestion="Break into smaller functions"
                        ))
                    
                    # Cyclomatic complexity
                    cc = self._cyclomatic_complexity(node)
                    if cc > self.MAX_CYCLOMATIC:
                        issues.append(QualityIssue(
                            rule_id="C002",
                            severity="error",
                            message=f"Function '{node.name}' too complex (CC={cc})",
                            location=file_path,
                            line=node.lineno,
                            suggestion="Reduce branching or extract methods"
                        ))
                    
                    # Nesting depth
                    nesting = self._nesting_depth(node)
                    if nesting > self.MAX_NESTING:
                        issues.append(QualityIssue(
                            rule_id="C003",
                            severity="warning",
                            message=f"Function '{node.name}' deeply nested (depth={nesting})",
                            location=file_path,
                            line=node.lineno,
                            suggestion="Extract nested logic to separate functions"
                        ))
                
                elif isinstance(node, ast.ClassDef):
                    # Class length
                    class_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
                    if class_lines > self.MAX_CLASS_LINES:
                        issues.append(QualityIssue(
                            rule_id="C004",
                            severity="warning",
                            message=f"Class '{node.name}' too large ({class_lines} lines)",
                            location=file_path,
                            line=node.lineno,
                            suggestion="Consider splitting class"
                        ))
        except SyntaxError:
            pass
        
        return issues
    
    def _cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity for function"""
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _nesting_depth(self, node: ast.FunctionDef, current: int = 0) -> int:
        """Calculate maximum nesting depth"""
        max_depth = current
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With)):
                child_depth = self._nesting_depth(child, current + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._nesting_depth(child, current)
                max_depth = max(max_depth, child_depth)
        
        return max_depth


class DocumentationValidator:
    """Documentation validation"""
    
    MIN_DOCSTRING_LENGTH = 10
    DOCSTRING_PATTERN = re.compile(r'"""[\s\S]*?"""', re.MULTILINE)
    
    def validate(self, code: str, file_path: str) -> List[QualityIssue]:
        """Validate documentation"""
        issues = []
        
        try:
            tree = ast.parse(code)
            
            # Module docstring
            if not tree.body or not isinstance(tree.body[0], ast.Expr):
                issues.append(QualityIssue(
                    rule_id="D001",
                    severity="warning",
                    message="Missing module docstring",
                    location=file_path,
                    line=1,
                    suggestion='Add module docstring at the top: """Description"""'
                ))
            
            for node in ast.walk(tree):
                # Class docstrings
                if isinstance(node, ast.ClassDef):
                    if not self._has_docstring(node):
                        issues.append(QualityIssue(
                            rule_id="D002",
                            severity="warning",
                            message=f"Class '{node.name}' missing docstring",
                            location=file_path,
                            line=node.lineno
                        ))
                
                # Function docstrings
                elif isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_') and not self._has_docstring(node):
                        issues.append(QualityIssue(
                            rule_id="D003",
                            severity="info",
                            message=f"Function '{node.name}' missing docstring",
                            location=file_path,
                            line=node.lineno
                        ))
        except SyntaxError:
            pass
        
        return issues
    
    def _has_docstring(self, node: ast.AST) -> bool:
        """Check if node has docstring"""
        if not hasattr(node, 'body') or not node.body:
            return False
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            return isinstance(first.value.value, str) and len(first.value.value) >= self.MIN_DOCSTRING_LENGTH
        return False
    
    def calculate_coverage(self, code: str) -> float:
        """Calculate documentation coverage"""
        try:
            tree = ast.parse(code)
            total = 0
            documented = 0
            
            # Count public functions and classes
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    if not node.name.startswith('_'):
                        total += 1
                        if self._has_docstring(node):
                            documented += 1
            
            if total == 0:
                return 100.0
            
            return round(documented / total * 100, 1)
        except SyntaxError:
            return 0.0


class TestCoverageValidator:
    """Test coverage validation"""
    
    MIN_COVERAGE = 80
    
    def validate_coverage(self, coverage_percent: float, file_path: str) -> List[QualityIssue]:
        """Validate test coverage percentage"""
        issues = []
        
        if coverage_percent < self.MIN_COVERAGE:
            issues.append(QualityIssue(
                rule_id="TC001",
                severity="warning",
                message=f"Test coverage {coverage_percent}% below minimum {self.MIN_COVERAGE}%",
                location=file_path,
                line=0,
                suggestion="Add more unit tests"
            ))
        
        return issues


class QualityValidator:
    """
    Main quality validator combining all checks
    
    Standards:
    - PEP 8 compliance
    - Type hint coverage > 80%
    - Cyclomatic complexity < 10
    - Documentation coverage > 80%
    - Test coverage > 90%
    """
    
    def __init__(self):
        self.pep8 = PEP8Validator()
        self.type_hints = TypeHintValidator()
        self.complexity = ComplexityValidator()
        self.documentation = DocumentationValidator()
        self.test_coverage = TestCoverageValidator()
    
    def validate_file(
        self,
        file_path: Path,
        code: str | None = None
    ) -> QualityReport:
        """Validate a single file"""
        
        if code is None:
            if not file_path.exists():
                return QualityReport(
                    file_path=str(file_path),
                    passed=False,
                    score=0,
                    summary="File not found"
                )
            code = file_path.read_text(encoding="utf-8", errors="ignore")
        
        all_issues = []
        metrics = {}
        
        # PEP 8
        all_issues.extend(self.pep8.validate(code, str(file_path)))
        all_issues.extend(self.pep8.validate_naming(code, str(file_path)))
        
        # Type hints
        all_issues.extend(self.type_hints.validate(code, str(file_path)))
        metrics["type_hint_coverage"] = self.type_hints.calculate_coverage(code)
        
        # Complexity
        all_issues.extend(self.complexity.validate(code, str(file_path)))
        
        # Documentation
        all_issues.extend(self.documentation.validate(code, str(file_path)))
        metrics["doc_coverage"] = self.documentation.calculate_coverage(code)
        
        # Calculate score
        score = self._calculate_score(all_issues, metrics)
        
        # Determine pass/fail
        errors = [i for i in all_issues if i.severity == "error"]
        passed = len(errors) == 0 and score >= 70
        
        # Generate summary
        summary = self._generate_summary(all_issues, metrics)
        
        return QualityReport(
            file_path=str(file_path),
            passed=passed,
            score=score,
            issues=all_issues,
            metrics=metrics,
            summary=summary
        )
    
    def _calculate_score(
        self,
        issues: List[QualityIssue],
        metrics: Dict[str, Any]
    ) -> float:
        """Calculate quality score (0-100)"""
        score = 100.0
        
        # Deduct for issues
        for issue in issues:
            if issue.severity == "error":
                score -= 5
            elif issue.severity == "warning":
                score -= 2
            else:
                score -= 0.5
        
        # Deduct for low coverage
        type_coverage = metrics.get("type_hint_coverage", 100)
        if type_coverage < 80:
            score -= (80 - type_coverage) * 0.2
        
        doc_coverage = metrics.get("doc_coverage", 100)
        if doc_coverage < 80:
            score -= (80 - doc_coverage) * 0.2
        
        return max(0, min(100, score))
    
    def _generate_summary(
        self,
        issues: List[QualityIssue],
        metrics: Dict[str, Any]
    ) -> str:
        """Generate summary text"""
        errors = len([i for i in issues if i.severity == "error"])
        warnings = len([i for i in issues if i.severity == "warning"])
        infos = len([i for i in issues if i.severity == "info"])
        
        parts = [f"{errors} errors, {warnings} warnings, {infos} info"]
        
        if "type_hint_coverage" in metrics:
            parts.append(f"Type hints: {metrics['type_hint_coverage']}%")
        
        if "doc_coverage" in metrics:
            parts.append(f"Docs: {metrics['doc_coverage']}%")
        
        return " | ".join(parts)
    
    def validate_project(
        self,
        project_root: Path,
        file_patterns: List[str] = None
    ) -> Dict[str, QualityReport]:
        """Validate all Python files in project"""
        
        if file_patterns is None:
            file_patterns = ["*.py"]
        
        reports = {}
        
        for pattern in file_patterns:
            for file_path in project_root.rglob(pattern):
                # Skip common exclusions
                if any(part in str(file_path) for part in ['__pycache__', '.venv', 'venv', 'node_modules', 'dist', 'build']):
                    continue
                
                report = self.validate_file(file_path)
                reports[str(file_path.relative_to(project_root))] = report
        
        return reports
    
    def get_project_summary(
        self,
        reports: Dict[str, QualityReport]
    ) -> Dict[str, Any]:
        """Get project-wide summary"""
        
        total_files = len(reports)
        passed_files = sum(1 for r in reports.values() if r.passed)
        total_issues = sum(len(r.issues) for r in reports.values())
        errors = sum(1 for r in reports.values() for i in r.issues if i.severity == "error")
        warnings = sum(1 for r in reports.values() for i in r.issues if i.severity == "warning")
        
        avg_score = sum(r.score for r in reports.values()) / total_files if total_files > 0 else 0
        
        avg_type_coverage = sum(
            r.metrics.get("type_hint_coverage", 0) for r in reports.values()
        ) / total_files if total_files > 0 else 0
        
        avg_doc_coverage = sum(
            r.metrics.get("doc_coverage", 0) for r in reports.values()
        ) / total_files if total_files > 0 else 0
        
        return {
            "total_files": total_files,
            "passed_files": passed_files,
            "pass_rate": round(passed_files / total_files * 100, 1) if total_files > 0 else 0,
            "total_issues": total_issues,
            "errors": errors,
            "warnings": warnings,
            "average_score": round(avg_score, 1),
            "average_type_coverage": round(avg_type_coverage, 1),
            "average_doc_coverage": round(avg_doc_coverage, 1)
        }


def validate_file(file_path: Path | str) -> QualityReport:
    """Convenience function to validate a file"""
    validator = QualityValidator()
    return validator.validate_file(Path(file_path))


if __name__ == "__main__":
    # Demo
    print("=" * 80)
    print("WASEEM QUALITY VALIDATOR - GOOGLE/NASA STANDARDS")
    print("=" * 80)
    
    validator = QualityValidator()
    
    # Test code with issues
    test_code = '''
def processData(data, config):
    result = []
    for item in data:
        if item:
            if item.value > 0:
                if item.active:
                    result.append(item)
    return result

class dataProcessor:
    def __init__(self):
        self.data = []
    
    def process(self, item):
        return item
'''
    
    print("\n[VALIDATION TEST]")
    report = validator.validate_file(Path("test.py"), test_code)
    
    print(f"\nFile: {report.file_path}")
    print(f"Passed: {report.passed}")
    print(f"Score: {report.score}")
    print(f"Summary: {report.summary}")
    print(f"\nMetrics:")
    for k, v in report.metrics.items():
        print(f"  {k}: {v}")
    
    print(f"\nIssues ({len(report.issues)}):")
    for issue in report.issues[:10]:
        print(f"  [{issue.severity}] Line {issue.line}: {issue.message}")
    
    print("\n[DONE]")
