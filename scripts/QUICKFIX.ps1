# Waseem Brain Quick Fix & Verification Script
# Run this after setting up Python to ensure everything is working

param(
    [switch]$Install = $false,
    [switch]$SkipTest = $false
)

$ErrorActionPreference = "Stop"
$WarningPreference = "SilentlyContinue"

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Waseem Brain: Quick Fix & Verification                      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Change to project directory
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

# 1. Check Python
Write-Host "1️⃣  Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -like "*3.11*") {
        Write-Host "   ✓ Python 3.11 found: $pythonVersion" -ForegroundColor Green
    } elseif ($pythonVersion -like "*3.1*") {
        Write-Host "   ⚠ Python version is $pythonVersion (3.11 recommended)" -ForegroundColor Yellow
    } else {
        Write-Host "   ✗ Python not found or wrong version" -ForegroundColor Red
        Write-Host "   👉 Install Python 3.11 from https://python.org" -ForegroundColor Cyan
        exit 1
    }
} catch {
    Write-Host "   ✗ Python not found in PATH" -ForegroundColor Red
    Write-Host "   👉 Install Python 3.11 and add to PATH" -ForegroundColor Cyan
    exit 1
}

# 2. Check pip
Write-Host ""
Write-Host "2️⃣  Checking pip..." -ForegroundColor Yellow
try {
    $pipVersion = python -m pip --version 2>&1
    Write-Host "   ✓ pip available: $($pipVersion.Split()[1])" -ForegroundColor Green
} catch {
    Write-Host "   ✗ pip not available" -ForegroundColor Red
    exit 1
}

# 3. Check Node.js
Write-Host ""
Write-Host "3️⃣  Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    if ([int]$nodeVersion.TrimStart('v').Split('.')[0] -ge 20) {
        Write-Host "   ✓ Node.js $nodeVersion found" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ Node.js $nodeVersion found (20+ recommended)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠ Node.js not found (needed for TypeScript interface)" -ForegroundColor Yellow
}

# 4. Check pnpm
Write-Host ""
Write-Host "4️⃣  Checking pnpm..." -ForegroundColor Yellow
try {
    $pnpmVersion = pnpm --version 2>&1
    Write-Host "   ✓ pnpm $pnpmVersion found" -ForegroundColor Green
} catch {
    Write-Host "   ✗ pnpm not found" -ForegroundColor Red
    Write-Host "   👉 Install with: npm install -g pnpm" -ForegroundColor Cyan
    exit 1
}

# 5. Check git
Write-Host ""
Write-Host "5️⃣  Checking git..." -ForegroundColor Yellow
try {
    $gitVersion = git --version 2>&1
    Write-Host "   ✓ git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "   ⚠ git not in PATH (optional)" -ForegroundColor Yellow
}

# 6. Install Python dependencies if requested
if ($Install) {
    Write-Host ""
    Write-Host "6️⃣  Installing Python dependencies..." -ForegroundColor Yellow
    
    Write-Host "   Installing runtime requirements..." -ForegroundColor Cyan
    python -m pip install -r requirements-runtime.txt -q
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Runtime requirements installed" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Failed to install runtime requirements" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "   Installing dev requirements..." -ForegroundColor Cyan
    python -m pip install -r requirements-dev.txt -q
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Dev requirements installed" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Failed to install dev requirements" -ForegroundColor Red
        exit 1
    }
}

# 7. Check key Python imports
Write-Host ""
Write-Host "7️⃣  Checking Python modules..." -ForegroundColor Yellow

$modules = @("onnxruntime", "hnswlib", "faster_whisper", "vaderSentiment")
foreach ($module in $modules) {
    try {
        $output = python -c "import $($module.Replace('-', '_')); print('ok')" 2>&1
        if ($output -contains "ok") {
            Write-Host "   ✓ $module installed" -ForegroundColor Green
        } else {
            Write-Host "   ⚠ $module might have issues" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "   ✗ $module not installed (run with -Install flag)" -ForegroundColor Yellow
    }
}

# 8. Check pnpm dependencies
Write-Host ""
Write-Host "8️⃣  Checking Node dependencies..." -ForegroundColor Yellow
if (Test-Path "node_modules/.pnpm") {
    Write-Host "   ✓ Node modules installed" -ForegroundColor Green
} else {
    Write-Host "   ⚠ Node modules not installed yet" -ForegroundColor Yellow
    Write-Host "   Run: pnpm install" -ForegroundColor Cyan
}

# 9. Check project structure
Write-Host ""
Write-Host "9️⃣  Checking project structure..." -ForegroundColor Yellow
$dirs = @("brain", "interface/src", "scripts", "data", "experts")
foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        Write-Host "   ✓ $dir exists" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $dir missing!" -ForegroundColor Red
    }
}

# 10. Git status
Write-Host ""
Write-Host "🔟 Checking git status..." -ForegroundColor Yellow
try {
    $gitStatus = git status --short 2>&1 | Measure-Object -Line
    $lastCommit = git log --oneline -1 2>&1
    Write-Host "   ✓ Git repository found" -ForegroundColor Green
    Write-Host "   Last commit: $lastCommit" -ForegroundColor Gray
    Write-Host "   Uncommitted changes: $($gitStatus.Lines)" -ForegroundColor Gray
} catch {
    Write-Host "   ⚠ Not a git repository" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✓ VERIFICATION COMPLETE" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host ""
if (!(Test-Path "node_modules/.pnpm")) {
    Write-Host "  1. Install Node dependencies:"
    Write-Host "     pnpm install"
    Write-Host ""
}

$modules = @("onnxruntime", "hnswlib")
$missing = $false
foreach ($module in $modules) {
    try {
        $output = python -c "import $($module.Replace('-', '_')); print('ok')" 2>&1
    } catch {
        $missing = $true
    }
}

if ($missing) {
    Write-Host "  2. Install Python dependencies:"
    Write-Host "     python -m pip install -r requirements-runtime.txt"
    Write-Host "     python -m pip install -r requirements-dev.txt"
    Write-Host ""
}

Write-Host "  3. Run diagnostics:"
Write-Host "     python scripts/diagnose_backends.py"
Write-Host ""
Write-Host "  4. Prepare runtime (download models):"
Write-Host "     run.bat prepare"
Write-Host ""
Write-Host "  5. Try interactive chat:"
Write-Host "     run.bat chat"
Write-Host ""
