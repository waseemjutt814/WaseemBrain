import os
import asyncio
from pathlib import Path
from brain.memory.graph import MemoryGraph
from brain.config import load_settings
from brain.types import SessionId

async def attach_project():
    """
    Project Attachment Service.
    Indexes the entire codebase into WaseemBrain's memory.
    """
    settings = load_settings()
    memory = MemoryGraph(settings)
    session_id = SessionId("project-indexing-alpha")
    
    # Files to index
    extensions = {".py", ".ts", ".rs", ".md", ".json", ".yaml", ".proto"}
    excluded = {".git", "node_modules", "target", "dist", "__pycache__", "data"}
    
    print(f"Indexing WaseemBrain codebase into memory...")
    
    count = 0
    for root, dirs, files in os.walk("."):
        # Filter excluded directories
        dirs[:] = [d for d in dirs if d not in excluded]
        
        for file in files:
            path = Path(root) / file
            if path.suffix.lower() in extensions:
                try:
                    content = path.read_text(encoding="utf-8")
                    if not content.strip():
                        continue
                        
                    # Store in memory graph
                    memory.store(
                        content=f"FILE: {path}\n\n{content[:5000]}",
                        source="project-indexing",
                        tags=["codebase", path.suffix[1:]],
                        session_id=session_id,
                        source_type="workspace"
                    )
                    count += 1
                except Exception:
                    pass
                    
    print(f"Indexing complete: {count} project documents attached to WaseemBrain.")
    memory.close()

if __name__ == "__main__":
    asyncio.run(attach_project())
