# Waseem Brain: Complete Setup Guide

**Status:** Fresh clone - needs environment setup  
**OS:** Windows (PowerShell)  
**Date:** April 5, 2026

---

## ✅ Requirements Checklist

### Required (Must Install)

- [ ] **Python 3.11** - Core runtime engine
  - Download: https://www.python.org/downloads/release/python-3110/
  - **Important:** Check "Add Python to PATH" during installation
  - Verify: `python --version` → should show `3.11.x`

- [ ] **Node.js 20+** - TypeScript interface
  - Status: ✅ Already installed (v24.14.1)
  - Already working

- [ ] **pnpm** - Node package manager
  - Status: ✅ Already installed
  - Already working

### Optional (For Advanced Features)

- [ ] **Rust 1.70+** - Router daemon (optional, not required)
  - Download: https://rustup.rs/
  - Only needed if you want: `run.bat router-start`
  - Can skip initially

---

## 🚀 Step-by-Step Setup

### Step 1: Install Python 3.11 (if not already installed)

**Download:**
```
https://www.python.org/downloads/release/python-3110/
```

**During Installation:**
- ✅ Check "Add Python to PATH"
- ✅ Check "Install pip"
- Uncheck "Install test suite" (not needed)

**Verify Installation:**
```powershell
python --version
# Should output: Python 3.11.x
```

If you get "Python was not found" → Python not in PATH yet. Restart PowerShell after installation.

---

### Step 2: Install Python Dependencies

```powershell
cd "d:\latest brain"

# Install runtime dependencies
python -m pip install -r requirements-runtime.txt -r requirements-dev.txt

# Install training dependencies (optional but recommended)
python -m pip install -r requirements-training.txt

# Verify installations
python -c "import onnxruntime; print('✓ ONNX Runtime OK')"
python -c "import hnswlib; print('✓ HNSW OK')"
python -c "import faster_whisper; print('✓ Whisper OK')"
```

**Expected time:** 5-10 minutes  
**Disk space needed:** ~1.5 GB for dependencies

---

### Step 3: Install Node.js Dependencies

```powershell
cd "d:\latest brain"

# Install TypeScript interface dependencies
pnpm install

# Build TypeScript
pnpm run build

# Verify
pnpm test
```

**Expected:** Tests should pass  
**Time:** 2-3 minutes

---

### Step 4: Verify Everything Works

```powershell
# Run diagnostics (will auto-download ML models)
python scripts/diagnose_backends.py

# Output should look like:
# ✓ Python 3.11 OK
# ✓ ONNX Runtime OK  
# ✓ HNSW Vector DB OK
# ✓ Faster Whisper OK
# ✓ SQLite OK
# ✓ All backends ready
```

---

### Step 5: Prepare Runtime (One-Time Warmup)

```powershell
# This will:
# - Download ML models to cache (~2GB)
# - Build knowledge store
# - Run smoke test query
# - Takes 5-10 minutes first time

run.bat prepare
```

**What happens:**
- Models cached to `data/` folder
- Knowledge cards loaded to SQLite
- Simple "What is the capital of France?" test query

**Expected output:**
```
[INFO] Warming runtime...
[INFO] Knowledge store loaded: 53 cards
[INFO] Smoke test: "Capital of France?"
[RESPONSE] Paris (from memory)
[INFO] Runtime ready!
```

---

## ✅ Verify Installation Complete

Once setup is done, verify with:

```powershell
# Check Python
python --version          # Should be 3.11.x

# Check pnpm  
pnpm --version            # Should be modern version

# Check Node
node --version            # Should be 20+

# Test basic query
python scripts/chat_cli.py --once "hello"
# Should respond with greeting

# Test build
run.bat build             # Should succeed with no errors

# Test all tests
run.bat test              # Python + TypeScript + Rust tests
```

---

## 🐛 Common Issues & Fixes

### Issue: "Python was not found"

**Cause:** Python not installed or not in PATH  
**Fix:**
```powershell
# Option 1: Re-run Python installer with "Add to PATH" checked
# Then restart PowerShell

# Option 2: Manually add Python to PATH
$pythonPath = "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311"
$env:PATH += ";$pythonPath"

# Verify
python --version
```

### Issue: "Missing module: onnxruntime"

**Cause:** Dependencies not installed  
**Fix:**
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-runtime.txt
```

### Issue: "pnpm not found"

**Cause:** pnpm not in PATH  
**Fix:**
```powershell
npm install -g pnpm
# Restart PowerShell
```

### Issue: "Runtime cold start takes 5+ seconds"

**Cause:** First query downloads ML models  
**Expected:** Normal behavior

**Speed up:** Use hot daemon
```powershell
run.bat runtime-start
# Then reuse in CLI:
python scripts/chat_cli.py --once "hello"
```

---

## 📚 Next Steps After Setup

### Run Interactive Chat
```powershell
run.bat chat
```

**Commands:**
- `/health` - Check system status
- `/experts` - List available experts
- `/recall <text>` - Search memory
- `/status` - Show detailed metrics
- `/quit` - Exit

### Run Development Server
```powershell
run.bat dev
```

Opens Fastify server on `http://localhost:3000`

### Run Full Test Suite
```powershell
run.bat test
```

Expected: All tests pass

---

## 🔧 Useful Commands Reference

```powershell
# Runtime Commands
run.bat prepare              # One-time setup
run.bat chat                 # Interactive CLI
run.bat dev                  # Dev server
run.bat bench                # Performance test
run.bat doctor               # Diagnostics

# Daemon Management
run.bat runtime-start        # Start Python daemon
run.bat runtime-status       # Check daemon
run.bat runtime-stop         # Stop daemon

# Router Daemon (optional)
run.bat router-start         # Start Rust router
run.bat router-status        
run.bat router-stop

# Build & Test
run.bat build                # Build TypeScript
run.bat test                 # Run all tests

# Knowledge Management
run.bat knowledge            # Build knowledge packs
run.bat assets               # Download models + knowledge
```

---

## 📊 System Requirements

### Minimum
- **RAM:** 4 GB
- **Disk:** 5 GB (models + caches)
- **CPU:** Any modern multi-core processor

### Recommended
- **RAM:** 8 GB
- **Disk:** 10 GB (gives breathing room)
- **CPU:** Intel i7 / AMD Ryzen 5+

### Voice Support (Optional)
- **RAM:** Extra 2 GB when using voice input
- **Disk:** Extra 2 GB for voice models

---

## 🎯 Troubleshooting Checklist

- [ ] Python 3.11 installed and in PATH
- [ ] Python dependencies installed: `pip list | grep -i onnx`
- [ ] Node packages installed: `pnpm list --depth=0`
- [ ] No git errors: `git status`
- [ ] Diagnostics pass: `python scripts/diagnose_backends.py`
- [ ] Preparation complete: `run.bat prepare`

---

## 📞 I'm Stuck!

If issues persist, run this diagnostic:

```powershell
cd "d:\latest brain"

# Comprehensive diagnostic
Write-Host "=== Python ==="
python --version
python -c "import sys; print(sys.path)"

Write-Host "=== pnpm ==="
pnpm --version
pnpm list --depth=0

Write-Host "=== Node ==="
node --version
npm --version

Write-Host "=== Git ==="
git status
git log --oneline | head -1

# Save output and share with the team
```

---

**Ready to go?** Start with: `run.bat prepare` 🚀
