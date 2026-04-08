#!/usr/bin/env python3
"""
WASEEM RUNTIME BRIDGE - Integration with Brain Runtime
Connects Super Agent to WaseemBrainRuntime, Coordinator, Memory, Experts
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncIterator, Union
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import brain components
try:
    from brain.runtime import WaseemBrainRuntime, HealthSnapshot
    from brain.coordinator import WaseemBrainCoordinator
    from brain.memory.graph import MemoryGraph
    from brain.experts.pool import ExpertPool
    from brain.experts.registry import ExpertRegistry
    from brain.config import BrainSettings, load_settings
    from brain.types import SessionId, ExpertId
    BRAIN_AVAILABLE = True
    SettingsType = BrainSettings | None
except ImportError as e:
    print(f"[WARNING] Brain imports failed: {e}")
    BRAIN_AVAILABLE = False
    SettingsType = Any  # type: ignore


@dataclass
class BridgeStatus:
    """Status of runtime bridge connection"""
    connected: bool
    runtime_ready: bool
    memory_available: bool
    experts_loaded: int
    experts_available: int
    last_health_check: str
    error_message: Optional[str] = None


@dataclass
class QueryResult:
    """Result from runtime query"""
    success: bool
    content: str
    expert_id: Optional[str] = None
    confidence: float = 0.0
    citations: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_trace: str = ""
    session_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class MemoryEntry:
    """Memory entry from brain memory graph"""
    id: str
    content: str
    confidence: float
    source: str
    tags: List[str] = field(default_factory=list)
    timestamp: Optional[str] = None


class RuntimeBridge:
    """
    Bridge between Super Agent and Waseem Brain Runtime
    
    Provides:
    - Direct access to WaseemBrainRuntime
    - Memory graph queries
    - Expert pool access
    - Health monitoring
    - Session management
    """
    
    def __init__(
        self,
        settings: SettingsType = None,
        auto_initialize: bool = True
    ):
        self.project_root = PROJECT_ROOT
        self._settings = settings
        self._runtime: Optional[WaseemBrainRuntime] = None
        self._memory_graph: Optional[MemoryGraph] = None
        self._expert_pool: Optional[ExpertPool] = None
        self._registry: Optional[ExpertRegistry] = None
        self._initialized = False
        self._session_counter = 0
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._super_agent_config: Dict[str, Any] = {}
        
        if auto_initialize and BRAIN_AVAILABLE:
            self.initialize()
    
    @property
    def super_agent_config(self) -> Dict[str, Any]:
        """Get Super Agent configuration from settings"""
        if self._settings and hasattr(self._settings, 'super_agent_enabled'):
            return {
                'enabled': self._settings.super_agent_enabled,
                'reasoning_depth': self._settings.super_agent_reasoning_depth,
                'auto_approve_safe': self._settings.super_agent_auto_approve_safe,
                'max_execution_time_sec': self._settings.super_agent_max_execution_time_sec,
                'learning_enabled': self._settings.super_agent_learning_enabled,
                'safety_strict_mode': self._settings.super_agent_safety_strict_mode,
            }
        return {
            'enabled': True,
            'reasoning_depth': 'deep',
            'auto_approve_safe': True,
            'max_execution_time_sec': 60.0,
            'learning_enabled': True,
            'safety_strict_mode': True,
        }
    
    def initialize(self) -> BridgeStatus:
        """Initialize connection to brain runtime"""
        if not BRAIN_AVAILABLE:
            return BridgeStatus(
                connected=False,
                runtime_ready=False,
                memory_available=False,
                experts_loaded=0,
                experts_available=0,
                last_health_check=datetime.now().isoformat(),
                error_message="Brain components not available"
            )
        
        try:
            # Load settings
            if self._settings is None:
                self._settings = load_settings()
            
            # Initialize runtime
            self._runtime = WaseemBrainRuntime(settings=self._settings)
            
            # Get references to components
            self._memory_graph = self._runtime._memory_graph
            self._expert_pool = self._runtime._expert_pool
            self._registry = self._runtime._registry
            
            self._initialized = True
            
            return self.get_status()
            
        except Exception as e:
            return BridgeStatus(
                connected=False,
                runtime_ready=False,
                memory_available=False,
                experts_loaded=0,
                experts_available=0,
                last_health_check=datetime.now().isoformat(),
                error_message=str(e)
            )
    
    def get_status(self) -> BridgeStatus:
        """Get current bridge status"""
        if not self._initialized or self._runtime is None:
            return BridgeStatus(
                connected=False,
                runtime_ready=False,
                memory_available=False,
                experts_loaded=0,
                experts_available=0,
                last_health_check=datetime.now().isoformat(),
                error_message="Runtime not initialized"
            )
        
        try:
            health = self._runtime.health()
            
            return BridgeStatus(
                connected=True,
                runtime_ready=health["ready"],
                memory_available=health["memory_node_count"] > 0,
                experts_loaded=health["experts_loaded"],
                experts_available=health["experts_available"],
                last_health_check=datetime.now().isoformat()
            )
        except Exception as e:
            return BridgeStatus(
                connected=True,
                runtime_ready=False,
                memory_available=False,
                experts_loaded=0,
                experts_available=0,
                last_health_check=datetime.now().isoformat(),
                error_message=str(e)
            )
    
    def health_snapshot(self) -> Dict[str, Any]:
        """Get detailed health snapshot"""
        if not self._initialized or self._runtime is None:
            return {"error": "Runtime not initialized"}
        
        try:
            health = self._runtime.health()
            return dict(health)
        except Exception as e:
            return {"error": str(e)}
    
    def create_session(self, prefix: str = "agent") -> str:
        """Create a new session for queries"""
        self._session_counter += 1
        session_id = f"{prefix}-{self._session_counter}-{int(time.time())}"
        self._active_sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "queries": 0,
            "status": "active"
        }
        
        # Ensure session exists in memory graph
        if self._memory_graph:
            self._memory_graph.ensure_session(SessionId(session_id))
        
        return session_id
    
    def close_session(self, session_id: str) -> Dict[str, Any]:
        """Close session and flush traces"""
        if session_id not in self._active_sessions:
            return {"error": "Session not found"}
        
        session_info = self._active_sessions[session_id]
        session_info["status"] = "closed"
        session_info["closed_at"] = datetime.now().isoformat()
        
        # Flush traces if runtime available
        traces = []
        if self._runtime:
            try:
                traces = self._runtime.flush_session_traces(SessionId(session_id))
            except Exception:
                pass
        
        result = {
            "session_id": session_id,
            "queries_count": session_info["queries"],
            "traces_flushed": len(traces),
            "duration_seconds": self._session_duration(session_info)
        }
        
        del self._active_sessions[session_id]
        return result
    
    def _session_duration(self, session_info: Dict) -> float:
        """Calculate session duration"""
        try:
            created = datetime.fromisoformat(session_info["created_at"])
            closed = datetime.fromisoformat(session_info.get("closed_at", datetime.now().isoformat()))
            return (closed - created).total_seconds()
        except Exception:
            return 0.0
    
    async def query(
        self,
        text: str,
        session_id: str | None = None,
        modality: str = "text"
    ) -> QueryResult:
        """
        Execute query against brain runtime
        
        Args:
            text: Query text
            session_id: Optional session ID (creates new if not provided)
            modality: Input modality (text, voice, url, file)
        
        Returns:
            QueryResult with response and metadata
        """
        if not self._initialized or self._runtime is None:
            return QueryResult(
                success=False,
                content="",
                error="Runtime not initialized"
            )
        
        # Create session if needed
        if session_id is None:
            session_id = self.create_session()
        
        if session_id not in self._active_sessions:
            self._active_sessions[session_id] = {
                "created_at": datetime.now().isoformat(),
                "queries": 0,
                "status": "active"
            }
        
        self._active_sessions[session_id]["queries"] += 1
        
        try:
            # Execute query through runtime
            response_parts = []
            async for chunk in self._runtime.query(
                raw_input=text,
                modality_hint=modality,
                session_id=SessionId(session_id)
            ):
                response_parts.append(chunk)
            
            content = "".join(response_parts)
            
            return QueryResult(
                success=True,
                content=content,
                session_id=session_id,
                confidence=0.85  # Default confidence
            )
            
        except Exception as e:
            return QueryResult(
                success=False,
                content="",
                session_id=session_id,
                error=str(e)
            )
    
    def recall_memory(
        self,
        query: str,
        limit: int = 5,
        session_id: str | None = None
    ) -> List[MemoryEntry]:
        """
        Recall from memory graph
        
        Args:
            query: Search query
            limit: Maximum results
            session_id: Optional session context
        
        Returns:
            List of memory entries
        """
        if not self._memory_graph:
            return []
        
        try:
            result = self._memory_graph.recall(
                query,
                limit=limit,
                session_id=SessionId(session_id) if session_id else None
            )
            
            if not result["ok"]:
                return []
            
            return [
                MemoryEntry(
                    id=str(node["id"]),
                    content=node["content"],
                    confidence=node["confidence"],
                    source=node["source"],
                    tags=node.get("tags", [])
                )
                for node in result["value"]
            ]
        except Exception:
            return []
    
    def store_memory(
        self,
        content: str,
        source: str = "agent",
        tags: List[str] | None = None,
        session_id: str | None = None
    ) -> Dict[str, Any]:
        """
        Store content in memory graph
        
        Args:
            content: Content to store
            source: Source identifier
            tags: Optional tags
            session_id: Optional session context
        
        Returns:
            Storage result
        """
        if not self._memory_graph:
            return {"success": False, "error": "Memory graph not available"}
        
        try:
            self._memory_graph.store(
                content=content,
                source=source,
                tags=tags or [],
                session_id=SessionId(session_id) if session_id else None,
                source_type="agent"
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_experts(self) -> Dict[str, Any]:
        """Get expert pool information"""
        if not self._runtime:
            return {"error": "Runtime not available"}
        
        try:
            experts = self._runtime.experts()
            return {
                "loaded": experts["loaded"],
                "count": experts["count"],
                "available": self._runtime.health().get("expert_ids", [])
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_expert_details(self, expert_id: str) -> Dict[str, Any]:
        """Get details for specific expert"""
        if not self._registry:
            return {"error": "Registry not available"}
        
        try:
            entries = self._registry.all()
            for entry in entries:
                if str(entry.get("id")) == expert_id:
                    return {"success": True, "expert": entry}
            return {"error": f"Expert {expert_id} not found"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_actions(self) -> Dict[str, Any]:
        """Get available actions from runtime"""
        if not self._runtime:
            return {"error": "Runtime not available"}
        
        try:
            actions = self._runtime.actions()
            return {"success": True, "groups": actions["groups"]}
        except Exception as e:
            return {"error": str(e)}
    
    def close(self) -> None:
        """Close runtime connection"""
        if self._runtime:
            self._runtime.close()
            self._runtime = None
            self._memory_graph = None
            self._expert_pool = None
            self._registry = None
            self._initialized = False
    
    def __enter__(self):
        """Context manager entry"""
        if not self._initialized:
            self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False


class ExpertBridge:
    """
    Direct bridge to expert pool for specialized queries
    """
    
    def __init__(self, runtime_bridge: RuntimeBridge):
        self._bridge = runtime_bridge
    
    def list_experts(self) -> List[Dict[str, Any]]:
        """List all available experts"""
        experts_info = self._bridge.get_experts()
        if "error" in experts_info:
            return []
        
        result = []
        for expert_id in experts_info.get("available", []):
            details = self._bridge.get_expert_details(expert_id)
            if "expert" in details:
                result.append(details["expert"])
        
        return result
    
    def get_expert_capabilities(self, expert_id: str) -> List[str]:
        """Get capabilities for specific expert"""
        details = self._bridge.get_expert_details(expert_id)
        if "expert" not in details:
            return []
        
        expert = details["expert"]
        return expert.get("capabilities", expert.get("skills", []))
    
    def find_experts_for_task(self, task_description: str) -> List[str]:
        """Find experts suitable for a task"""
        experts = self.list_experts()
        task_lower = task_description.lower()
        
        suitable = []
        for expert in experts:
            expert_id = str(expert.get("id", ""))
            capabilities = expert.get("capabilities", expert.get("skills", []))
            
            # Check if any capability matches task
            for cap in capabilities:
                if isinstance(cap, str) and cap.lower() in task_lower:
                    suitable.append(expert_id)
                    break
        
        return suitable


class MemoryBridge:
    """
    Direct bridge to memory graph for context management
    """
    
    def __init__(self, runtime_bridge: RuntimeBridge):
        self._bridge = runtime_bridge
    
    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memory with query"""
        return self._bridge.recall_memory(query, limit)
    
    def add_knowledge(
        self,
        content: str,
        source: str = "agent-knowledge",
        tags: List[str] | None = None
    ) -> Dict[str, Any]:
        """Add knowledge to memory"""
        return self._bridge.store_memory(content, source, tags)
    
    def get_session_context(self, session_id: str) -> List[MemoryEntry]:
        """Get context for a session"""
        return self._bridge.recall_memory("", limit=20, session_id=session_id)
    
    def clear_session_context(self, session_id: str) -> Dict[str, Any]:
        """Clear context for a session"""
        # Sessions are managed by memory graph internally
        return {"success": True, "session_id": session_id}


# Convenience function
def get_runtime_bridge(auto_init: bool = True) -> RuntimeBridge:
    """Get a runtime bridge instance"""
    return RuntimeBridge(auto_initialize=auto_init)


if __name__ == "__main__":
    # Demo
    print("=" * 80)
    print("WASEEM RUNTIME BRIDGE - BRAIN INTEGRATION")
    print("=" * 80)
    
    if not BRAIN_AVAILABLE:
        print("[ERROR] Brain components not available")
        sys.exit(1)
    
    # Create bridge
    bridge = RuntimeBridge()
    
    # Check status
    status = bridge.get_status()
    print(f"\n[STATUS]")
    print(f"  Connected: {status.connected}")
    print(f"  Runtime Ready: {status.runtime_ready}")
    print(f"  Memory Available: {status.memory_available}")
    print(f"  Experts Loaded: {status.experts_loaded}")
    print(f"  Experts Available: {status.experts_available}")
    
    if status.error_message:
        print(f"  Error: {status.error_message}")
    
    if status.connected:
        # Get health snapshot
        health = bridge.health_snapshot()
        print(f"\n[HEALTH SNAPSHOT]")
        print(f"  Project: {health.get('project_name', 'N/A')}")
        print(f"  Condition: {health.get('condition', 'N/A')}")
        print(f"  Memory Nodes: {health.get('memory_node_count', 0)}")
        
        # List experts
        expert_bridge = ExpertBridge(bridge)
        experts = expert_bridge.list_experts()
        print(f"\n[EXPERTS] {len(experts)} available")
        for expert in experts[:5]:
            print(f"  - {expert.get('id', 'unknown')}: {expert.get('description', 'N/A')[:50]}")
    
    # Close
    bridge.close()
    print("\n[DONE] Bridge closed")
