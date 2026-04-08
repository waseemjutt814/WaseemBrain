#!/usr/bin/env python3
"""
WASEEM LEARNING ENGINE - Self-Improvement System
Pattern extraction, strategy optimization, knowledge persistence
"""

from __future__ import annotations

import json
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ExecutionTrace:
    """Trace of a single execution"""
    trace_id: str
    operation: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    success: bool
    duration_ms: float
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Pattern:
    """Learned pattern"""
    pattern_id: str
    pattern_type: str
    description: str
    frequency: int
    success_rate: float
    examples: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class Strategy:
    """Learned strategy"""
    strategy_id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    success_count: int
    failure_count: int
    success_rate: float
    applicable_conditions: Dict[str, Any] = field(default_factory=dict)
    learned_from: List[str] = field(default_factory=list)


@dataclass
class LearningInsight:
    """Insight from learning analysis"""
    insight_id: str
    category: str
    title: str
    description: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    actionable: bool = True
    priority: str = "medium"


class PatternExtractor:
    """Extract patterns from execution history"""
    
    def __init__(self):
        self.patterns: Dict[str, Pattern] = {}
    
    def extract_from_traces(
        self,
        traces: List[ExecutionTrace]
    ) -> List[Pattern]:
        """Extract patterns from execution traces"""
        patterns = []
        
        # Group by operation type
        by_operation = defaultdict(list)
        for trace in traces:
            by_operation[trace.operation].append(trace)
        
        # Extract patterns per operation
        for operation, op_traces in by_operation.items():
            # Success pattern
            successful = [t for t in op_traces if t.success]
            failed = [t for t in op_traces if not t.success]
            
            if successful:
                success_rate = len(successful) / len(op_traces)
                
                # Find common conditions in successful executions
                common_conditions = self._find_common_conditions(successful)
                
                pattern = Pattern(
                    pattern_id=f"pattern-{operation}-{hashlib.md5(operation.encode()).hexdigest()[:8]}",
                    pattern_type="execution_success",
                    description=f"Successful execution pattern for {operation}",
                    frequency=len(successful),
                    success_rate=success_rate,
                    examples=[t.trace_id for t in successful[:3]],
                    conditions=common_conditions,
                    recommendations=self._generate_recommendations(common_conditions)
                )
                patterns.append(pattern)
                self.patterns[pattern.pattern_id] = pattern
            
            # Failure pattern
            if failed:
                failure_conditions = self._find_common_conditions(failed)
                
                pattern = Pattern(
                    pattern_id=f"pattern-{operation}-fail-{hashlib.md5(operation.encode()).hexdigest()[:8]}",
                    pattern_type="execution_failure",
                    description=f"Failure pattern for {operation}",
                    frequency=len(failed),
                    success_rate=0.0,
                    examples=[t.trace_id for t in failed[:3]],
                    conditions=failure_conditions,
                    recommendations=self._generate_failure_recommendations(failure_conditions)
                )
                patterns.append(pattern)
                self.patterns[pattern.pattern_id] = pattern
        
        return patterns
    
    def _find_common_conditions(
        self,
        traces: List[ExecutionTrace]
    ) -> Dict[str, Any]:
        """Find common conditions across traces"""
        conditions = {}
        
        # Check input patterns
        input_keys = defaultdict(int)
        for trace in traces:
            for key in trace.inputs.keys():
                input_keys[key] += 1
        
        # Keys present in >50% of traces
        threshold = len(traces) * 0.5
        common_keys = [k for k, v in input_keys.items() if v >= threshold]
        
        if common_keys:
            conditions["common_inputs"] = common_keys
        
        # Duration patterns
        durations = [t.duration_ms for t in traces]
        avg_duration = sum(durations) / len(durations)
        conditions["avg_duration_ms"] = round(avg_duration, 2)
        
        return conditions
    
    def _generate_recommendations(
        self,
        conditions: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations from conditions"""
        recommendations = []
        
        if "common_inputs" in conditions:
            recommendations.append(f"Ensure inputs include: {', '.join(conditions['common_inputs'])}")
        
        if "avg_duration_ms" in conditions:
            recommendations.append(f"Expected duration: ~{conditions['avg_duration_ms']}ms")
        
        return recommendations
    
    def _generate_failure_recommendations(
        self,
        conditions: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations to avoid failures"""
        recommendations = []
        
        recommendations.append("Review conditions before execution")
        recommendations.append("Add validation for common failure points")
        
        return recommendations


class StrategyOptimizer:
    """Optimize strategies based on learning"""
    
    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}
    
    def learn_strategy(
        self,
        name: str,
        traces: List[ExecutionTrace]
    ) -> Strategy:
        """Learn a strategy from execution traces"""
        
        # Group by success
        successful = [t for t in traces if t.success]
        failed = [t for t in traces if not t.success]
        
        # Extract steps from successful traces
        steps = self._extract_steps(successful)
        
        # Calculate success rate
        success_rate = len(successful) / len(traces) if traces else 0
        
        # Find applicable conditions
        conditions = self._find_applicable_conditions(successful)
        
        strategy = Strategy(
            strategy_id=f"strategy-{hashlib.md5(name.encode()).hexdigest()[:8]}",
            name=name,
            description=f"Learned strategy for {name}",
            steps=steps,
            success_count=len(successful),
            failure_count=len(failed),
            success_rate=success_rate,
            applicable_conditions=conditions,
            learned_from=[t.trace_id for t in successful[:5]]
        )
        
        self.strategies[strategy.strategy_id] = strategy
        return strategy
    
    def _extract_steps(
        self,
        traces: List[ExecutionTrace]
    ) -> List[Dict[str, Any]]:
        """Extract common steps from traces"""
        steps = []
        
        # Find common operation sequence
        operation_sequences = []
        for trace in traces:
            if "operations" in trace.metadata:
                operation_sequences.append(trace.metadata["operations"])
        
        if operation_sequences:
            # Find most common sequence
            sequence_counts = defaultdict(int)
            for seq in operation_sequences:
                seq_key = json.dumps(seq, sort_keys=True)
                sequence_counts[seq_key] += 1
            
            most_common = max(sequence_counts.items(), key=lambda x: x[1])
            steps = json.loads(most_common[0])
        
        return steps
    
    def _find_applicable_conditions(
        self,
        traces: List[ExecutionTrace]
    ) -> Dict[str, Any]:
        """Find conditions where strategy applies"""
        conditions = {}
        
        # Input types
        input_types = defaultdict(int)
        for trace in traces:
            for key, value in trace.inputs.items():
                input_types[f"{key}:{type(value).__name__}"] += 1
        
        # Most common input types
        if input_types:
            sorted_types = sorted(input_types.items(), key=lambda x: x[1], reverse=True)
            conditions["input_types"] = [t[0] for t in sorted_types[:5]]
        
        return conditions
    
    def optimize_strategy(
        self,
        strategy_id: str,
        new_traces: List[ExecutionTrace]
    ) -> Strategy:
        """Update strategy with new data"""
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        strategy = self.strategies[strategy_id]
        
        # Update counts
        successful = [t for t in new_traces if t.success]
        failed = [t for t in new_traces if not t.success]
        
        strategy.success_count += len(successful)
        strategy.failure_count += len(failed)
        
        total = strategy.success_count + strategy.failure_count
        strategy.success_rate = strategy.success_count / total if total > 0 else 0
        
        # Update learned_from
        strategy.learned_from.extend([t.trace_id for t in successful[:3]])
        
        return strategy
    
    def get_best_strategy(
        self,
        operation: str
    ) -> Optional[Strategy]:
        """Get best strategy for an operation"""
        matching = [
            s for s in self.strategies.values()
            if operation.lower() in s.name.lower()
        ]
        
        if not matching:
            return None
        
        # Return strategy with highest success rate
        return max(matching, key=lambda s: s.success_rate)


class InsightGenerator:
    """Generate insights from learning data"""
    
    def __init__(self):
        self.insights: Dict[str, LearningInsight] = {}
    
    def generate_insights(
        self,
        patterns: List[Pattern],
        strategies: List[Strategy]
    ) -> List[LearningInsight]:
        """Generate insights from patterns and strategies"""
        insights = []
        
        # Pattern-based insights
        for pattern in patterns:
            if pattern.pattern_type == "execution_failure":
                insight = LearningInsight(
                    insight_id=f"insight-{pattern.pattern_id}",
                    category="risk",
                    title=f"Failure pattern detected: {pattern.description}",
                    description=f"Found {pattern.frequency} failures with common conditions",
                    confidence=0.8,
                    evidence=pattern.examples,
                    actionable=True,
                    priority="high"
                )
                insights.append(insight)
                self.insights[insight.insight_id] = insight
            
            elif pattern.success_rate > 0.9:
                insight = LearningInsight(
                    insight_id=f"insight-{pattern.pattern_id}",
                    category="optimization",
                    title=f"High success pattern: {pattern.description}",
                    description=f"Success rate: {pattern.success_rate:.1%}",
                    confidence=0.9,
                    evidence=pattern.examples,
                    actionable=True,
                    priority="medium"
                )
                insights.append(insight)
                self.insights[insight.insight_id] = insight
        
        # Strategy-based insights
        for strategy in strategies:
            if strategy.success_rate < 0.5:
                insight = LearningInsight(
                    insight_id=f"insight-strategy-{strategy.strategy_id}",
                    category="improvement",
                    title=f"Low success strategy: {strategy.name}",
                    description=f"Strategy success rate: {strategy.success_rate:.1%}",
                    confidence=0.85,
                    evidence=strategy.learned_from,
                    actionable=True,
                    priority="high"
                )
                insights.append(insight)
                self.insights[insight.insight_id] = insight
        
        return insights


class KnowledgePersistence:
    """Persist learned knowledge"""
    
    def __init__(self, knowledge_dir: Path | None = None):
        self.knowledge_dir = knowledge_dir or Path("data/learned_knowledge")
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
    
    def save_patterns(self, patterns: List[Pattern]) -> None:
        """Save patterns to file"""
        path = self.knowledge_dir / "patterns.json"
        data = {
            "timestamp": datetime.now().isoformat(),
            "patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "pattern_type": p.pattern_type,
                    "description": p.description,
                    "frequency": p.frequency,
                    "success_rate": p.success_rate,
                    "conditions": p.conditions,
                    "recommendations": p.recommendations
                }
                for p in patterns
            ]
        }
        path.write_text(json.dumps(data, indent=2))
    
    def save_strategies(self, strategies: List[Strategy]) -> None:
        """Save strategies to file"""
        path = self.knowledge_dir / "strategies.json"
        data = {
            "timestamp": datetime.now().isoformat(),
            "strategies": [
                {
                    "strategy_id": s.strategy_id,
                    "name": s.name,
                    "description": s.description,
                    "steps": s.steps,
                    "success_rate": s.success_rate,
                    "applicable_conditions": s.applicable_conditions
                }
                for s in strategies
            ]
        }
        path.write_text(json.dumps(data, indent=2))
    
    def save_insights(self, insights: List[LearningInsight]) -> None:
        """Save insights to file"""
        path = self.knowledge_dir / "insights.json"
        data = {
            "timestamp": datetime.now().isoformat(),
            "insights": [
                {
                    "insight_id": i.insight_id,
                    "category": i.category,
                    "title": i.title,
                    "description": i.description,
                    "confidence": i.confidence,
                    "actionable": i.actionable,
                    "priority": i.priority
                }
                for i in insights
            ]
        }
        path.write_text(json.dumps(data, indent=2))
    
    def load_patterns(self) -> List[Pattern]:
        """Load patterns from file"""
        path = self.knowledge_dir / "patterns.json"
        if not path.exists():
            return []
        
        data = json.loads(path.read_text())
        return [
            Pattern(
                pattern_id=p["pattern_id"],
                pattern_type=p["pattern_type"],
                description=p["description"],
                frequency=p["frequency"],
                success_rate=p["success_rate"],
                conditions=p.get("conditions", {}),
                recommendations=p.get("recommendations", [])
            )
            for p in data.get("patterns", [])
        ]
    
    def load_strategies(self) -> List[Strategy]:
        """Load strategies from file"""
        path = self.knowledge_dir / "strategies.json"
        if not path.exists():
            return []
        
        data = json.loads(path.read_text())
        return [
            Strategy(
                strategy_id=s["strategy_id"],
                name=s["name"],
                description=s["description"],
                steps=s["steps"],
                success_count=0,
                failure_count=0,
                success_rate=s["success_rate"],
                applicable_conditions=s.get("applicable_conditions", {})
            )
            for s in data.get("strategies", [])
        ]


class LearningEngine:
    """
    Main learning engine for self-improvement
    
    Features:
    - Pattern extraction from execution history
    - Strategy optimization
    - Insight generation
    - Knowledge persistence
    """
    
    def __init__(
        self,
        project_root: Path,
        knowledge_dir: Path | None = None
    ):
        self.project_root = project_root
        self.pattern_extractor = PatternExtractor()
        self.strategy_optimizer = StrategyOptimizer()
        self.insight_generator = InsightGenerator()
        self.persistence = KnowledgePersistence(knowledge_dir)
        
        self.execution_traces: List[ExecutionTrace] = []
        self.trace_counter = 0
    
    def record_execution(
        self,
        operation: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        success: bool,
        duration_ms: float,
        error: Optional[str] = None,
        metadata: Dict[str, Any] | None = None
    ) -> ExecutionTrace:
        """Record an execution for learning"""
        self.trace_counter += 1
        trace_id = f"trace-{self.trace_counter}-{int(datetime.now().timestamp())}"
        
        trace = ExecutionTrace(
            trace_id=trace_id,
            operation=operation,
            inputs=inputs,
            outputs=outputs,
            success=success,
            duration_ms=duration_ms,
            error=error,
            metadata=metadata or {}
        )
        
        self.execution_traces.append(trace)
        return trace
    
    def learn(self) -> Dict[str, Any]:
        """Run learning cycle"""
        if not self.execution_traces:
            return {"status": "no_data", "message": "No execution traces to learn from"}
        
        # Extract patterns
        patterns = self.pattern_extractor.extract_from_traces(self.execution_traces)
        
        # Learn strategies
        by_operation = defaultdict(list)
        for trace in self.execution_traces:
            by_operation[trace.operation].append(trace)
        
        strategies = []
        for operation, traces in by_operation.items():
            if len(traces) >= 3:  # Need minimum traces
                strategy = self.strategy_optimizer.learn_strategy(operation, traces)
                strategies.append(strategy)
        
        # Generate insights
        insights = self.insight_generator.generate_insights(patterns, strategies)
        
        # Persist knowledge
        self.persistence.save_patterns(patterns)
        self.persistence.save_strategies(strategies)
        self.persistence.save_insights(insights)
        
        return {
            "status": "success",
            "patterns_learned": len(patterns),
            "strategies_learned": len(strategies),
            "insights_generated": len(insights),
            "traces_analyzed": len(self.execution_traces)
        }
    
    def get_best_practices(self, operation: str) -> List[str]:
        """Get best practices for an operation"""
        patterns = self.pattern_extractor.patterns
        practices = []
        
        for pattern in patterns.values():
            if operation.lower() in pattern.description.lower():
                if pattern.success_rate > 0.8:
                    practices.extend(pattern.recommendations)
        
        return list(set(practices))
    
    def get_strategy_for(self, operation: str) -> Optional[Strategy]:
        """Get best strategy for operation"""
        return self.strategy_optimizer.get_best_strategy(operation)
    
    def get_insights(self, category: str | None = None) -> List[LearningInsight]:
        """Get insights, optionally filtered by category"""
        insights = list(self.insight_generator.insights.values())
        
        if category:
            insights = [i for i in insights if i.category == category]
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        insights.sort(key=lambda i: priority_order.get(i.priority, 3))
        
        return insights
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of learning state"""
        traces = self.execution_traces
        successful = [t for t in traces if t.success]
        
        return {
            "total_traces": len(traces),
            "successful_traces": len(successful),
            "success_rate": len(successful) / len(traces) if traces else 0,
            "unique_operations": len(set(t.operation for t in traces)),
            "patterns_learned": len(self.pattern_extractor.patterns),
            "strategies_learned": len(self.strategy_optimizer.strategies),
            "insights_generated": len(self.insight_generator.insights)
        }
    
    def load_knowledge(self) -> None:
        """Load previously learned knowledge"""
        patterns = self.persistence.load_patterns()
        for pattern in patterns:
            self.pattern_extractor.patterns[pattern.pattern_id] = pattern
        
        strategies = self.persistence.load_strategies()
        for strategy in strategies:
            self.strategy_optimizer.strategies[strategy.strategy_id] = strategy
    
    def clear_traces(self) -> None:
        """Clear execution traces (keep learned knowledge)"""
        self.execution_traces.clear()


def create_learning_engine(
    project_root: Path | str | None = None,
    knowledge_dir: Path | str | None = None
) -> LearningEngine:
    """Create learning engine instance"""
    root = Path(project_root) if project_root else Path.cwd()
    kdir = Path(knowledge_dir) if knowledge_dir else None
    return LearningEngine(root, kdir)


if __name__ == "__main__":
    # Demo
    print("=" * 80)
    print("WASEEM LEARNING ENGINE - SELF-IMPROVEMENT")
    print("=" * 80)
    
    engine = LearningEngine(Path.cwd())
    
    # Record some executions
    print("\n[RECORDING EXECUTIONS]")
    for i in range(10):
        success = i < 7  # 70% success rate
        engine.record_execution(
            operation="code_analysis",
            inputs={"file": f"test_{i}.py"},
            outputs={"result": "analyzed"} if success else {},
            success=success,
            duration_ms=100 + i * 10,
            error=None if success else "Syntax error"
        )
    
    # Run learning
    print("\n[RUNNING LEARNING]")
    result = engine.learn()
    print(f"Status: {result['status']}")
    print(f"Patterns: {result['patterns_learned']}")
    print(f"Strategies: {result['strategies_learned']}")
    print(f"Insights: {result['insights_generated']}")
    
    # Get summary
    print("\n[LEARNING SUMMARY]")
    summary = engine.get_learning_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")
    
    # Get insights
    print("\n[INSIGHTS]")
    for insight in engine.get_insights()[:3]:
        print(f"  [{insight.priority}] {insight.title}")
    
    print("\n[DONE]")
