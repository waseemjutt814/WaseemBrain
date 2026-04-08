#!/usr/bin/env python3
"""
WASEEM FEEDBACK LOOP - Correction & Improvement System
Error detection, correction suggestions, performance tracking
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FeedbackEntry:
    """Single feedback entry"""
    feedback_id: str
    operation: str
    result: str  # success, partial, failure
    message: str
    correction: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrectionSuggestion:
    """Suggested correction"""
    suggestion_id: str
    issue_type: str
    description: str
    suggested_fix: str
    confidence: float
    examples: List[str] = field(default_factory=list)
    auto_applicable: bool = False


@dataclass
class PerformanceMetric:
    """Performance metric tracking"""
    metric_name: str
    current_value: float
    previous_value: float
    trend: str  # improving, stable, declining
    target: Optional[float] = None
    history: List[float] = field(default_factory=list)


class ErrorDetector:
    """Detect and categorize errors"""
    
    ERROR_PATTERNS = {
        "syntax": [
            r"SyntaxError",
            r"IndentationError",
            r"TabError",
            r"unexpected token",
        ],
        "runtime": [
            r"RuntimeError",
            r"TypeError",
            r"ValueError",
            r"KeyError",
            r"IndexError",
            r"AttributeError",
        ],
        "import": [
            r"ImportError",
            r"ModuleNotFoundError",
            r"No module named",
        ],
        "permission": [
            r"PermissionError",
            r"AccessDenied",
            r"forbidden",
        ],
        "resource": [
            r"MemoryError",
            r"TimeoutError",
            r"ConnectionError",
            r"OSError",
        ],
        "logic": [
            r"AssertionError",
            r"Failed assertion",
            r"Expected.*but got",
        ],
    }
    
    def detect(self, error_message: str) -> Tuple[str, str, float]:
        """
        Detect error type from message
        
        Returns: (category, specific_type, confidence)
        """
        error_lower = error_message.lower()
        
        for category, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in error_lower:
                    return category, pattern, 0.9
        
        # Unknown error
        return "unknown", "unclassified", 0.3
    
    def get_severity(self, error_type: str) -> str:
        """Get severity level for error type"""
        high_severity = ["runtime", "resource", "permission"]
        medium_severity = ["import", "logic"]
        
        if error_type in high_severity:
            return "high"
        elif error_type in medium_severity:
            return "medium"
        return "low"


class CorrectionGenerator:
    """Generate correction suggestions"""
    
    CORRECTION_TEMPLATES = {
        "syntax": {
            "SyntaxError": "Check for missing parentheses, brackets, or quotes",
            "IndentationError": "Ensure consistent indentation (4 spaces recommended)",
            "unexpected token": "Review syntax around the error location",
        },
        "runtime": {
            "TypeError": "Verify argument types match function expectations",
            "ValueError": "Validate input values before processing",
            "KeyError": "Check if key exists before accessing dictionary",
            "IndexError": "Verify index is within bounds of sequence",
            "AttributeError": "Confirm object has the requested attribute",
        },
        "import": {
            "ImportError": "Ensure module is installed: pip install <module>",
            "ModuleNotFoundError": "Check module name and installation",
        },
        "permission": {
            "PermissionError": "Run with appropriate permissions or check file ownership",
        },
        "resource": {
            "MemoryError": "Reduce data size or process in chunks",
            "TimeoutError": "Increase timeout or optimize performance",
            "ConnectionError": "Check network connectivity and retry",
        },
    }
    
    def generate(
        self,
        error_category: str,
        error_type: str,
        context: Dict[str, Any] | None = None
    ) -> CorrectionSuggestion:
        """Generate correction suggestion"""
        
        # Get template suggestion
        templates = self.CORRECTION_TEMPLATES.get(error_category, {})
        suggested_fix = templates.get(error_type, "Review the error and adjust code accordingly")
        
        # Determine if auto-applicable
        auto_applicable = error_category in ["syntax", "import"]
        
        # Build confidence based on category
        confidence_scores = {
            "syntax": 0.9,
            "import": 0.85,
            "runtime": 0.7,
            "permission": 0.6,
            "resource": 0.5,
            "unknown": 0.3,
        }
        confidence = confidence_scores.get(error_category, 0.5)
        
        return CorrectionSuggestion(
            suggestion_id=f"corr-{error_category}-{error_type}-{int(datetime.now().timestamp())}",
            issue_type=error_type,
            description=f"{error_category} error: {error_type}",
            suggested_fix=suggested_fix,
            confidence=confidence,
            auto_applicable=auto_applicable
        )


class PerformanceTracker:
    """Track performance metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.history: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    
    def record(
        self,
        metric_name: str,
        value: float,
        target: float | None = None
    ) -> PerformanceMetric:
        """Record a metric value"""
        
        previous = self.metrics.get(metric_name)
        previous_value = previous.current_value if previous else value
        
        # Determine trend
        if value > previous_value * 1.05:
            trend = "improving"
        elif value < previous_value * 0.95:
            trend = "declining"
        else:
            trend = "stable"
        
        # Update history
        history = self.metrics.get(metric_name, PerformanceMetric(
            metric_name=metric_name,
            current_value=0,
            previous_value=0,
            trend="stable"
        )).history
        history.append(value)
        
        metric = PerformanceMetric(
            metric_name=metric_name,
            current_value=value,
            previous_value=previous_value,
            trend=trend,
            target=target,
            history=history[-100:]  # Keep last 100
        )
        
        self.metrics[metric_name] = metric
        self.history[metric_name].append((datetime.now().isoformat(), value))
        
        return metric
    
    def get_metric(self, metric_name: str) -> Optional[PerformanceMetric]:
        """Get metric by name"""
        return self.metrics.get(metric_name)
    
    def get_all_metrics(self) -> Dict[str, PerformanceMetric]:
        """Get all metrics"""
        return dict(self.metrics)
    
    def get_trending(self, direction: str = "declining") -> List[str]:
        """Get metrics trending in a direction"""
        return [
            name for name, metric in self.metrics.items()
            if metric.trend == direction
        ]


class FeedbackLoop:
    """
    Main feedback loop system
    
    Features:
    - Error detection and categorization
    - Correction suggestion generation
    - Performance tracking
    - Feedback aggregation
    """
    
    def __init__(
        self,
        project_root: Path,
        feedback_dir: Path | None = None
    ):
        self.project_root = project_root
        self.feedback_dir = feedback_dir or project_root / "data" / "feedback"
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
        self.error_detector = ErrorDetector()
        self.correction_generator = CorrectionGenerator()
        self.performance_tracker = PerformanceTracker()
        
        self.feedback_entries: List[FeedbackEntry] = []
        self.feedback_counter = 0
    
    def record_feedback(
        self,
        operation: str,
        result: str,
        message: str,
        correction: str | None = None,
        metadata: Dict[str, Any] | None = None
    ) -> FeedbackEntry:
        """Record feedback entry"""
        self.feedback_counter += 1
        feedback_id = f"fb-{self.feedback_counter}-{int(datetime.now().timestamp())}"
        
        entry = FeedbackEntry(
            feedback_id=feedback_id,
            operation=operation,
            result=result,
            message=message,
            correction=correction,
            metadata=metadata or {}
        )
        
        self.feedback_entries.append(entry)
        self._persist_feedback(entry)
        
        return entry
    
    def process_error(
        self,
        error_message: str,
        operation: str,
        context: Dict[str, Any] | None = None
    ) -> Tuple[FeedbackEntry, CorrectionSuggestion]:
        """Process an error and generate feedback"""
        
        # Detect error type
        category, error_type, confidence = self.error_detector.detect(error_message)
        severity = self.error_detector.get_severity(category)
        
        # Generate correction
        correction = self.correction_generator.generate(
            category, error_type, context
        )
        
        # Record feedback
        entry = self.record_feedback(
            operation=operation,
            result="failure",
            message=error_message,
            correction=correction.suggested_fix,
            metadata={
                "category": category,
                "error_type": error_type,
                "severity": severity,
                "confidence": confidence
            }
        )
        
        return entry, correction
    
    def record_success(
        self,
        operation: str,
        message: str = "Operation completed successfully",
        metadata: Dict[str, Any] | None = None
    ) -> FeedbackEntry:
        """Record successful operation"""
        return self.record_feedback(
            operation=operation,
            result="success",
            message=message,
            metadata=metadata
        )
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        target: float | None = None
    ) -> PerformanceMetric:
        """Record performance metric"""
        return self.performance_tracker.record(metric_name, value, target)
    
    def get_corrections_for(
        self,
        error_type: str
    ) -> List[CorrectionSuggestion]:
        """Get corrections for specific error type"""
        corrections = []
        
        for entry in self.feedback_entries:
            if entry.result == "failure":
                meta = entry.metadata
                if meta.get("error_type") == error_type:
                    corrections.append(CorrectionSuggestion(
                        suggestion_id=f"corr-from-{entry.feedback_id}",
                        issue_type=error_type,
                        description=entry.message,
                        suggested_fix=entry.correction or "No fix recorded",
                        confidence=meta.get("confidence", 0.5)
                    ))
        
        return corrections
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """Get summary of all feedback"""
        total = len(self.feedback_entries)
        successes = sum(1 for e in self.feedback_entries if e.result == "success")
        failures = sum(1 for e in self.feedback_entries if e.result == "failure")
        partials = sum(1 for e in self.feedback_entries if e.result == "partial")
        
        # Error breakdown
        error_breakdown = defaultdict(int)
        for entry in self.feedback_entries:
            if entry.result == "failure":
                category = entry.metadata.get("category", "unknown")
                error_breakdown[category] += 1
        
        # Performance summary
        metrics = self.performance_tracker.get_all_metrics()
        improving = [n for n, m in metrics.items() if m.trend == "improving"]
        declining = [n for n, m in metrics.items() if m.trend == "declining"]
        
        return {
            "total_feedback": total,
            "successes": successes,
            "failures": failures,
            "partials": partials,
            "success_rate": successes / total if total > 0 else 0,
            "error_breakdown": dict(error_breakdown),
            "improving_metrics": improving,
            "declining_metrics": declining,
            "total_metrics": len(metrics)
        }
    
    def get_improvement_recommendations(self) -> List[str]:
        """Get recommendations based on feedback"""
        recommendations = []
        
        # Check declining metrics
        declining = self.performance_tracker.get_trending("declining")
        if declining:
            recommendations.append(f"Address declining metrics: {', '.join(declining)}")
        
        # Check common errors
        error_counts = defaultdict(int)
        for entry in self.feedback_entries:
            if entry.result == "failure":
                error_type = entry.metadata.get("error_type", "unknown")
                error_counts[error_type] += 1
        
        common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        for error_type, count in common_errors[:3]:
            if count > 2:
                recommendations.append(f"Fix recurring error: {error_type} ({count} occurrences)")
        
        # Check success rate
        summary = self.get_feedback_summary()
        if summary["success_rate"] < 0.8:
            recommendations.append("Success rate below 80% - review failure patterns")
        
        return recommendations
    
    def _persist_feedback(self, entry: FeedbackEntry) -> None:
        """Persist feedback to file"""
        path = self.feedback_dir / f"feedback_{datetime.now().strftime('%Y%m')}.jsonl"
        
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "feedback_id": entry.feedback_id,
                "operation": entry.operation,
                "result": entry.result,
                "message": entry.message,
                "correction": entry.correction,
                "timestamp": entry.timestamp,
                "metadata": entry.metadata
            }) + "\n")
    
    def load_feedback(self, months: int = 3) -> List[FeedbackEntry]:
        """Load recent feedback from files"""
        entries = []
        
        # Load last N months
        for i in range(months):
            from datetime import datetime, timedelta
            date = datetime.now() - timedelta(days=i * 30)
            path = self.feedback_dir / f"feedback_{date.strftime('%Y%m')}.jsonl"
            
            if path.exists():
                for line in path.read_text().splitlines():
                    if line.strip():
                        data = json.loads(line)
                        entries.append(FeedbackEntry(
                            feedback_id=data["feedback_id"],
                            operation=data["operation"],
                            result=data["result"],
                            message=data["message"],
                            correction=data.get("correction"),
                            timestamp=data["timestamp"],
                            metadata=data.get("metadata", {})
                        ))
        
        return entries
    
    def clear_old_feedback(self, days: int = 90) -> int:
        """Clear feedback older than specified days"""
        cutoff = datetime.now().timestamp() - (days * 86400)
        
        original_count = len(self.feedback_entries)
        self.feedback_entries = [
            e for e in self.feedback_entries
            if datetime.fromisoformat(e.timestamp).timestamp() > cutoff
        ]
        
        return original_count - len(self.feedback_entries)


def create_feedback_loop(
    project_root: Path | str | None = None
) -> FeedbackLoop:
    """Create feedback loop instance"""
    root = Path(project_root) if project_root else Path.cwd()
    return FeedbackLoop(root)


if __name__ == "__main__":
    # Demo
    print("=" * 80)
    print("WASEEM FEEDBACK LOOP - CORRECTION SYSTEM")
    print("=" * 80)
    
    feedback = FeedbackLoop(Path.cwd())
    
    # Process some errors
    print("\n[PROCESSING ERRORS]")
    errors = [
        ("SyntaxError: unexpected token", "code_execution"),
        ("TypeError: 'str' object is not callable", "function_call"),
        ("ImportError: No module named 'xyz'", "import_module"),
    ]
    
    for error_msg, operation in errors:
        entry, correction = feedback.process_error(error_msg, operation)
        print(f"\n  Error: {error_msg}")
        print(f"  Category: {entry.metadata.get('category')}")
        print(f"  Suggestion: {correction.suggested_fix}")
    
    # Record metrics
    print("\n[RECORDING METRICS]")
    for i in range(5):
        value = 0.7 + (i * 0.05)  # Improving
        metric = feedback.record_metric("success_rate", value, target=0.9)
        print(f"  success_rate: {value:.2f} ({metric.trend})")
    
    # Get summary
    print("\n[FEEDBACK SUMMARY]")
    summary = feedback.get_feedback_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")
    
    # Get recommendations
    print("\n[IMPROVEMENT RECOMMENDATIONS]")
    for rec in feedback.get_improvement_recommendations():
        print(f"  - {rec}")
    
    print("\n[DONE]")
