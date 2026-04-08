"""Logical Inference Engine for Waseem Brain.

Implements forward/backward chaining, constraint satisfaction, and logical
inference rules to enhance reasoning capabilities across domains.
"""

from dataclasses import dataclass
from typing import Optional, Callable
from enum import Enum


class InferenceStrategy(Enum):
    """Strategies for logical inference."""
    FORWARD_CHAINING = "forward"
    BACKWARD_CHAINING = "backward"
    CONSTRAINT_SATISFACTION = "constraint"
    BAYESIAN = "bayesian"


@dataclass
class LogicalFact:
    """Represents a logical fact in the knowledge base."""
    predicate: str  # e.g., "is_animal", "is_mortal"
    subject: str  # e.g., "socrates", "fluffy"
    value: bool = True
    confidence: float = 1.0
    metadata: dict = None
    
    def __repr__(self) -> str:
        return f"{self.subject} {self.predicate}={self.value}"


@dataclass
class Rule:
    """Represents a logical inference rule."""
    id: str
    name: str
    conditions: list[LogicalFact]  # If ALL conditions met
    conclusion: LogicalFact  # Then conclude this
    confidence: float = 1.0  # Rule confidence
    explanation: str = ""
    
    def __repr__(self) -> str:
        return f"Rule({self.name}): {self.conditions} → {self.conclusion}"


class LogicalKnowledgeBase:
    """Knowledge base for storing facts and rules."""
    
    def __init__(self):
        """Initialize knowledge base."""
        self.facts: list[LogicalFact] = []
        self.rules: list[Rule] = []
    
    def add_fact(self, fact: LogicalFact) -> None:
        """Add a fact to the knowledge base.
        
        Args:
            fact: LogicalFact to add
        """
        if fact not in self.facts:
            self.facts.append(fact)
    
    def add_rule(self, rule: Rule) -> None:
        """Add an inference rule.
        
        Args:
            rule: Rule to add
        """
        if rule.id not in [r.id for r in self.rules]:
            self.rules.append(rule)
    
    def get_facts_about(self, subject: str) -> list[LogicalFact]:
        """Get all facts about a subject.
        
        Args:
            subject: The subject to query
            
        Returns:
            List of facts about the subject
        """
        return [f for f in self.facts if f.subject == subject]
    
    def has_fact(self, predicate: str, subject: str) -> bool:
        """Check if a fact exists.
        
        Args:
            predicate: The predicate
            subject: The subject
            
        Returns:
            True if fact exists and is true
        """
        for fact in self.facts:
            if fact.predicate == predicate and fact.subject == subject and fact.value:
                return True
        return False


class ForwardChainingEngine:
    """Forward chaining inference engine.
    
    Starts with known facts and applies rules to derive new facts
    until no new facts can be derived.
    """
    
    def __init__(self, kb: LogicalKnowledgeBase):
        """Initialize forward chaining engine.
        
        Args:
            kb: LogicalKnowledgeBase to use
        """
        self.kb = kb
        self.inferred_facts: list[LogicalFact] = []
        self.inference_trace: list[str] = []
    
    def infer(self) -> list[LogicalFact]:
        """Perform forward chaining inference.
        
        Returns:
            List of newly inferred facts
            
        Example:
            >>> kb = LogicalKnowledgeBase()
            >>> kb.add_fact(LogicalFact("is_human", "socrates"))
            >>> rule = Rule(
            ...     id="r1",
            ...     name="Mortality of humans",
            ...     conditions=[LogicalFact("is_human", "socrates")],
            ...     conclusion=LogicalFact("is_mortal", "socrates")
            ... )
            >>> kb.add_rule(rule)
            >>> engine = ForwardChainingEngine(kb)
            >>> new_facts = engine.infer()
        """
        new_facts_found = True
        iteration = 0
        
        while new_facts_found:
            iteration += 1
            new_facts_found = False
            
            # Try each rule
            for rule in self.kb.rules:
                # Check if all conditions are met
                conditions_met = all(
                    self.kb.has_fact(cond.predicate, cond.subject)
                    for cond in rule.conditions
                )
                
                if conditions_met:
                    # Add conclusion if not already known
                    if not self.kb.has_fact(rule.conclusion.predicate, 
                                           rule.conclusion.subject):
                        self.kb.add_fact(rule.conclusion)
                        self.inferred_facts.append(rule.conclusion)
                        new_facts_found = True
                        
                        # Log inference
                        trace = f"[Iter {iteration}] {rule.name}: {rule.conclusion}"
                        self.inference_trace.append(trace)
        
        return self.inferred_facts
    
    def get_trace(self) -> list[str]:
        """Get inference trace."""
        return self.inference_trace


class BackwardChainingEngine:
    """Backward chaining inference engine.
    
    Starts with a goal and works backwards to find facts/rules
    that support the goal.
    """
    
    def __init__(self, kb: LogicalKnowledgeBase):
        """Initialize backward chaining engine.
        
        Args:
            kb: LogicalKnowledgeBase to use
        """
        self.kb = kb
        self.proof_tree: dict = {}
        self.proof_trace: list[str] = []
    
    def prove(self, goal: LogicalFact, depth: int = 0) -> bool:
        """Attempt to prove a goal.
        
        Args:
            goal: The LogicalFact to prove
            depth: Recursion depth (prevents infinite loops)
            
        Returns:
            True if goal can be proven
            
        Example:
            >>> kb = LogicalKnowledgeBase()
            >>> kb.add_fact(LogicalFact("is_human", "socrates"))
            >>> rule = Rule(
            ...     id="r1",
            ...     name="All humans are mortal",
            ...     conditions=[LogicalFact("is_human", "socrates")],
            ...     conclusion=LogicalFact("is_mortal", "socrates")
            ... )
            >>> kb.add_rule(rule)
            >>> engine = BackwardChainingEngine(kb)
            >>> result = engine.prove(LogicalFact("is_mortal", "socrates"))
        """
        max_depth = 10
        if depth > max_depth:
            return False
        
        # Base case: check if goal is already a known fact
        if self.kb.has_fact(goal.predicate, goal.subject):
            self.proof_trace.append(f"{'  ' * depth}✓ Known fact: {goal}")
            return True
        
        # Recursive case: try to prove using rules
        for rule in self.kb.rules:
            # Check if rule's conclusion matches our goal
            if (rule.conclusion.predicate == goal.predicate and
                rule.conclusion.subject == goal.subject):
                
                self.proof_trace.append(f"{'  ' * depth}→ Trying rule: {rule.name}")
                
                # Try to prove all conditions
                all_conditions_met = True
                for condition in rule.conditions:
                    if not self.prove(condition, depth + 1):
                        all_conditions_met = False
                        break
                
                if all_conditions_met:
                    self.proof_trace.append(f"{'  ' * depth}✓ Proved: {goal}")
                    return True
        
        self.proof_trace.append(f"{'  ' * depth}✗ Cannot prove: {goal}")
        return False
    
    def get_proof(self) -> str:
        """Get proof trace as string."""
        return "\n".join(self.proof_trace)


class ConstraintSatisfactionEngine:
    """Constraint satisfaction problem solver."""
    
    def __init__(self):
        """Initialize CSP solver."""
        self.variables: dict[str, list] = {}  # var: [possible values]
        self.constraints: list[Callable] = []  # constraint functions
    
    def add_variable(self, name: str, domain: list) -> None:
        """Add variable with domain.
        
        Args:
            name: Variable name
            domain: List of possible values
        """
        self.variables[name] = domain
    
    def add_constraint(self, constraint: Callable) -> None:
        """Add constraint function.
        
        Args:
            constraint: Function that returns True if constraint satisfied
        """
        self.constraints.append(constraint)
    
    def solve(self) -> Optional[dict]:
        """Solve the CSP using backtracking.
        
        Returns:
            Assignment dictionary if solution found, None otherwise
            
        Example:
            >>> csp = ConstraintSatisfactionEngine()
            >>> csp.add_variable("X", [1, 2, 3])
            >>> csp.add_variable("Y", [1, 2, 3])
            >>> csp.add_constraint(lambda a, b: a + b <= 4)
            >>> solution = csp.solve()
        """
        var_names = list(self.variables.keys())
        return self._backtrack({}, var_names, 0)
    
    def _backtrack(self, assignment: dict, var_names: list[str], 
                   index: int) -> Optional[dict]:
        """Recursive backtracking solver.
        
        Args:
            assignment: Current assignment
            var_names: List of variable names
            index: Current variable index
            
        Returns:
            Complete assignment or None
        """
        if index == len(var_names):
            # Check if all constraints satisfied
            if self._check_constraints(assignment):
                return assignment
            return None
        
        var = var_names[index]
        for value in self.variables[var]:
            assignment[var] = value
            
            if self._is_consistent(assignment):
                result = self._backtrack(assignment, var_names, index + 1)
                if result is not None:
                    return result
            
            del assignment[var]
        
        return None
    
    def _is_consistent(self, assignment: dict) -> bool:
        """Check consistency of partial assignment."""
        return self._check_constraints(assignment)
    
    def _check_constraints(self, assignment: dict) -> bool:
        """Check if all constraints are satisfied."""
        for constraint in self.constraints:
            try:
                # Try calling constraint with assignment
                if not constraint(assignment):
                    return False
            except (KeyError, TypeError):
                # Skip constraints that can't be evaluated yet
                pass
        return True


# =============================================================================
# EXAMPLE USAGE: Classic Socrates Example
# =============================================================================
def create_socrates_example() -> tuple[LogicalKnowledgeBase, list[str]]:
    """Create the classic Socrates knowledge base.
    
    Returns:
        (knowledge_base, expected_conclusions)
    """
    kb = LogicalKnowledgeBase()
    
    # Add facts
    kb.add_fact(LogicalFact("is_human", "socrates"))
    
    # Add rule: All humans are mortal
    rule1 = Rule(
        id="r1",
        name="All humans are mortal",
        conditions=[LogicalFact("is_human", "socrates")],
        conclusion=LogicalFact("is_mortal", "socrates"),
        explanation="If someone is human, they are mortal"
    )
    kb.add_rule(rule1)
    
    # Add rule: All mortals die
    rule2 = Rule(
        id="r2",
        name="All mortals die",
        conditions=[LogicalFact("is_mortal", "socrates")],
        conclusion=LogicalFact("dies", "socrates"),
        explanation="If someone is mortal, they will die"
    )
    kb.add_rule(rule2)
    
    expected = [
        "socrates is_human=True",
        "socrates is_mortal=True",
        "socrates dies=True",
    ]
    
    return kb, expected
