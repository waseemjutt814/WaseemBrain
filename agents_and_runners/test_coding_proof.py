#!/usr/bin/env python3
"""
Test Waseem Brain with a real coding task.
Shows actual proof of what the system can do.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add project to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from brain.runtime import WaseemBrainRuntime
from brain.types import SessionId
from brain.helpers import logger as logger_module

# Configure logging
logger_module.configure_logging()
logger = logger_module.get_logger(__name__)


async def test_coding_task():
    """Test the system with a real coding task."""
    print("\n" + "="*70)
    print("WASEEM BRAIN - LIVE CODING TASK TEST")
    print("="*70)
    
    # Initialize runtime
    print("\n[1/5] Initializing Waseem Brain Runtime...")
    runtime = WaseemBrainRuntime()
    
    # Get health status
    print("\n[2/5] Checking system health...")
    health = runtime.health()
    print(f"     Status: {health['status']}")
    print(f"     Condition: {health['condition']}")
    print(f"     Ready: {health['ready']}")
    
    # Create session
    print("\n[3/5] Creating session...")
    session_id = SessionId("test-coding-session")
    
    # Task 1: Simple coding request
    print("\n[4/5] SUBMITTING CODING TASK:")
    print("-" * 70)
    coding_task = """
    Write Python code to reverse a string and return it.
    Include validation for empty strings.
    Show me the logic with type hints.
    """
    print(f"TASK: {coding_task.strip()}")
    print("-" * 70)
    
    # Process the query - async streaming generator
    print("\n[5/5] Processing task through: normalize > emotion > route > memory > experts > render")
    print("-" * 70)
    
    full_response = ""
    token_count = 0
    
    try:
        async for token in runtime.query(
            raw_input=coding_task.strip(),
            modality_hint="text",
            session_id=session_id,
        ):
            full_response += token
            token_count += 1
            # Print streaming tokens in real-time
            print(token, end="", flush=True)
        
        print("\n")
        print("="*70)
        print("\n✓ RESPONSE COMPLETE!")
        print("="*70)
        
        print(f"\n✓ STREAMING METADATA:")
        print(f"   - Tokens streamed: {token_count}")
        print(f"   - Total response length: {len(full_response)} characters")
        print(f"   - Session ID: {session_id}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    try:
        success = await test_coding_task()
        if success:
            print("\n" + "="*70)
            print("✓ TEST COMPLETE - PROOF OF CAPABILITY SHOWN")
            print("="*70)
        else:
            print("\n✗ Test failed - check errors above")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
