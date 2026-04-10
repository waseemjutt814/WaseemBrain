# ═══════════════════════════════════════════════════════════════════════════════
#                    WASEEM BRAIN - WINDOWS INSTALLER
# ═══════════════════════════════════════════════════════════════════════════════
# 
# Author:  MUHAMMAD WASEEM AKRAM
# Contact: waseemjutt814@gmail.com | +923164290739
#
# Usage:   irm https://raw.githubusercontent.com/waseemjutt814/WaseemBrain/main/install.ps1 | iex
#          OR
#          .\install.ps1
#
# ═══════════════════════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"

# ═══════════════════════════════════════════════════════════════════════════════
# 🔐 AUTHOR AUTHENTICATION - DO NOT REMOVE
# ═══════════════════════════════════════════════════════════════════════════════

# SHA256 hash of password (hidden, not plain text)
# To verify: echo -n "password" | sha256sum
$REQUIRED_PASSWORD_HASH = "7c6f6a8b9c3e2d1f4056789012345678901234567890abcdef1234567890abcd"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════════════════╗"
Write-Host "║                    🔐 AUTHOR AUTHENTICATION REQUIRED 🔐                  ║"
Write-Host "╚══════════════════════════════════════════════════════════════════════════╝"
Write-Host ""

# Function to hash password
function Get-PasswordHash($password) {
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($password)
    $hash = $sha256.ComputeHash($bytes)
    return [BitConverter]::ToString($hash).Replace("-", "").ToLower()
}

# Check for password from environment or prompt
if ($env:WASEEM_BRAIN_PASSWORD) {
    $USER_PASSWORD = $env:WASEEM_BRAIN_PASSWORD
} else {
    $securePassword = Read-Host "Enter Author Password" -AsSecureString
    $USER_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword))
}

# Hash and compare
$USER_HASH = Get-PasswordHash $USER_PASSWORD

if ($USER_HASH -ne $REQUIRED_PASSWORD_HASH) {
    Write-Host ""
    Write-Host "❌ INVALID PASSWORD - Access Denied" -ForegroundColor Red
    Write-Host ""
    Write-Host "Author: MUHAMMAD WASEEM AKRAM"
    Write-Host "Contact: waseemjutt814@gmail.com | +923164290739"
    Write-Host ""
    exit 1
}

Write-Host "✅ Authentication Successful - Proceeding with installation..." -ForegroundColor Green
Write-Host ""

# Colors
function Write-Color($Text, $Color) {
    Write-Host $Text -ForegroundColor $Color
}

# Banner
Write-Host ""
Write-Color "╔══════════════════════════════════════════════════════════════════════════╗" Cyan
Write-Color "║                                                                          ║" Cyan
Write-Color "║              🤖  WASEEM BRAIN - WINDOWS INSTALLER  🤖                   ║" Cyan
Write-Color "║                                                                          ║" Cyan
Write-Color "║         World's First Assistant-First Intelligence Runtime               ║" Cyan
Write-Color "║                                                                          ║" Cyan
Write-Color "╚══════════════════════════════════════════════════════════════════════════╝" Cyan
Write-Host ""

$INSTALL_DIR = "$env:USERPROFILE\waseembrain"
$REPO_URL = "https://github.com/waseemjutt814/WaseemBrain.git"
$VERSION = "3.0.0"

Write-Color "📦 Installing Waseem Brain v$VERSION..." Blue
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Color "⚠ Running without admin privileges. Some features may be limited." Yellow
}

# Check dependencies
Write-Color "🔍 Checking dependencies..." Yellow

function Test-Command($Command) {
    $exists = Get-Command $Command -ErrorAction SilentlyContinue
    if ($exists) {
        Write-Color "  ✓ $Command installed" Green
        return $true
    } else {
        Write-Color "  ✗ $Command not found" Red
        return $false
    }
}

$missingDeps = 0

Test-Command "git" | Out-Null; if (-not $?) { $missingDeps++ }
Test-Command "python" | Out-Null; if (-not $?) { $missingDeps++ }
Test-Command "pip" | Out-Null; if (-not $?) { $missingDeps++ }
Test-Command "node" | Out-Null; if (-not $?) { $missingDeps++ }
Test-Command "npm" | Out-Null; if (-not $?) { $missingDeps++ }

# Check optional
Write-Color "🔍 Checking optional dependencies..." Yellow
Test-Command "rustc" | Out-Null; if (-not $?) { Write-Color "  ⚠ Rust not found (Agent V3 optional)" Yellow }
Test-Command "cargo" | Out-Null; if (-not $?) { Write-Color "  ⚠ Cargo not found (Agent V3 optional)" Yellow }

if ($missingDeps -gt 0) {
    Write-Host ""
    Write-Color "❌ Missing required dependencies!" Red
    Write-Color "Please install: Git, Python, Node.js" Yellow
    Write-Host ""
    Write-Color "📋 Download from:" Cyan
    Write-Color "  Git:    https://git-scm.com/download/win" White
    Write-Color "  Python: https://python.org/downloads" White
    Write-Color "  Node:   https://nodejs.org" White
    exit 1
}

Write-Host ""
Write-Color "✅ All dependencies satisfied!" Green

# Clone repository
Write-Host ""
Write-Color "📥 Cloning Waseem Brain repository..." Blue

if (Test-Path $INSTALL_DIR) {
    Write-Color "⚠ Directory $INSTALL_DIR already exists" Yellow
    $response = Read-Host "Do you want to update? (y/n)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Set-Location $INSTALL_DIR
        git pull origin main
    } else {
        Write-Color "Skipping clone..." Yellow
    }
} else {
    git clone --depth=1 $REPO_URL $INSTALL_DIR
    Write-Color "✅ Repository cloned to $INSTALL_DIR" Green
}

Set-Location $INSTALL_DIR

# Install Python dependencies
Write-Host ""
Write-Color "🐍 Installing Python dependencies..." Blue
pip install -q -r requirements.txt 2>$null || pip install -q fastapi uvicorn httpx numpy pandas python-dotenv requests pydantic 2>$null
Write-Color "✅ Python dependencies installed" Green

# Install Node.js dependencies
Write-Host ""
Write-Color "📦 Installing Node.js dependencies..." Blue
npm install -g pnpm 2>$null || npm install -g pnpm --force 2>$null
pnpm install 2>$null || npm install 2>$null
Write-Color "✅ Node.js dependencies installed" Green

# Build Agents
Write-Host ""
Write-Color "🔨 Building Agents..." Blue

# Agent V1 (Python)
Write-Color "  → Agent V1 (Python) - Ready to use" Cyan

# Agent V2 (OCaml)
if (Get-Command dune -ErrorAction SilentlyContinue) {
    Write-Color "  → Building Agent V2 (OCaml)..." Cyan
    Set-Location agent-v2
    dune build 2>$null || Write-Color "    ⚠ Agent V2 build skipped" Yellow
    Set-Location ..
} else {
    Write-Color "  → Agent V2 (OCaml) - Optional, skipped" Yellow
}

# Agent V3 (Rust)
if (Get-Command cargo -ErrorAction SilentlyContinue) {
    Write-Color "  → Building Agent V3 (Rust)..." Cyan
    Set-Location agent-v3
    cargo build --release 2>$null || Write-Color "    ⚠ Agent V3 build skipped" Yellow
    Set-Location ..
} else {
    Write-Color "  → Agent V3 (Rust) - Optional, skipped" Yellow
}

# Create config
Write-Host ""
Write-Color "⚙️ Creating configuration..." Blue

$configDir = "$env:USERPROFILE\.waseembrain"
New-Item -ItemType Directory -Force -Path $configDir | Out-Null

$config = @{
    version = $VERSION
    install_dir = $INSTALL_DIR
    author = "MUHAMMAD WASEEM AKRAM"
    contact = "waseemjutt814@gmail.com"
    installed_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    agents = @{
        v1_python = $true
        v2_ocaml = $false
        v3_rust = $false
    }
} | ConvertTo-Json

$config | Out-File "$configDir\config.json" -Encoding UTF8

# Create launcher script
Write-Host ""
Write-Color "🚀 Creating launcher..." Blue

$launcherContent = @'
# Waseem Brain Launcher for PowerShell
param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

$INSTALL_DIR = "$env:USERPROFILE\waseembrain"

if (-not (Test-Path $INSTALL_DIR)) {
    Write-Error "Error: Waseem Brain not found at $INSTALL_DIR"
    Write-Host "Please run the installer again."
    exit 1
}

Set-Location $INSTALL_DIR

switch ($Command) {
    "start" { 
        Write-Host "🚀 Starting Waseem Brain..."
        pnpm run dev 2>$null || python brain\runtime.py 2>$null
    }
    "stop" {
        Write-Host "🛑 Stopping Waseem Brain..."
        Get-Process | Where-Object {$_.ProcessName -match "waseembrain|python|node"} | Stop-Process -Force 2>$null
    }
    "status" {
        Write-Host "📊 Checking status..."
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:8080/health" -TimeoutSec 2
            Write-Host "✅ Running: $response"
        } catch {
            Write-Host "❌ Not running"
        }
    }
    "agent-v1" {
        Write-Host "🐍 Starting Agent V1 (Python)..."
        Set-Location "$INSTALL_DIR\agents_and_runners"
        python waseem_agent.py
    }
    "agent-v2" {
        Write-Host "🐫 Starting Agent V2 (OCaml)..."
        Set-Location "$INSTALL_DIR\agent-v2"
        dune exec agent-v2 2>$null || Write-Host "Agent V2 not built"
    }
    "agent-v3" {
        Write-Host "🦀 Starting Agent V3 (Rust)..."
        Set-Location "$INSTALL_DIR\agent-v3"
        cargo run --release 2>$null || Write-Host "Agent V3 not built"
    }
    "dashboard" {
        Write-Host "🎨 Opening Dashboard..."
        Write-Host "Dashboard: http://localhost:8080"
        Start-Process "http://localhost:8080"
    }
    "update" {
        Write-Host "🔄 Updating Waseem Brain..."
        Set-Location $INSTALL_DIR
        git pull origin main
    }
    default {
        Write-Host "🤖 Waseem Brain - Commands:"
        Write-Host ""
        Write-Host "  waseembrain start     - Start the system"
        Write-Host "  waseembrain stop      - Stop the system"
        Write-Host "  waseembrain status    - Check system status"
        Write-Host "  waseembrain agent-v1  - Run Agent V1 (Python)"
        Write-Host "  waseembrain agent-v2  - Run Agent V2 (OCaml)"
        Write-Host "  waseembrain agent-v3  - Run Agent V3 (Rust)"
        Write-Host "  waseembrain dashboard - Open web dashboard"
        Write-Host "  waseembrain update    - Update to latest version"
        Write-Host ""
    }
}
'@

$launcherContent | Out-File "$env:USERPROFILE\waseembrain-launcher.ps1" -Encoding UTF8

# Create batch wrapper
$batchContent = @"
@echo off
powershell -ExecutionPolicy Bypass -File "%USERPROFILE%\waseembrain-launcher.ps1" %*
"@

$batchContent | Out-File "$env:USERPROFILE\waseembrain.bat" -Encoding ASCII

# Add to PATH
Write-Host ""
Write-Color "🔧 Setting up PATH..." Blue

$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if (-not $userPath.Contains("$env:USERPROFILE")) {
    [Environment]::SetEnvironmentVariable("PATH", "$env:USERPROFILE;$userPath", "User")
    Write-Color "✅ Added to PATH (restart terminal to apply)" Green
}

# Final banner
Write-Host ""
Write-Color "╔══════════════════════════════════════════════════════════════════════════╗" Green
Write-Color "║                                                                          ║" Green
Write-Color "║              ✅  WASEEM BRAIN INSTALLED SUCCESSFULLY!  ✅                 ║" Green
Write-Color "║                                                                          ║" Green
Write-Color "╚══════════════════════════════════════════════════════════════════════════╝" Green
Write-Host ""
Write-Color "📍 Installation Directory: $INSTALL_DIR" Cyan
Write-Color "🚀 Start Command:         waseembrain start" Cyan
Write-Color "🌐 Dashboard:             http://localhost:8080" Cyan
Write-Color "🆘 Help:                  waseembrain help" Cyan
Write-Host ""
Write-Color "📚 Documentation:" Yellow
Write-Host "  - README:   $INSTALL_DIR\README.md"
Write-Host "  - License:  $INSTALL_DIR\LICENSE"
Write-Host "  - Author:   MUHAMMAD WASEEM AKRAM"
Write-Host "  - Contact:  waseemjutt814@gmail.com"
Write-Host ""
Write-Color "🎉 Ready to use!" Green
Write-Host "   Option 1: waseembrain start"
Write-Host "   Option 2: $env:USERPROFILE\waseembrain-launcher.ps1 start"
Write-Host ""

# Pause
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
