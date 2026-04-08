"""Reasoning Quality Evaluation System.

Assesses the quality, correctness, and reasoning depth of responses
to ensure high-quality outputs from Waseem Brain.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json


class ReasoningQualityLevel(Enum):
    """Quality classification levels."""
    POOR = 1
    FAIR = 2
    GOOD = 3
    EXCELLENT = 4
    EXEMPLARY = 5


@dataclass
class ReasoningMetrics:
    """Metrics for evaluating reasoning quality."""
    clarity: float  # 0-1: How clear and understandable
    correctness: float  # 0-1: Factual correctness
    completeness: float  # 0-1: Covers all aspects
    logical_consistency: float  # 0-1: Internal logic sound
    evidence_quality: float  # 0-1: Quality of supporting evidence
    depth: float  # 0-1: Depth of analysis
    relevance: float  # 0-1: Relevance to question
    innovation: float  # 0-1: Novel insights
    
    def calculate_overall_score(self) -> float:
        """Calculate weighted overall quality score.
        
        Returns:
            Score from 0-100
        """
        weights = {
            'correctness': 0.30,      # Most important
            'logical_consistency': 0.25,
            'clarity': 0.15,
            'completeness': 0.10,
            'evidence_quality': 0.10,
            'depth': 0.05,
            'relevance': 0.03,
            'innovation': 0.02,
        }
        
        total = (
            self.correctness * weights['correctness'] +
            self.logical_consistency * weights['logical_consistency'] +
            self.clarity * weights['clarity'] +
            self.completeness * weights['completeness'] +
            self.evidence_quality * weights['evidence_quality'] +
            self.depth * weights['depth'] +
            self.relevance * weights['relevance'] +
            self.innovation * weights['innovation']
        )
        
        return round(total * 100, 2)
    
    def get_quality_level(self) -> ReasoningQualityLevel:
        """Get quality level classification."""
        score = self.calculate_overall_score()
        if score >= 90:
            return ReasoningQualityLevel.EXEMPLARY
        elif score >= 80:
            return ReasoningQualityLevel.EXCELLENT
        elif score >= 70:
            return ReasoningQualityLevel.GOOD
        elif score >= 50:
            return ReasoningQualityLevel.FAIR
        else:
            return ReasoningQualityLevel.POOR


@dataclass
class ReasoningQualityReport:
    """Complete quality evaluation report."""
    query: str
    response: str
    metrics: ReasoningMetrics
    issues: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "query": self.query,
            "overall_score": self.metrics.calculate_overall_score(),
            "quality_level": self.metrics.get_quality_level().name,
            "metrics": {
                "clarity": self.metrics.clarity,
                "correctness": self.metrics.correctness,
                "completeness": self.metrics.completeness,
                "logical_consistency": self.metrics.logical_consistency,
                "evidence_quality": self.metrics.evidence_quality,
                "depth": self.metrics.depth,
                "relevance": self.metrics.relevance,
                "innovation": self.metrics.innovation,
            },
            "issues": self.issues,
            "strengths": self.strengths,
            "improvements": self.improvements,
        }
    
    def to_json(self) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict(), indent=2)
    
    def __str__(self) -> str:
        """String representation."""
        score = self.metrics.calculate_overall_score()
        level = self.metrics.get_quality_level().name
        return f"Quality: {level} ({score}%)"


class ReasoningQualityEvaluator:
    """Evaluates reasoning quality across multiple dimensions."""
    
    def __init__(self):
        """Initialize evaluator."""
        self.evaluation_history: list[ReasoningQualityReport] = []
    
    def evaluate(self, query: str, response: str, 
                 reference_answer: Optional[str] = None) -> ReasoningQualityReport:
        """Evaluate reasoning quality of a response.
        
        Args:
            query: The original query
            response: The response to evaluate
            reference_answer: Known correct answer (optional)
            
        Returns:
            ReasoningQualityReport with detailed evaluation
            
        Example:
            >>> evaluator = ReasoningQualityEvaluator()
            >>> query = "What is 2+2?"
            >>> response = "2+2 equals 4 because..."
            >>> report = evaluator.evaluate(query, response, reference_answer="4")
        """
        metrics = self._calculate_metrics(query, response, reference_answer)
        issues = self._identify_issues(response)
        strengths = self._identify_strengths(response)
        improvements = self._suggest_improvements(response, issues)
        
        report = ReasoningQualityReport(
            query=query,
            response=response,
            metrics=metrics,
            issues=issues,
            strengths=strengths,
            improvements=improvements,
        )
        
        self.evaluation_history.append(report)
        return report
    
    def _calculate_metrics(self, query: str, response: str,
                          reference_answer: Optional[str]) -> ReasoningMetrics:
        """Calculate quality metrics.
        
        Args:
            query: Original query
            response: Response text
            reference_answer: Correct answer if available
            
        Returns:
            ReasoningMetrics object
        """
        # Clarity: based on sentence structure, complexity
        clarity = self._evaluate_clarity(response)
        
        # Correctness: based on matching reference answer
        correctness = self._evaluate_correctness(response, reference_answer)
        
        # Completeness: based on coverage of aspects
        completeness = self._evaluate_completeness(query, response)
        
        # Logical consistency: check for contradictions
        logical_consistency = self._evaluate_logical_consistency(response)
        
        # Evidence quality: assess supporting evidence
        evidence_quality = self._evaluate_evidence_quality(response)
        
        # Depth: check for analytical depth
        depth = self._evaluate_depth(response)
        
        # Relevance: check relevance to query
        relevance = self._evaluate_relevance(query, response)
        
        # Innovation: check for novel insights
        innovation = self._evaluate_innovation(response)
        
        return ReasoningMetrics(
            clarity=clarity,
            correctness=correctness,
            completeness=completeness,
            logical_consistency=logical_consistency,
            evidence_quality=evidence_quality,
            depth=depth,
            relevance=relevance,
            innovation=innovation,
        )
    
    def _evaluate_clarity(self, response: str) -> float:
        """Evaluate clarity of response.
        
        Checks for clear structure, simple language, organization.
        """
        # Simple heuristics
        has_structure = bool(response.count('\n') > 1)
        has_examples = bool('example' in response.lower())
        has_explanation = bool('because' in response.lower() or 'reason' in response.lower())
        
        score = 0.6  # Base
        if has_structure:
            score += 0.15
        if has_examples:
            score += 0.10
        if has_explanation:
            score += 0.15
        
        return min(1.0, score)
    
    def _evaluate_correctness(self, response: str, 
                             reference_answer: Optional[str]) -> float:
        """Evaluate factual correctness."""
        if reference_answer is None:
            return 0.5  # Neutral if no reference
        
        # Simple string matching
        ref_lower = reference_answer.lower()
        resp_lower = response.lower()
        
        if ref_lower in resp_lower:
            return 0.95
        elif ref_lower.split()[0] in resp_lower:
            return 0.70
        else:
            return 0.20
    
    def _evaluate_completeness(self, query: str, response: str) -> float:
        """Evaluate how complete the response is."""
        response_length = len(response.split())
        
        # Heuristics: longer doesn't mean complete, but too short is incomplete
        if response_length < 10:
            return 0.3
        elif response_length < 30:
            return 0.6
        elif response_length < 100:
            return 0.8
        else:
            return 0.95
    
    def _evaluate_logical_consistency(self, response: str) -> float:
        """Check for logical contradictions."""
        # Look for contradiction patterns
        contradictions = 0
        
        # Simple patterns
        if 'but not' in response.lower() and 'but' in response.lower():
            contradictions += 0.1
        
        lines = response.split('\n')
        prev_statement = ""
        for line in lines:
            # Check for obvious contradictions (very simple)
            if prev_statement and len(line) > 10:
                prev_statement = line
        
        # Neutral score unless clear contradictions detected
        return max(0.7, 1.0 - contradictions)
    
    def _evaluate_evidence_quality(self, response: str) -> float:
        """Assess quality of supporting evidence."""
        has_facts = bool('fact' in response.lower() or 'evidence' in response.lower())
        has_examples = bool('example' in response.lower())
        has_citations = bool('based on' in response.lower() or 'according to' in response.lower())
        
        score = 0.5
        if has_facts:
            score += 0.20
        if has_examples:
            score += 0.15
        if has_citations:
            score += 0.15
        
        return min(1.0, score)
    
    def _evaluate_depth(self, response: str) -> float:
        """Evaluate analytical depth."""
        # Check for deeper analysis indicators
        has_why = bool('why' in response.lower())
        has_analysis = bool('analys' in response.lower() or 'consider' in response.lower())
        has_implications = bool('therefore' in response.lower() or 'implies' in response.lower())
        
        response_length = len(response.split())
        
        score = 0.4
        if response_length > 50:
            score += 0.20
        if has_why:
            score += 0.15
        if has_analysis:
            score += 0.15
        if has_implications:
            score += 0.10
        
        return min(1.0, score)
    
    def _evaluate_relevance(self, query: str, response: str) -> float:
        """Evaluate relevance to original query."""
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        
        # Calculate word overlap
        overlap = len(query_words & response_words)
        
        if overlap / len(query_words) > 0.7:
            return 0.95
        elif overlap / len(query_words) > 0.5:
            return 0.80
        elif overlap / len(query_words) > 0.3:
            return 0.60
        else:
            return 0.40
    
    def _evaluate_innovation(self, response: str) -> float:
        """Detect novel or insightful content."""
        # Look for indicators of novel thinking
        has_new_perspective = bool('novel' in response.lower() or 'unique' in response.lower())
        has_synthesis = bool('combine' in response.lower() or 'integrate' in response.lower())
        has_insight = bool('insight' in response.lower() or 'realize' in response.lower())
        
        score = 0.3  # Most responses aren't particularly novel
        if has_new_perspective:
            score += 0.25
        if has_synthesis:
            score += 0.25
        if has_insight:
            score += 0.20
        
        return min(1.0, score)
    
    def _identify_issues(self, response: str) -> list[str]:
        """Identify quality issues in response."""
        issues = []
        
        if len(response) < 20:
            issues.append("Response too brief")
        
        if response.count('?') > 3:
            issues.append("Too many questions instead of assertions")
        
        if 'i don\'t know' in response.lower():
            issues.append("Lack of confident assertion")
        
        if response.count('...') > 2:
            issues.append("Incomplete thoughts indicated by ellipsis")
        
        return issues
    
    def _identify_strengths(self, response: str) -> list[str]:
        """Identify strengths in response."""
        strengths = []
        
        if len(response) > 100:
            strengths.append("Comprehensive response")
        
        if 'because' in response.lower() or 'reason' in response.lower():
            strengths.append("Explains reasoning")
        
        if 'example' in response.lower():
            strengths.append("Includes concrete examples")
        
        if response.count('\n') > 2:
            strengths.append("Well-structured with clear sections")
        
        return strengths
    
    def _suggest_improvements(self, response: str, issues: list[str]) -> list[str]:
        """Suggest improvements."""
        suggestions = []
        
        if "Response too brief" in issues:
            suggestions.append("Expand with more detailed explanation")
        
        if "Too many questions" in issues:
            suggestions.append("Provide more direct statements")
        
        if "Lack of confident assertion" in issues:
            suggestions.append("Ground response in concrete facts")
        
        if len(response.split()) < 50:
            suggestions.append("Add supporting examples and evidence")
        
        return suggestions
    
    def get_history(self) -> list[ReasoningQualityReport]:
        """Get evaluation history."""
        return self.evaluation_history
    
    def get_average_quality(self) -> float:
        """Get average quality score across evaluations."""
        if not self.evaluation_history:
            return 0.0
        
        total = sum(r.metrics.calculate_overall_score() for r in self.evaluation_history)
        return round(total / len(self.evaluation_history), 2)
