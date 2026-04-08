"""Testing utilities and fixtures."""

import json
from dataclasses import dataclass
from typing import Any, Optional

from ..types import MemoryNode, SessionId


@dataclass
class MockQuery:
    """Mock query for testing."""
    
    text: str
    modality: str = "text"
    session_id: Optional[SessionId] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "modality": self.modality,
            "session_id": self.session_id,
        }


@dataclass
class MockResponse:
    """Mock response for testing."""
    
    text: str
    confidence: float = 0.8
    mode: str = "answer"
    expert: str = "test-expert"
    citations: list[str] = None
    
    def __post_init__(self) -> None:
        if self.citations is None:
            self.citations = []
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "mode": self.mode,
            "expert": self.expert,
            "citations": self.citations,
        }


def create_test_memory_node(
    content: str,
    node_id: str = "test-node",
    source: str = "test",
    confidence: float = 0.8,
) -> MemoryNode:
    """Create a test memory node.
    
    Args:
        content: Node content
        node_id: Node ID
        source: Source identifier
        confidence: Confidence score
        
    Returns:
        Test memory node
    """
    import time
    from ..memory.embedder import MemoryEmbedder
    
    embedder = MemoryEmbedder()
    now = time.time()
    
    return MemoryNode(
        id=node_id,  # type: ignore[typeddict-unknown-key]
        content=content,
        embedding=embedder.embed(content),
        tags=[],
        source=source,
        source_type="memory",  # type: ignore[typeddict-unknown-key]
        created_at=now,
        last_accessed=now,
        access_count=1,
        confidence=confidence,
        session_id=None,  # type: ignore[typeddict-unknown-key]
        provenance=[],
    )


def assert_valid_response(response: dict[str, Any]) -> None:
    """Assert that a response has required fields.
    
    Args:
        response: Response dict to validate
        
    Raises:
        AssertionError: If response is invalid
    """
    required_fields = ["text", "confidence", "mode"]
    for field in required_fields:
        assert field in response, f"Missing required field: {field}"
    
    assert isinstance(response["text"], str), "text must be string"
    assert isinstance(response["confidence"], (int, float)), "confidence must be number"
    assert 0.0 <= response["confidence"] <= 1.0, "confidence must be 0.0-1.0"


def assert_valid_trace(trace: dict[str, Any]) -> None:
    """Assert that a trace has required fields.
    
    Args:
        trace: Trace dict to validate
        
    Raises:
        AssertionError: If trace is invalid
    """
    required_fields = ["query", "response", "expert", "mode"]
    for field in required_fields:
        assert field in trace, f"Missing required field in trace: {field}"
    
    assert isinstance(trace["query"], str), "query must be string"
    assert isinstance(trace["response"], str), "response must be string"


class TestRegistry:
    """Registry for test fixtures and utilities."""
    
    def __init__(self) -> None:
        self._fixtures: dict[str, Any] = {}
    
    def register_fixture(self, name: str, factory: Any) -> None:
        """Register a fixture factory.
        
        Args:
            name: Fixture name
            factory: Callable that creates the fixture
        """
        self._fixtures[name] = factory
    
    def get_fixture(self, name: str) -> Any:
        """Get a fixture.
        
        Args:
            name: Fixture name
            
        Returns:
            Fixture value
            
        Raises:
            KeyError: If fixture not found
        """
        if name not in self._fixtures:
            raise KeyError(f"Fixture not found: {name}")
        
        factory = self._fixtures[name]
        return factory() if callable(factory) else factory
    
    def list_fixtures(self) -> list[str]:
        """List all registered fixtures.
        
        Returns:
            List of fixture names
        """
        return list(self._fixtures.keys())


# Global test registry
_registry = TestRegistry()


def register_fixture(name: str, factory: Any) -> None:
    """Register a test fixture globally.
    
    Usage:
        @register_fixture("test_query")
        def create_test_query():
            return MockQuery("test")
    """
    _registry.register_fixture(name, factory)


def get_fixture(name: str) -> Any:
    """Get a registered fixture.
    
    Args:
        name: Fixture name
        
    Returns:
        Fixture value
    """
    return _registry.get_fixture(name)


class MockBrainRuntime:
    """Mock Brain runtime for testing."""
    
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.responses: list[str] = []
        self.last_confidence: float = 0.8
    
    def query(self, text: str) -> dict[str, Any]:
        """Mock query execution.
        
        Args:
            text: Query text
            
        Returns:
            Mock response
        """
        self.queries.append(text)
        response = f"Response to: {text}"
        self.responses.append(response)
        
        return {
            "text": response,
            "confidence": self.last_confidence,
            "mode": "answer",
            "expert": "mock",
            "citations": [],
        }
    
    def reset(self) -> None:
        """Reset mock state."""
        self.queries.clear()
        self.responses.clear()


def create_mock_runtime() -> MockBrainRuntime:
    """Create a mock Brain runtime.
    
    Returns:
        Mock runtime instance
    """
    return MockBrainRuntime()
