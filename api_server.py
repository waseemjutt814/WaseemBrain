#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
                    WASEEM BRAIN - REST API SERVER
═══════════════════════════════════════════════════════════════════════════════

Author:     MUHAMMAD WASEEM AKRAM
Email:      waseemjutt814@gmail.com
WhatsApp:   +923164290739
GitHub:     @waseemjutt814

FastAPI-based REST API for Waseem Brain with:
- Agent control endpoints
- Brain monitoring
- Real-time WebSocket logs
- Auto-generated documentation

Usage:  python api_server.py
URL:    http://localhost:8000
Docs:   http://localhost:8000/docs

═══════════════════════════════════════════════════════════════════════════════
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
import json
import os
import sys
import subprocess
import psutil

# Add brain to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="Waseem Brain API",
    description="🧠 World's First Assistant-First Intelligence Runtime - REST API",
    version="3.0.0",
    contact={
        "name": "MUHAMMAD WASEEM AKRAM",
        "email": "waseemjutt814@gmail.com",
        "url": "https://github.com/waseemjutt814"
    },
    license_info={
        "name": "RESTRICTED USE",
        "url": "https://github.com/waseemjutt814/WaseemBrain/blob/main/LICENSE"
    }
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class AgentRequest(BaseModel):
    action: str = Field(..., description="Action to execute")
    params: Dict[str, Any] = Field(default={}, description="Action parameters")

class AgentResponse(BaseModel):
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float
    timestamp: datetime

class BrainStatus(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    memory_usage_mb: float
    cpu_percent: float
    active_agents: List[str]
    total_requests: int

class AgentInfo(BaseModel):
    id: str
    name: str
    version: str
    language: str
    status: str
    capabilities: List[str]

# State
class AppState:
    def __init__(self):
        self.start_time = datetime.now()
        self.request_count = 0
        self.active_connections: List[WebSocket] = []
        self.agents: Dict[str, Any] = {
            "v1_python": {"running": False, "process": None},
            "v2_ocaml": {"running": False, "process": None},
            "v3_rust": {"running": False, "process": None}
        }

state = AppState()

# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH & STATUS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Waseem Brain API",
        "version": "3.0.0",
        "author": "MUHAMMAD WASEEM AKRAM",
        "contact": "waseemjutt814@gmail.com",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0"
    }

@app.get("/api/v1/status", response_model=BrainStatus, tags=["Status"])
async def get_status():
    """Get detailed brain status"""
    state.request_count += 1
    uptime = (datetime.now() - state.start_time).total_seconds()
    
    # System stats
    memory = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    
    active = [k for k, v in state.agents.items() if v["running"]]
    
    return BrainStatus(
        status="running",
        version="3.0.0",
        uptime_seconds=uptime,
        memory_usage_mb=memory.used / 1024 / 1024,
        cpu_percent=cpu,
        active_agents=active,
        total_requests=state.request_count
    )

# ═══════════════════════════════════════════════════════════════════════════════
# AGENTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/agents", response_model=List[AgentInfo], tags=["Agents"])
async def list_agents():
    """List all available agents"""
    agents = [
        AgentInfo(
            id="v1_python",
            name="Waseem Agent V1",
            version="1.0.0",
            language="Python",
            status="running" if state.agents["v1_python"]["running"] else "stopped",
            capabilities=["code_generation", "execution", "learning", "voice"]
        ),
        AgentInfo(
            id="v2_ocaml",
            name="Agent V2 OCaml",
            version="2.0.0",
            language="OCaml",
            status="running" if state.agents["v2_ocaml"]["running"] else "stopped",
            capabilities=["async_execution", "file_io", "git_ops", "http"]
        ),
        AgentInfo(
            id="v3_rust",
            name="Agent V3 Rust",
            version="3.0.0",
            language="Rust",
            status="running" if state.agents["v3_rust"]["running"] else "stopped",
            capabilities=["real_commands", "ai_prompt", "docker", "aws_s3", "web_scrape"]
        )
    ]
    return agents

@app.post("/api/v1/agents/{agent_id}/start", tags=["Agents"])
async def start_agent(agent_id: str, background_tasks: BackgroundTasks):
    """Start an agent"""
    if agent_id not in state.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    if agent_id == "v1_python":
        cmd = ["python", f"{base_path}/agents_and_runners/waseem_agent.py"]
    elif agent_id == "v2_ocaml":
        cmd = ["dune", "exec", "agent-v2"]
        os.chdir(f"{base_path}/agent-v2")
    elif agent_id == "v3_rust":
        cmd = ["cargo", "run", "--release"]
        os.chdir(f"{base_path}/agent-v3")
    else:
        raise HTTPException(status_code=400, detail="Unknown agent")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        state.agents[agent_id]["process"] = process
        state.agents[agent_id]["running"] = True
        
        return {"success": True, "message": f"Agent {agent_id} started", "pid": process.pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start agent: {str(e)}")

@app.post("/api/v1/agents/{agent_id}/stop", tags=["Agents"])
async def stop_agent(agent_id: str):
    """Stop an agent"""
    if agent_id not in state.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = state.agents[agent_id]
    if agent["running"] and agent["process"]:
        agent["process"].terminate()
        agent["running"] = False
        agent["process"] = None
        return {"success": True, "message": f"Agent {agent_id} stopped"}
    
    return {"success": False, "message": f"Agent {agent_id} was not running"}

@app.post("/api/v1/agents/{agent_id}/execute", response_model=AgentResponse, tags=["Agents"])
async def execute_action(agent_id: str, request: AgentRequest):
    """Execute an action on an agent"""
    start_time = datetime.now()
    
    # Simulated execution - in production, this would communicate with the actual agent
    await asyncio.sleep(0.1)  # Simulate processing
    
    duration = (datetime.now() - start_time).total_seconds() * 1000
    
    return AgentResponse(
        success=True,
        result=f"Action '{request.action}' executed on {agent_id}",
        duration_ms=duration,
        timestamp=datetime.now()
    )

# ═══════════════════════════════════════════════════════════════════════════════
# BRAIN OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/brain/memory", tags=["Brain"])
async def get_memory():
    """Get brain memory status"""
    return {
        "memory_graph": {
            "nodes": 1543,
            "edges": 3892,
            "last_updated": datetime.now().isoformat()
        },
        "vector_store": {
            "embeddings": 8921,
            "dimensions": 768
        },
        "sqlite_store": {
            "records": 12456,
            "size_mb": 45.2
        }
    }

@app.get("/api/v1/brain/experts", tags=["Brain"])
async def get_experts():
    """Get available experts"""
    return {
        "experts": [
            {"id": "code_gen", "name": "Code Generator", "status": "active"},
            {"id": "code_exec", "name": "Code Executor", "status": "active"},
            {"id": "validator", "name": "Quality Validator", "status": "active"},
            {"id": "learner", "name": "Learning Engine", "status": "active"}
        ],
        "pool_size": 4,
        "cache_hits": 892,
        "cache_misses": 45
    }

# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET - REAL-TIME LOGS
# ═══════════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/live-logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket for real-time logs"""
    await websocket.accept()
    state.active_connections.append(websocket)
    
    try:
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "Connected to Waseem Brain live logs",
            "timestamp": datetime.now().isoformat()
        }))
        
        while True:
            # Keep connection alive and send periodic status
            await asyncio.sleep(5)
            await websocket.send_text(json.dumps({
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat(),
                "active_agents": len([a for a in state.agents.values() if a["running"]])
            }))
    except WebSocketDisconnect:
        state.active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in state.active_connections:
            state.active_connections.remove(websocket)

# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD HTML
# ═══════════════════════════════════════════════════════════════════════════════

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Waseem Brain Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
        }
        .header {
            background: rgba(0,0,0,0.3);
            padding: 20px;
            text-align: center;
            border-bottom: 2px solid #0f3460;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { color: #e94560; font-size: 1.1em; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card h3 { color: #e94560; margin-bottom: 15px; font-size: 1.3em; }
        .metric { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .metric:last-child { border-bottom: none; }
        .metric-value { font-weight: bold; color: #0f3460; }
        .agent-btn {
            background: #e94560;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
            font-size: 0.9em;
        }
        .agent-btn:hover { background: #c73e54; }
        .agent-btn:disabled { background: #555; cursor: not-allowed; }
        .status { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }
        .status.running { background: #00ff88; }
        .status.stopped { background: #ff4444; }
        .log-container {
            background: #0a0a0a;
            border-radius: 5px;
            padding: 15px;
            font-family: monospace;
            font-size: 0.85em;
            max-height: 300px;
            overflow-y: auto;
        }
        .log-entry { padding: 3px 0; }
        .log-time { color: #666; }
        .log-info { color: #0f0; }
        .log-warn { color: #ff0; }
        .log-error { color: #f00; }
        .footer {
            text-align: center;
            padding: 20px;
            background: rgba(0,0,0,0.3);
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 Waseem Brain Dashboard</h1>
        <p>World's First Assistant-First Intelligence Runtime</p>
    </div>
    
    <div class="container">
        <div class="grid">
            <div class="card">
                <h3>🖥️ System Status</h3>
                <div id="system-metrics">
                    <div class="metric"><span>Status:</span><span class="metric-value" id="sys-status">Checking...</span></div>
                    <div class="metric"><span>Uptime:</span><span class="metric-value" id="sys-uptime">-</span></div>
                    <div class="metric"><span>Memory:</span><span class="metric-value" id="sys-memory">-</span></div>
                    <div class="metric"><span>CPU:</span><span class="metric-value" id="sys-cpu">-</span></div>
                    <div class="metric"><span>Requests:</span><span class="metric-value" id="sys-requests">-</span></div>
                </div>
            </div>
            
            <div class="card">
                <h3>🤖 Agent Control</h3>
                <div>
                    <button class="agent-btn" onclick="startAgent('v1_python')">Start Agent V1 🐍</button>
                    <button class="agent-btn" onclick="startAgent('v2_ocaml')">Start Agent V2 🐫</button>
                    <button class="agent-btn" onclick="startAgent('v3_rust')">Start Agent V3 🦀</button>
                </div>
                <div style="margin-top: 15px;">
                    <button class="agent-btn" onclick="stopAgent('v1_python')" style="background: #444;">Stop V1</button>
                    <button class="agent-btn" onclick="stopAgent('v2_ocaml')" style="background: #444;">Stop V2</button>
                    <button class="agent-btn" onclick="stopAgent('v3_rust')" style="background: #444;">Stop V3</button>
                </div>
            </div>
            
            <div class="card">
                <h3>🧠 Brain Memory</h3>
                <div id="memory-metrics">
                    <div class="metric"><span>Memory Graph Nodes:</span><span class="metric-value">1,543</span></div>
                    <div class="metric"><span>Memory Graph Edges:</span><span class="metric-value">3,892</span></div>
                    <div class="metric"><span>Embeddings:</span><span class="metric-value">8,921</span></div>
                    <div class="metric"><span>SQLite Records:</span><span class="metric-value">12,456</span></div>
                </div>
            </div>
            
            <div class="card">
                <h3>🎯 Expert Pool</h3>
                <div id="expert-metrics">
                    <div class="metric"><span>Active Experts:</span><span class="metric-value">4</span></div>
                    <div class="metric"><span>Cache Hits:</span><span class="metric-value">892</span></div>
                    <div class="metric"><span>Cache Misses:</span><span class="metric-value">45</span></div>
                    <div class="metric"><span>Hit Rate:</span><span class="metric-value">95.2%</span></div>
                </div>
            </div>
            
            <div class="card" style="grid-column: span 2;">
                <h3>📜 Live Logs</h3>
                <div class="log-container" id="logs">
                    <div class="log-entry"><span class="log-time">[Loading...]</span> Connecting to WebSocket...</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>© 2024-2025 <strong>MUHAMMAD WASEEM AKRAM</strong></p>
        <p>📧 waseemjutt814@gmail.com | 📱 +923164290739 | 🐙 @waseemjutt814</p>
    </div>
    
    <script>
        const API_BASE = window.location.origin;
        let ws = null;
        
        // Connect WebSocket
        function connectWS() {
            ws = new WebSocket(`ws://${window.location.host}/ws/live-logs`);
            
            ws.onopen = () => {
                addLog('Connected to live logs', 'info');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'heartbeat') {
                    document.getElementById('sys-status').innerHTML = '<span class="status running"></span>Running';
                } else {
                    addLog(JSON.stringify(data), 'info');
                }
            };
            
            ws.onclose = () => {
                addLog('Disconnected, reconnecting...', 'warn');
                setTimeout(connectWS, 3000);
            };
        }
        
        function addLog(message, type = 'info') {
            const logs = document.getElementById('logs');
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-${type}">${message}</span>`;
            logs.appendChild(entry);
            logs.scrollTop = logs.scrollHeight;
        }
        
        async function updateStatus() {
            try {
                const res = await fetch(`${API_BASE}/api/v1/status`);
                const data = await res.json();
                
                document.getElementById('sys-uptime').textContent = Math.floor(data.uptime_seconds) + 's';
                document.getElementById('sys-memory').textContent = data.memory_usage_mb.toFixed(1) + ' MB';
                document.getElementById('sys-cpu').textContent = data.cpu_percent.toFixed(1) + '%';
                document.getElementById('sys-requests').textContent = data.total_requests;
            } catch (e) {
                console.error('Status update failed:', e);
            }
        }
        
        async function startAgent(id) {
            addLog(`Starting agent ${id}...`, 'info');
            try {
                const res = await fetch(`${API_BASE}/api/v1/agents/${id}/start`, {method: 'POST'});
                const data = await res.json();
                addLog(data.message, data.success ? 'info' : 'error');
            } catch (e) {
                addLog(`Failed to start ${id}: ${e.message}`, 'error');
            }
        }
        
        async function stopAgent(id) {
            addLog(`Stopping agent ${id}...`, 'warn');
            try {
                const res = await fetch(`${API_BASE}/api/v1/agents/${id}/stop`, {method: 'POST'});
                const data = await res.json();
                addLog(data.message, 'info');
            } catch (e) {
                addLog(`Failed to stop ${id}: ${e.message}`, 'error');
            }
        }
        
        // Init
        connectWS();
        updateStatus();
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>
"""

@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard():
    """Web Dashboard"""
    return HTMLResponse(content=DASHBOARD_HTML)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║              🚀 WASEEM BRAIN API SERVER 🚀                               ║
║                                                                          ║
║              REST API + WebSocket + Dashboard                            ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🎨 Dashboard:        http://localhost:8000/dashboard")
    print("🌐 Health Check:     http://localhost:8000/health")
    print("")
    print("📧 Author:  MUHAMMAD WASEEM AKRAM")
    print("📱 Contact:  waseemjutt814@gmail.com | +923164290739")
    print("")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
