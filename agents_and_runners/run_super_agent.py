#!/usr/bin/env python3
"""
WASEEM SUPER AGENT - Master Runner
Unified CLI interface for full-power autonomous agent

Usage:
    python run_super_agent.py [command] [options]

Commands:
    analyze     Deep analysis with NASA-level reasoning
    execute     Safe code execution with rollback
    generate    Generate code from templates
    validate    Quality validation (Google standards)
    learn       Run learning cycle
    status      Show system status
    query       Query the brain runtime
    mission     Execute autonomous mission
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import all components
try:
    from .reasoning_engine import (
        ReasoningEngine, ReasoningDepth, ReasoningResult, analyze
    )
    from .runtime_bridge import (
        RuntimeBridge, BridgeStatus, QueryResult, MemoryEntry
    )
    from .code_executor import (
        CodeExecutor, ExecutionMode, ExecutionResult, create_executor
    )
    from .code_generator import (
        CodeGenerator, GeneratedCode, generate_class, generate_function
    )
    from .quality_validator import (
        QualityValidator, QualityReport, validate_file
    )
    from .safety_protocols import (
        SafetyProtocols, SafetyReport, RiskLevel, create_safety_protocols
    )
    from .learning_engine import (
        LearningEngine, ExecutionTrace, create_learning_engine
    )
    from .feedback_loop import (
        FeedbackLoop, FeedbackEntry, CorrectionSuggestion, create_feedback_loop
    )
except ImportError:
    # Fallback for direct execution
    from reasoning_engine import (
        ReasoningEngine, ReasoningDepth, ReasoningResult, analyze
    )
    from runtime_bridge import (
        RuntimeBridge, BridgeStatus, QueryResult, MemoryEntry
    )
    from code_executor import (
        CodeExecutor, ExecutionMode, ExecutionResult, create_executor
    )
    from code_generator import (
        CodeGenerator, GeneratedCode, generate_class, generate_function
    )
    from quality_validator import (
        QualityValidator, QualityReport, validate_file
    )
    from safety_protocols import (
        SafetyProtocols, SafetyReport, RiskLevel, create_safety_protocols
    )
    from learning_engine import (
        LearningEngine, ExecutionTrace, create_learning_engine
    )
    from feedback_loop import (
        FeedbackLoop, FeedbackEntry, CorrectionSuggestion, create_feedback_loop
    )


class WaseemSuperAgent:
    """
    Unified Super Agent with full power capabilities
    
    Integrates:
    - Deep Reasoning Engine (NASA-level)
    - Runtime Bridge (Brain integration)
    - Code Executor (Safe execution)
    - Code Generator (Template synthesis)
    - Quality Validator (Google standards)
    - Safety Protocols (Rollback)
    - Learning Engine (Self-improvement)
    - Feedback Loop (Corrections)
    """
    
    def __init__(self, project_root: Path | None = None):
        self.project_root = Path(project_root) if project_root else PROJECT_ROOT
        
        # Initialize all components
        self.reasoning = ReasoningEngine(self.project_root)
        self.runtime = RuntimeBridge(auto_initialize=False)
        self.executor = create_executor(self.project_root, ExecutionMode.SAFE)
        self.generator = CodeGenerator()
        self.validator = QualityValidator()
        self.safety = create_safety_protocols(self.project_root)
        self.learning = create_learning_engine(self.project_root)
        self.feedback = create_feedback_loop(self.project_root)
        
        self._initialized = False
        self._mission_counter = 0
    
    def initialize(self) -> Dict[str, Any]:
        """Initialize all components"""
        results = {}
        
        # Initialize runtime bridge
        try:
            status = self.runtime.initialize()
            results["runtime"] = {
                "connected": status.connected,
                "experts_loaded": status.experts_loaded
            }
        except Exception as e:
            results["runtime"] = {"error": str(e)}
        
        # Load learned knowledge
        try:
            self.learning.load_knowledge()
            results["learning"] = {"loaded": True}
        except Exception as e:
            results["learning"] = {"loaded": False, "error": str(e)}
        
        self._initialized = True
        results["status"] = "initialized"
        results["timestamp"] = datetime.now().isoformat()
        
        return results
    
    def analyze(
        self,
        query: str,
        code: str = "",
        depth: str = "deep"
    ) -> ReasoningResult:
        """Run deep analysis with reasoning engine"""
        depth_map = {
            "surface": ReasoningDepth.SURFACE,
            "standard": ReasoningDepth.STANDARD,
            "deep": ReasoningDepth.DEEP,
            "exhaustive": ReasoningDepth.EXHAUSTIVE,
            "nasa": ReasoningDepth.NASA_LEVEL,
        }
        
        reasoning_depth = depth_map.get(depth.lower(), ReasoningDepth.DEEP)
        
        context = {"code": code} if code else {}
        
        return self.reasoning.analyze(query, context, reasoning_depth)
    
    async def query_brain(
        self,
        text: str,
        session_id: str | None = None
    ) -> QueryResult:
        """Query the brain runtime"""
        if not self.runtime._initialized:
            self.runtime.initialize()
        
        return await self.runtime.query(text, session_id)
    
    def execute_code(
        self,
        file_path: Path,
        content: str,
        dry_run: bool = False,
        validate: bool = True
    ) -> ExecutionResult:
        """Execute code modification with safety"""
        if dry_run:
            self.executor.mode = ExecutionMode.DRY_RUN
        else:
            self.executor.mode = ExecutionMode.SAFE
        
        return self.executor.write_file(file_path, content, validate)
    
    def generate_code(
        self,
        template_type: str,
        params: Dict[str, Any]
    ) -> GeneratedCode:
        """Generate code from template"""
        if template_type == "class":
            return self.generator.generate_class(
                class_name=params.get("name", "GeneratedClass"),
                description=params.get("description", ""),
                fields=params.get("fields", []),
                methods=params.get("methods", []),
                language=params.get("language", "python")
            )
        elif template_type == "function":
            return self.generator.generate_function(
                name=params.get("name", "generated_function"),
                description=params.get("description", ""),
                params=params.get("params", []),
                return_type=params.get("return_type", "Any"),
                body=params.get("body", "pass")
            )
        elif template_type == "test":
            return self.generator.generate_test(
                module_name=params.get("module", "module"),
                class_or_function=params.get("target", "Target"),
                test_cases=params.get("cases", [])
            )
        else:
            return GeneratedCode(
                code="",
                language="unknown",
                description=f"Unknown template: {template_type}",
                confidence=0.0
            )
    
    def validate_quality(
        self,
        file_path: Path
    ) -> QualityReport:
        """Validate code quality"""
        return self.validator.validate_file(file_path)
    
    def run_learning(self) -> Dict[str, Any]:
        """Run learning cycle"""
        return self.learning.learn()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "project_root": str(self.project_root),
            "initialized": self._initialized,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Runtime status
        runtime_status = self.runtime.get_status()
        status["runtime"] = {
            "connected": runtime_status.connected,
            "experts_loaded": runtime_status.experts_loaded,
            "memory_available": runtime_status.memory_available
        }
        
        # Learning status
        learning_summary = self.learning.get_learning_summary()
        status["learning"] = learning_summary
        
        # Feedback status
        feedback_summary = self.feedback.get_feedback_summary()
        status["feedback"] = feedback_summary
        
        # Reasoning history
        status["reasoning"] = {
            "traces_count": len(self.reasoning.reasoning_history)
        }
        
        return status
    
    def execute_mission(
        self,
        mission: str,
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """Execute an autonomous mission"""
        self._mission_counter += 1
        mission_id = f"mission-{self._mission_counter}-{int(time.time())}"
        
        start_time = time.time()
        results = {
            "mission_id": mission_id,
            "mission": mission,
            "status": "started",
            "steps": []
        }
        
        # Step 1: Analyze mission with reasoning
        analysis = self.analyze(
            f"Analyze mission requirements: {mission}",
            depth="nasa"
        )
        results["steps"].append({
            "step": "analysis",
            "status": "completed",
            "confidence": analysis.confidence
        })
        
        # Step 2: Generate execution plan from reasoning
        plan = self._generate_plan(analysis)
        results["steps"].append({
            "step": "planning",
            "status": "completed",
            "plan_steps": len(plan)
        })
        
        # Step 3: Validate plan with safety
        safety_reports = []
        for step in plan:
            if step.get("target_files"):
                op_id, report = self.safety.prepare_operation(
                    operation=step.get("action", "unknown"),
                    target_paths=[Path(f) for f in step.get("target_files", [])],
                    auto_approve=auto_approve
                )
                safety_reports.append({
                    "operation_id": op_id,
                    "risk_level": report.risk_level.value,
                    "approved": report.approval_status.value
                })
        
        results["steps"].append({
            "step": "safety_check",
            "status": "completed",
            "reports": safety_reports
        })
        
        # Step 4: Execute approved steps
        executed = []
        for i, step in enumerate(plan):
            if i < len(safety_reports):
                sr = safety_reports[i]
                if sr["approved"] in ("approved", "auto_approved"):
                    # Execute step
                    exec_result = self._execute_step(step)
                    executed.append({
                        "step": step.get("action"),
                        "success": exec_result.get("success", False)
                    })
                    
                    # Record for learning
                    self.learning.record_execution(
                        operation=step.get("action", "unknown"),
                        inputs=step,
                        outputs=exec_result,
                        success=exec_result.get("success", False),
                        duration_ms=exec_result.get("duration_ms", 0)
                    )
        
        results["steps"].append({
            "step": "execution",
            "status": "completed",
            "executed": executed
        })
        
        # Step 5: Learn from execution
        learning_result = self.learning.learn()
        results["steps"].append({
            "step": "learning",
            "status": "completed",
            "patterns": learning_result.get("patterns_learned", 0)
        })
        
        # Finalize
        execution_time = (time.time() - start_time) * 1000
        results["status"] = "completed"
        results["execution_time_ms"] = round(execution_time, 2)
        results["timestamp"] = datetime.now().isoformat()
        
        return results
    
    def _generate_plan(self, analysis: ReasoningResult) -> List[Dict[str, Any]]:
        """Generate execution plan from reasoning"""
        plan = []
        
        # Use recommendations as plan steps
        for i, rec in enumerate(analysis.recommendations[:5]):
            plan.append({
                "step": i + 1,
                "action": "implement",
                "description": rec,
                "target_files": [],
                "priority": "medium"
            })
        
        return plan
    
    def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step"""
        start = time.time()
        
        # Placeholder execution
        result = {
            "success": True,
            "message": f"Executed: {step.get('description', 'unknown')}",
            "duration_ms": (time.time() - start) * 1000
        }
        
        return result


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Waseem Super Agent - Full Power Autonomous Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_super_agent.py analyze "optimize this function" --code "def foo(): pass"
    python run_super_agent.py execute test.py --content "print('hello')"
    python run_super_agent.py generate class --name MyModel --fields '[{"name":"id","type":"int"}]'
    python run_super_agent.py validate src/main.py
    python run_super_agent.py learn
    python run_super_agent.py status
    python run_super_agent.py mission "refactor authentication module"
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Deep analysis with reasoning")
    analyze_parser.add_argument("query", help="Analysis query")
    analyze_parser.add_argument("--code", default="", help="Code to analyze")
    analyze_parser.add_argument("--depth", choices=["surface", "standard", "deep", "exhaustive", "nasa"],
                                default="deep", help="Analysis depth")
    
    # Execute command
    execute_parser = subparsers.add_parser("execute", help="Safe code execution")
    execute_parser.add_argument("file", help="File path to write")
    execute_parser.add_argument("--content", required=True, help="File content")
    execute_parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    execute_parser.add_argument("--no-validate", action="store_true", help="Skip validation")
    
    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate code")
    generate_parser.add_argument("type", choices=["class", "function", "test"],
                                 help="Template type")
    generate_parser.add_argument("--name", default="Generated", help="Name")
    generate_parser.add_argument("--description", default="", help="Description")
    generate_parser.add_argument("--fields", default="[]", help="Fields JSON")
    generate_parser.add_argument("--methods", default="[]", help="Methods JSON")
    generate_parser.add_argument("--params", default="[]", help="Parameters JSON")
    generate_parser.add_argument("--return-type", default="Any", help="Return type")
    generate_parser.add_argument("--language", default="python", help="Language")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Quality validation")
    validate_parser.add_argument("file", help="File to validate")
    
    # Learn command
    learn_parser = subparsers.add_parser("learn", help="Run learning cycle")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show system status")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query brain runtime")
    query_parser.add_argument("text", help="Query text")
    
    # Mission command
    mission_parser = subparsers.add_parser("mission", help="Execute autonomous mission")
    mission_parser.add_argument("description", help="Mission description")
    mission_parser.add_argument("--auto-approve", action="store_true", help="Auto-approve operations")
    
    return parser


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create agent
    agent = WaseemSuperAgent()
    
    # Initialize
    print(f"\n{'='*80}")
    print("WASEEM SUPER AGENT - FULL POWER MODE")
    print(f"{'='*80}\n")
    
    init_result = agent.initialize()
    print(f"[INIT] Status: {init_result.get('status', 'unknown')}")
    
    # Execute command
    if args.command == "analyze":
        print(f"\n[ANALYZE] Query: {args.query}")
        print(f"[ANALYZE] Depth: {args.depth}")
        
        result = agent.analyze(args.query, args.code, args.depth)
        
        print(f"\n[RESULT]")
        print(f"  Confidence: {result.confidence:.2%}")
        print(f"  Steps: {len(result.steps)}")
        print(f"  Patterns: {len(result.patterns)}")
        print(f"\n[CONCLUSION]")
        print(f"  {result.conclusion}")
        
        if result.recommendations:
            print(f"\n[RECOMMENDATIONS]")
            for i, rec in enumerate(result.recommendations[:5], 1):
                print(f"  {i}. {rec}")
    
    elif args.command == "execute":
        file_path = Path(args.file)
        print(f"\n[EXECUTE] File: {file_path}")
        print(f"[EXECUTE] Mode: {'dry-run' if args.dry_run else 'safe'}")
        
        result = agent.execute_code(
            file_path,
            args.content,
            dry_run=args.dry_run,
            validate=not args.no_validate
        )
        
        print(f"\n[RESULT]")
        print(f"  Success: {result.success}")
        print(f"  Status: {result.status.value}")
        print(f"  Message: {result.message}")
        
        if result.error:
            print(f"  Error: {result.error}")
    
    elif args.command == "generate":
        print(f"\n[GENERATE] Type: {args.type}")
        print(f"[GENERATE] Name: {args.name}")
        
        import json as json_mod
        
        params = {
            "name": args.name,
            "description": args.description,
            "fields": json_mod.loads(args.fields) if args.fields else [],
            "methods": json_mod.loads(args.methods) if args.methods else [],
            "params": json_mod.loads(args.params) if args.params else [],
            "return_type": args.return_type,
            "language": args.language
        }
        
        result = agent.generate_code(args.type, params)
        
        print(f"\n[RESULT]")
        print(f"  Language: {result.language}")
        print(f"  Confidence: {result.confidence:.2%}")
        print(f"\n[CODE]")
        print(result.code)
    
    elif args.command == "validate":
        file_path = Path(args.file)
        print(f"\n[VALIDATE] File: {file_path}")
        
        result = agent.validate_quality(file_path)
        
        print(f"\n[RESULT]")
        print(f"  Passed: {result.passed}")
        print(f"  Score: {result.score}")
        print(f"  Summary: {result.summary}")
        
        if result.issues:
            print(f"\n[ISSUES] ({len(result.issues)})")
            for issue in result.issues[:10]:
                print(f"  [{issue.severity}] Line {issue.line}: {issue.message}")
    
    elif args.command == "learn":
        print(f"\n[LEARN] Running learning cycle...")
        
        result = agent.run_learning()
        
        print(f"\n[RESULT]")
        print(f"  Status: {result.get('status')}")
        print(f"  Patterns: {result.get('patterns_learned', 0)}")
        print(f"  Strategies: {result.get('strategies_learned', 0)}")
        print(f"  Insights: {result.get('insights_generated', 0)}")
    
    elif args.command == "status":
        print(f"\n[STATUS]")
        
        status = agent.get_status()
        
        print(f"  Project: {status.get('project_root')}")
        print(f"  Initialized: {status.get('initialized')}")
        print(f"\n  [RUNTIME]")
        runtime = status.get("runtime", {})
        print(f"    Connected: {runtime.get('connected')}")
        print(f"    Experts: {runtime.get('experts_loaded')}")
        print(f"\n  [LEARNING]")
        learning = status.get("learning", {})
        print(f"    Traces: {learning.get('total_traces')}")
        print(f"    Patterns: {learning.get('patterns_learned')}")
        print(f"\n  [FEEDBACK]")
        feedback = status.get("feedback", {})
        print(f"    Success Rate: {feedback.get('success_rate', 0):.1%}")
    
    elif args.command == "query":
        print(f"\n[QUERY] {args.text}")
        
        result = asyncio.run(agent.query_brain(args.text))
        
        print(f"\n[RESULT]")
        print(f"  Success: {result.success}")
        print(f"  Content: {result.content[:500]}...")
        
        if result.error:
            print(f"  Error: {result.error}")
    
    elif args.command == "mission":
        print(f"\n[MISSION] {args.description}")
        print(f"[MISSION] Auto-approve: {args.auto_approve}")
        
        result = agent.execute_mission(args.description, args.auto_approve)
        
        print(f"\n[RESULT]")
        print(f"  Mission ID: {result.get('mission_id')}")
        print(f"  Status: {result.get('status')}")
        print(f"  Time: {result.get('execution_time_ms')}ms")
        
        print(f"\n[STEPS]")
        for step in result.get("steps", []):
            print(f"  [{step.get('step')}] {step.get('status')}")
    
    print(f"\n{'='*80}")
    print("[DONE]")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
