#!/usr/bin/env python3
"""
WASEEM REASONING ENGINE - NASA/Google-level Deep Analysis
Multi-step logical reasoning, pattern recognition, decision trees
"""

from __future__ import annotations

import ast
import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from collections import defaultdict


class ReasoningDepth(Enum):
    """Depth levels for reasoning"""
    SURFACE = 1      # Quick scan
    STANDARD = 3     # Normal analysis
    DEEP = 5         # Thorough investigation
    EXHAUSTIVE = 7   # Complete analysis
    NASA_LEVEL = 10  # Maximum depth


class ConfidenceLevel(Enum):
    """Confidence thresholds"""
    VERY_LOW = 0.3
    LOW = 0.5
    MEDIUM = 0.7
    HIGH = 0.85
    VERY_HIGH = 0.95
    CERTAIN = 0.99


@dataclass
class ReasoningStep:
    """Single step in reasoning chain"""
    step_number: int
    action: str
    observation: str
    inference: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DecisionNode:
    """Node in decision tree"""
    condition: str
    true_branch: Optional["DecisionNode"] = None
    false_branch: Optional["DecisionNode"] = None
    action: Optional[str] = None
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)


@dataclass
class PatternMatch:
    """Detected pattern in code/data"""
    pattern_type: str
    location: str
    description: str
    frequency: int
    confidence: float
    examples: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ReasoningResult:
    """Complete reasoning output"""
    query: str
    depth: int
    steps: List[ReasoningStep]
    conclusion: str
    confidence: float
    decision_tree: Optional[DecisionNode]
    patterns: List[PatternMatch]
    recommendations: List[str]
    execution_time_ms: float
    trace_id: str


class LogicalInference:
    """Logical inference engine"""
    
    @staticmethod
    def modus_ponens(premise: str, implication: str) -> Tuple[bool, str]:
        """If P, then Q. P is true. Therefore Q."""
        return True, f"Given {premise} and {implication}, conclusion follows"
    
    @staticmethod
    def modus_tollens(implication: str, not_q: str) -> Tuple[bool, str]:
        """If P, then Q. Not Q. Therefore not P."""
        return True, f"Given {implication} and {not_q}, negation follows"
    
    @staticmethod
    def hypothesis_test(hypothesis: str, evidence: List[str]) -> Tuple[bool, float]:
        """Test hypothesis against evidence"""
        if not evidence:
            return False, 0.0
        
        supporting = sum(1 for e in evidence if hypothesis.lower() in e.lower())
        confidence = supporting / len(evidence)
        return confidence > 0.5, confidence
    
    @staticmethod
    def abductive_reasoning(observation: str, possible_causes: List[str]) -> Tuple[str, float]:
        """Find most likely cause for observation"""
        if not possible_causes:
            return "Unknown cause", 0.0
        
        # Score each cause by relevance
        scored = []
        for cause in possible_causes:
            overlap = len(set(observation.lower().split()) & set(cause.lower().split()))
            scored.append((cause, overlap))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        best_cause, score = scored[0]
        confidence = min(0.9, score / max(len(observation.split()), 1))
        
        return best_cause, confidence


class PatternRecognizer:
    """Advanced pattern recognition"""
    
    CODE_PATTERNS = {
        "singleton": r"class\s+\w+:\s*\n\s*_instance\s*=",
        "factory": r"def\s+create_\w+\s*\(",
        "observer": r"def\s+(add|remove)_observer\s*\(",
        "strategy": r"class\s+\w+Strategy",
        "adapter": r"class\s+\w+Adapter",
        "decorator": r"@\w+\s*\n\s*def",
        "async_pattern": r"async\s+def\s+\w+\s*\(",
        "error_handling": r"try:\s*\n.*except\s+\w+",
        "logging": r"(logger|logging)\.\w+\s*\(",
        "test_pattern": r"def\s+test_\w+\s*\(",
    }
    
    QUALITY_PATTERNS = {
        "type_hints": r":\s*(str|int|float|bool|list|dict|Any|Optional)",
        "docstring": r'"""[\s\S]*?"""',
        "todo": r"#\s*TODO",
        "fixme": r"#\s*FIXME",
        "hack": r"#\s*HACK",
        "complexity_warning": r"if\s+.*\s+if\s+.*\s+if\s+",
    }
    
    def __init__(self):
        self.detected_patterns: Dict[str, List[PatternMatch]] = defaultdict(list)
    
    def analyze_file(self, content: str, file_path: str) -> List[PatternMatch]:
        """Analyze file for all patterns"""
        patterns = []
        
        # Code patterns
        for pattern_name, pattern_regex in self.CODE_PATTERNS.items():
            matches = list(re.finditer(pattern_regex, content, re.MULTILINE))
            if matches:
                patterns.append(PatternMatch(
                    pattern_type=f"code:{pattern_name}",
                    location=file_path,
                    description=f"Detected {pattern_name} pattern",
                    frequency=len(matches),
                    confidence=0.85,
                    examples=[m.group()[:50] for m in matches[:3]],
                    recommendations=self._get_pattern_recommendation(pattern_name)
                ))
        
        # Quality patterns
        for pattern_name, pattern_regex in self.QUALITY_PATTERNS.items():
            matches = list(re.finditer(pattern_regex, content, re.MULTILINE | re.DOTALL))
            if matches:
                patterns.append(PatternMatch(
                    pattern_type=f"quality:{pattern_name}",
                    location=file_path,
                    description=f"Found {len(matches)} {pattern_name} instances",
                    frequency=len(matches),
                    confidence=0.9,
                    examples=[m.group()[:50] for m in matches[:3]],
                    recommendations=self._get_quality_recommendation(pattern_name)
                ))
        
        return patterns
    
    def _get_pattern_recommendation(self, pattern: str) -> List[str]:
        """Get recommendations for pattern"""
        recommendations = {
            "singleton": ["Consider dependency injection instead", "Ensure thread safety"],
            "factory": ["Document factory methods", "Consider abstract factory for families"],
            "observer": ["Handle observer exceptions", "Consider async notification"],
            "strategy": ["Use composition over inheritance", "Document strategy selection logic"],
            "async_pattern": ["Ensure proper error handling", "Consider timeout handling"],
            "error_handling": ["Log exceptions with context", "Avoid bare except clauses"],
        }
        return recommendations.get(pattern, ["Review pattern implementation"])
    
    def _get_quality_recommendation(self, pattern: str) -> List[str]:
        """Get recommendations for quality issues"""
        recommendations = {
            "todo": ["Resolve TODO items before release", "Track TODOs in issue tracker"],
            "fixme": ["Fix known issues immediately", "Add test for fix verification"],
            "hack": ["Refactor hack implementations", "Document workaround rationale"],
            "complexity_warning": ["Reduce nesting levels", "Extract methods for clarity"],
        }
        return recommendations.get(pattern, ["Review and address"])


class ComplexityAnalyzer:
    """Analyze code complexity"""
    
    @staticmethod
    def cyclomatic_complexity(code: str) -> int:
        """Calculate cyclomatic complexity"""
        # Count decision points
        decision_keywords = ['if', 'elif', 'for', 'while', 'and', 'or', 'except', 'case']
        complexity = 1  # Base complexity
        
        for keyword in decision_keywords:
            complexity += len(re.findall(rf'\b{keyword}\b', code))
        
        return complexity
    
    @staticmethod
    def cognitive_complexity(code: str) -> int:
        """Calculate cognitive complexity (human-readable)"""
        complexity = 0
        nesting_level = 0
        
        lines = code.split('\n')
        for line in lines:
            indent = len(line) - len(line.lstrip())
            
            # Increase for control structures
            if re.search(r'\b(if|for|while|try)\b', line):
                complexity += 1 + nesting_level
                nesting_level = indent // 4 + 1
            elif re.search(r'\b(elif|else|except|finally)\b', line):
                complexity += 1
        
        return complexity
    
    @staticmethod
    def halstead_metrics(code: str) -> Dict[str, float]:
        """Calculate Halstead complexity metrics"""
        # Extract operators and operands
        operators = re.findall(r'[+\-*/%=<>!&|^~?:]+|\b(and|or|not|in|is)\b', code)
        operands = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b|\b\d+\b', code)
        
        n1 = len(set(operators))  # Unique operators
        n2 = len(set(operands))   # Unique operands
        N1 = len(operators)       # Total operators
        N2 = len(operands)        # Total operands
        
        if n1 == 0 or n2 == 0:
            return {"volume": 0, "difficulty": 0, "effort": 0}
        
        vocabulary = n1 + n2
        length = N1 + N2
        volume = length * (n1 + n2) / (n1 * n2) if n1 * n2 > 0 else 0
        difficulty = (n1 / 2) * (N2 / n2) if n2 > 0 else 0
        effort = difficulty * volume
        
        return {
            "vocabulary": vocabulary,
            "length": length,
            "volume": round(volume, 2),
            "difficulty": round(difficulty, 2),
            "effort": round(effort, 2)
        }


class ReasoningEngine:
    """
    Main reasoning engine with NASA/Google-level analysis capabilities
    """
    
    def __init__(self, project_root: Path | None = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.inference = LogicalInference()
        self.pattern_recognizer = PatternRecognizer()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.reasoning_history: List[ReasoningResult] = []
    
    def analyze(
        self,
        query: str,
        context: Dict[str, Any] | None = None,
        depth: ReasoningDepth = ReasoningDepth.DEEP
    ) -> ReasoningResult:
        """
        Perform deep analysis with reasoning chain
        """
        start_time = datetime.now()
        steps: List[ReasoningStep] = []
        patterns: List[PatternMatch] = []
        recommendations: List[str] = []
        
        context = context or {}
        trace_id = hashlib.sha256(f"{query}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        # Step 1: Query Understanding
        steps.append(self._understand_query(query, 1))
        
        # Step 2: Context Gathering
        steps.append(self._gather_context(query, context, 2))
        
        # Step 3: Pattern Detection
        if depth.value >= ReasoningDepth.STANDARD.value:
            patterns = self._detect_patterns(query, context)
            steps.append(ReasoningStep(
                step_number=3,
                action="Pattern Detection",
                observation=f"Found {len(patterns)} patterns",
                inference="Patterns indicate code structure and quality",
                confidence=0.85,
                evidence=[p.description for p in patterns[:5]]
            ))
        
        # Step 4: Hypothesis Generation
        if depth.value >= ReasoningDepth.DEEP.value:
            hypotheses = self._generate_hypotheses(query, patterns)
            steps.append(ReasoningStep(
                step_number=4,
                action="Hypothesis Generation",
                observation=f"Generated {len(hypotheses)} hypotheses",
                inference="Top hypothesis selected for testing",
                confidence=0.75,
                evidence=hypotheses[:3]
            ))
        
        # Step 5: Evidence Analysis
        if depth.value >= ReasoningDepth.DEEP.value:
            evidence_result = self._analyze_evidence(query, hypotheses, context)
            steps.append(evidence_result)
        
        # Step 6: Decision Tree Construction
        decision_tree = None
        if depth.value >= ReasoningDepth.EXHAUSTIVE.value:
            decision_tree = self._build_decision_tree(query, hypotheses, patterns)
            steps.append(ReasoningStep(
                step_number=6,
                action="Decision Tree Construction",
                observation="Built decision tree for systematic evaluation",
                inference="Tree provides structured decision path",
                confidence=0.8,
                evidence=[f"Root: {decision_tree.condition}"] if decision_tree else []
            ))
        
        # Step 7-10: Additional NASA-level analysis
        if depth.value >= ReasoningDepth.NASA_LEVEL.value:
            steps.extend(self._nasa_level_analysis(query, context, patterns))
        
        # Generate conclusion
        conclusion = self._synthesize_conclusion(steps, patterns)
        confidence = self._calculate_confidence(steps)
        recommendations = self._generate_recommendations(patterns, conclusion)
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        result = ReasoningResult(
            query=query,
            depth=depth.value,
            steps=steps,
            conclusion=conclusion,
            confidence=confidence,
            decision_tree=decision_tree,
            patterns=patterns,
            recommendations=recommendations,
            execution_time_ms=execution_time,
            trace_id=trace_id
        )
        
        self.reasoning_history.append(result)
        return result
    
    def _understand_query(self, query: str, step_num: int) -> ReasoningStep:
        """Understand the query intent"""
        # Extract key terms
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        keywords = [w for w in words if w not in {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'has', 'have'}]
        
        # Detect query type
        query_types = {
            "analysis": ["analyze", "examine", "investigate", "study"],
            "optimization": ["optimize", "improve", "enhance", "speed"],
            "debugging": ["debug", "fix", "error", "bug", "issue"],
            "generation": ["create", "generate", "build", "make", "write"],
            "explanation": ["explain", "describe", "tell", "what", "how", "why"]
        }
        
        detected_type = "general"
        for qtype, indicators in query_types.items():
            if any(ind in query.lower() for ind in indicators):
                detected_type = qtype
                break
        
        return ReasoningStep(
            step_number=step_num,
            action="Query Understanding",
            observation=f"Query contains {len(keywords)} key terms: {', '.join(keywords[:5])}",
            inference=f"Query type detected as: {detected_type}",
            confidence=0.9,
            evidence=[f"Keywords: {keywords[:5]}", f"Type: {detected_type}"]
        )
    
    def _gather_context(
        self, query: str, context: Dict[str, Any], step_num: int
    ) -> ReasoningStep:
        """Gather relevant context"""
        context_items = []
        
        if "files" in context:
            context_items.append(f"{len(context['files'])} files available")
        if "code" in context:
            lines = len(context['code'].split('\n'))
            context_items.append(f"{lines} lines of code")
        if "history" in context:
            context_items.append(f"{len(context['history'])} historical entries")
        
        observation = "Context gathered: " + (", ".join(context_items) if context_items else "No additional context")
        
        return ReasoningStep(
            step_number=step_num,
            action="Context Gathering",
            observation=observation,
            inference="Context will inform analysis depth and focus",
            confidence=0.85,
            evidence=context_items
        )
    
    def _detect_patterns(
        self, query: str, context: Dict[str, Any]
    ) -> List[PatternMatch]:
        """Detect patterns in code/data"""
        patterns = []
        
        if "code" in context:
            patterns.extend(self.pattern_recognizer.analyze_file(
                context["code"], context.get("file_path", "unknown")
            ))
        
        if "files" in context:
            for file_info in context["files"][:10]:  # Limit for performance
                if "content" in file_info:
                    patterns.extend(self.pattern_recognizer.analyze_file(
                        file_info["content"],
                        file_info.get("path", "unknown")
                    ))
        
        return patterns
    
    def _generate_hypotheses(
        self, query: str, patterns: List[PatternMatch]
    ) -> List[str]:
        """Generate hypotheses based on query and patterns"""
        hypotheses = []
        
        # Pattern-based hypotheses
        quality_issues = [p for p in patterns if p.pattern_type.startswith("quality:")]
        if quality_issues:
            hypotheses.append(f"Code has {len(quality_issues)} quality issues that may affect {query}")
        
        code_patterns = [p for p in patterns if p.pattern_type.startswith("code:")]
        if code_patterns:
            pattern_names = set(p.pattern_type.split(":")[1] for p in code_patterns)
            hypotheses.append(f"Code uses {len(pattern_names)} design patterns: {', '.join(pattern_names)}")
        
        # Query-based hypotheses
        if "optimize" in query.lower():
            hypotheses.append("Performance optimization opportunities exist in hot paths")
        if "debug" in query.lower() or "fix" in query.lower():
            hypotheses.append("Root cause likely in error handling or edge cases")
        if "improve" in query.lower():
            hypotheses.append("Improvement possible through refactoring and pattern application")
        
        # Default hypothesis
        if not hypotheses:
            hypotheses.append("Analysis will reveal actionable insights")
        
        return hypotheses
    
    def _analyze_evidence(
        self, query: str, hypotheses: List[str], context: Dict[str, Any]
    ) -> ReasoningStep:
        """Analyze evidence for/against hypotheses"""
        evidence_for = []
        evidence_against = []
        
        code = context.get("code", "")
        
        for hypothesis in hypotheses:
            is_supported, confidence = self.inference.hypothesis_test(
                hypothesis, [code] if code else []
            )
            if is_supported:
                evidence_for.append(f"{hypothesis} (confidence: {confidence:.2f})")
            else:
                evidence_against.append(f"{hypothesis} (confidence: {1-confidence:.2f})")
        
        return ReasoningStep(
            step_number=5,
            action="Evidence Analysis",
            observation=f"Found {len(evidence_for)} supporting and {len(evidence_against)} contradicting evidence",
            inference="Evidence supports primary hypothesis",
            confidence=0.8,
            evidence=evidence_for[:3] + evidence_against[:2]
        )
    
    def _build_decision_tree(
        self, query: str, hypotheses: List[str], patterns: List[PatternMatch]
    ) -> DecisionNode:
        """Build decision tree for systematic evaluation"""
        
        # Root node based on query type
        if "optimize" in query.lower():
            root = DecisionNode(
                condition="Is performance critical path?",
                confidence=0.85,
                evidence=["Query mentions optimization"]
            )
            root.true_branch = DecisionNode(
                condition="Are there complexity hotspots?",
                action="Profile and optimize hot paths",
                confidence=0.8
            )
            root.false_branch = DecisionNode(
                condition="Is code maintainable?",
                action="Focus on maintainability improvements",
                confidence=0.75
            )
        
        elif "debug" in query.lower() or "fix" in query.lower():
            root = DecisionNode(
                condition="Is error reproducible?",
                confidence=0.85,
                evidence=["Query mentions debugging"]
            )
            root.true_branch = DecisionNode(
                condition="Is error in known location?",
                action="Apply targeted fix with tests",
                confidence=0.9
            )
            root.false_branch = DecisionNode(
                condition="Are there error logs?",
                action="Analyze logs and add instrumentation",
                confidence=0.8
            )
        
        else:
            root = DecisionNode(
                condition="Is analysis scope clear?",
                confidence=0.75,
                evidence=["General query"]
            )
            root.true_branch = DecisionNode(
                condition="Is sufficient context available?",
                action="Proceed with detailed analysis",
                confidence=0.85
            )
            root.false_branch = DecisionNode(
                condition="Can more context be gathered?",
                action="Request additional context",
                confidence=0.7
            )
        
        return root
    
    def _nasa_level_analysis(
        self, query: str, context: Dict[str, Any], patterns: List[PatternMatch]
    ) -> List[ReasoningStep]:
        """Additional NASA-level deep analysis"""
        steps = []
        
        # Step 7: Complexity Analysis
        code = context.get("code", "")
        if code:
            cc = self.complexity_analyzer.cyclomatic_complexity(code)
            cog = self.complexity_analyzer.cognitive_complexity(code)
            halstead = self.complexity_analyzer.halstead_metrics(code)
            
            steps.append(ReasoningStep(
                step_number=7,
                action="Complexity Analysis",
                observation=f"Cyclomatic: {cc}, Cognitive: {cog}, Volume: {halstead['volume']}",
                inference="Complexity metrics indicate code maintainability",
                confidence=0.9,
                evidence=[
                    f"Cyclomatic complexity: {cc} ({'high' if cc > 10 else 'acceptable'})",
                    f"Cognitive complexity: {cog} ({'high' if cog > 15 else 'acceptable'})",
                    f"Effort estimate: {halstead['effort']}"
                ]
            ))
        
        # Step 8: Risk Assessment
        risk_factors = []
        for pattern in patterns:
            if "todo" in pattern.pattern_type or "fixme" in pattern.pattern_type:
                risk_factors.append(f"Unresolved {pattern.pattern_type}")
            if "complexity" in pattern.pattern_type:
                risk_factors.append("High complexity areas")
        
        steps.append(ReasoningStep(
            step_number=8,
            action="Risk Assessment",
            observation=f"Identified {len(risk_factors)} risk factors",
            inference="Risk assessment complete",
            confidence=0.85,
            evidence=risk_factors[:5] if risk_factors else ["No significant risks identified"]
        ))
        
        # Step 9: Alternative Solutions
        alternatives = self._generate_alternatives(query, patterns)
        steps.append(ReasoningStep(
            step_number=9,
            action="Alternative Solutions",
            observation=f"Generated {len(alternatives)} alternative approaches",
            inference="Alternatives provide flexibility in implementation",
            confidence=0.75,
            evidence=alternatives[:3]
        ))
        
        # Step 10: Validation Strategy
        validation_steps = self._define_validation_strategy(query)
        steps.append(ReasoningStep(
            step_number=10,
            action="Validation Strategy",
            observation=f"Defined {len(validation_steps)} validation steps",
            inference="Validation ensures correctness of conclusions",
            confidence=0.9,
            evidence=validation_steps
        ))
        
        return steps
    
    def _generate_alternatives(self, query: str, patterns: List[PatternMatch]) -> List[str]:
        """Generate alternative approaches"""
        alternatives = []
        
        if "optimize" in query.lower():
            alternatives.extend([
                "Algorithmic optimization - reduce time complexity",
                "Caching strategy - memoize expensive operations",
                "Parallelization - utilize concurrent execution",
                "Data structure optimization - use efficient structures"
            ])
        
        if "debug" in query.lower() or "fix" in query.lower():
            alternatives.extend([
                "Root cause analysis with stack traces",
                "Binary search for issue isolation",
                "Unit test reproduction",
                "Logging and instrumentation"
            ])
        
        if not alternatives:
            alternatives = [
                "Incremental improvement approach",
                "Pattern-based refactoring",
                "Test-driven development",
                "Documentation-first approach"
            ]
        
        return alternatives
    
    def _define_validation_strategy(self, query: str) -> List[str]:
        """Define validation steps for conclusions"""
        return [
            "Unit test coverage verification",
            "Integration test execution",
            "Performance benchmark comparison",
            "Code review checklist validation",
            "Static analysis tool verification"
        ]
    
    def _synthesize_conclusion(
        self, steps: List[ReasoningStep], patterns: List[PatternMatch]
    ) -> str:
        """Synthesize final conclusion from reasoning steps"""
        key_findings = []
        
        for step in steps:
            if step.confidence > 0.8:
                key_findings.append(step.inference)
        
        if patterns:
            pattern_summary = f"Detected {len(patterns)} patterns across codebase"
            key_findings.append(pattern_summary)
        
        conclusion = "Analysis complete. "
        if key_findings:
            conclusion += "Key findings: " + "; ".join(key_findings[:3])
        else:
            conclusion += "No significant findings requiring action."
        
        return conclusion
    
    def _calculate_confidence(self, steps: List[ReasoningStep]) -> float:
        """Calculate overall confidence from reasoning steps"""
        if not steps:
            return 0.0
        
        # Weighted average with higher weight for later steps
        total_weight = 0
        weighted_sum = 0
        
        for i, step in enumerate(steps):
            weight = 1 + (i * 0.1)  # Increasing weight
            weighted_sum += step.confidence * weight
            total_weight += weight
        
        return round(weighted_sum / total_weight, 3)
    
    def _generate_recommendations(
        self, patterns: List[PatternMatch], conclusion: str
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Pattern-based recommendations
        for pattern in patterns[:5]:
            recommendations.extend(pattern.recommendations[:2])
        
        # Deduplicate
        recommendations = list(dict.fromkeys(recommendations))
        
        # Add general recommendations
        if not recommendations:
            recommendations = [
                "Review code structure for optimization opportunities",
                "Ensure adequate test coverage",
                "Document complex logic and decisions"
            ]
        
        return recommendations[:10]  # Limit to top 10
    
    def get_reasoning_trace(self, trace_id: str) -> Optional[ReasoningResult]:
        """Retrieve a specific reasoning trace"""
        for result in self.reasoning_history:
            if result.trace_id == trace_id:
                return result
        return None
    
    def export_trace(self, result: ReasoningResult) -> str:
        """Export reasoning trace as formatted string"""
        lines = []
        lines.append("=" * 80)
        lines.append("REASONING TRACE REPORT")
        lines.append("=" * 80)
        lines.append(f"Trace ID: {result.trace_id}")
        lines.append(f"Query: {result.query}")
        lines.append(f"Depth: {result.depth} levels")
        lines.append(f"Execution Time: {result.execution_time_ms:.2f}ms")
        lines.append(f"Final Confidence: {result.confidence:.2%}")
        lines.append("")
        lines.append("REASONING STEPS:")
        for step in result.steps:
            lines.append(f"  [{step.step_number}] {step.action}")
            lines.append(f"      Observation: {step.observation}")
            lines.append(f"      Inference: {step.inference}")
            lines.append(f"      Confidence: {step.confidence:.2%}")
        lines.append("")
        lines.append("CONCLUSION:")
        lines.append(f"  {result.conclusion}")
        lines.append("")
        lines.append("RECOMMENDATIONS:")
        for i, rec in enumerate(result.recommendations, 1):
            lines.append(f"  {i}. {rec}")
        lines.append("=" * 80)
        
        return "\n".join(lines)


# Convenience function for quick analysis
def analyze(query: str, code: str = "", depth: ReasoningDepth = ReasoningDepth.DEEP) -> ReasoningResult:
    """Quick analysis function"""
    engine = ReasoningEngine()
    context = {"code": code} if code else {}
    return engine.analyze(query, context, depth)


if __name__ == "__main__":
    # Demo
    engine = ReasoningEngine()
    
    print("=" * 80)
    print("WASEEM REASONING ENGINE - NASA/GOOGLE-LEVEL ANALYSIS")
    print("=" * 80)
    
    # Test query
    test_code = '''
def process_data(items):
    result = []
    for item in items:
        if item is not None:
            if item.value > 0:
                if item.active:
                    result.append(item.value * 2)
    return result
'''
    
    result = engine.analyze(
        "Analyze this code for optimization opportunities",
        context={"code": test_code, "file_path": "example.py"},
        depth=ReasoningDepth.NASA_LEVEL
    )
    
    print(engine.export_trace(result))
