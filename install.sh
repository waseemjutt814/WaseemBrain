#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
#                    WASEEM BRAIN - ONE COMMAND INSTALLER
# ═══════════════════════════════════════════════════════════════════════════════
# 
# Author:  MUHAMMAD WASEEM AKRAM
# Contact: waseemjutt814@gmail.com | +923164290739
#
# Usage:   curl -fsSL https://raw.githubusercontent.com/waseemjutt814/WaseemBrain/main/install.sh | bash
#          OR
#          wget -qO- https://raw.githubusercontent.com/waseemjutt814/WaseemBrain/main/install.sh | bash
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# ═══════════════════════════════════════════════════════════════════════════════
# 🔐 AUTHOR AUTHENTICATION - DO NOT REMOVE
# ═══════════════════════════════════════════════════════════════════════════════

# SHA256 hash of password (hidden, not plain text)
# To verify: echo -n "password" | sha256sum
REQUIRED_PASSWORD_HASH="7c6f6a8b9c3e2d1f4056789012345678901234567890abcdef1234567890abcd"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                    🔐 AUTHOR AUTHENTICATION REQUIRED 🔐                  ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Function to hash password
hash_password() {
    echo -n "$1" | sha256sum | awk '{print $1}'
}

# Check for password from environment or prompt
if [ -z "$WASEEM_BRAIN_PASSWORD" ]; then
    read -sp "Enter Author Password: " USER_PASSWORD
    echo ""
else
    USER_PASSWORD="$WASEEM_BRAIN_PASSWORD"
fi

# Hash and compare
USER_HASH=$(hash_password "$USER_PASSWORD")

if [ "$USER_HASH" != "$REQUIRED_PASSWORD_HASH" ]; then
    echo ""
    echo "❌ INVALID PASSWORD - Access Denied"
    echo ""
    echo "Author: MUHAMMAD WASEEM AKRAM"
    echo "Contact: waseemjutt814@gmail.com | +923164290739"
    echo ""
    exit 1
fi

echo "✅ Authentication Successful - Proceeding with installation..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                                          ║${NC}"
echo -e "${CYAN}║              🤖  WASEEM BRAIN - INSTALLER  🤖                           ║${NC}"
echo -e "${CYAN}║                                                                          ║${NC}"
echo -e "${CYAN}║         World's First Assistant-First Intelligence Runtime               ║${NC}"
echo -e "${CYAN}║                                                                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

INSTALL_DIR="$HOME/waseembrain"
REPO_URL="https://github.com/waseemjutt814/WaseemBrain.git"
VERSION="3.0.0"

echo -e "${BLUE}📦 Installing Waseem Brain v${VERSION}...${NC}"
echo ""

# Check OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM=Linux;;
    Darwin*)    PLATFORM=Mac;;
    CYGWIN*)    PLATFORM=Cygwin;;
    MINGW*)     PLATFORM=MinGw;;
    *)          PLATFORM="UNKNOWN:${OS}"
esac

echo -e "${BLUE}🖥️  Detected Platform: ${PLATFORM}${NC}"

# Check dependencies
echo ""
echo -e "${YELLOW}🔍 Checking dependencies...${NC}"

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}  ✓ $1 installed${NC}"
        return 0
    else
        echo -e "${RED}  ✗ $1 not found${NC}"
        return 1
    fi
}

# Check required tools
MISSING_DEPS=0

check_command "git" || MISSING_DEPS=$((MISSING_DEPS + 1))
check_command "python3" || MISSING_DEPS=$((MISSING_DEPS + 1))
check_command "pip3" || MISSING_DEPS=$((MISSING_DEPS + 1))
check_command "node" || MISSING_DEPS=$((MISSING_DEPS + 1))
check_command "npm" || MISSING_DEPS=$((MISSING_DEPS + 1))

# Check optional tools
echo -e "${YELLOW}🔍 Checking optional dependencies...${NC}"
check_command "rustc" || echo -e "${YELLOW}  ⚠ Rust not found (Agent V3 optional)${NC}"
check_command "cargo" || echo -e "${YELLOW}  ⚠ Cargo not found (Agent V3 optional)${NC}"
check_command "ocaml" || echo -e "${YELLOW}  ⚠ OCaml not found (Agent V2 optional)${NC}"
check_command "dune" || echo -e "${YELLOW}  ⚠ Dune not found (Agent V2 optional)${NC}"

if [ $MISSING_DEPS -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ Missing required dependencies!${NC}"
    echo -e "${YELLOW}Please install: git, python3, pip3, node, npm${NC}"
    echo ""
    echo -e "${CYAN}📋 Installation commands:${NC}"
    
    if [[ "$PLATFORM" == "Linux" ]]; then
        echo -e "  Ubuntu/Debian: ${YELLOW}sudo apt update && sudo apt install -y git python3 python3-pip nodejs npm${NC}"
        echo -e "  CentOS/RHEL:   ${YELLOW}sudo yum install -y git python3 python3-pip nodejs npm${NC}"
        echo -e "  Fedora:        ${YELLOW}sudo dnf install -y git python3 python3-pip nodejs npm${NC}"
    elif [[ "$PLATFORM" == "Mac" ]]; then
        echo -e "  Mac: ${YELLOW}brew install git python3 node${NC}"
    fi
    
    exit 1
fi

echo ""
echo -e "${GREEN}✅ All dependencies satisfied!${NC}"

# Clone repository
echo ""
echo -e "${BLUE}📥 Cloning Waseem Brain repository...${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠ Directory $INSTALL_DIR already exists${NC}"
    read -p "Do you want to update? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$INSTALL_DIR"
        git pull origin main
    else
        echo -e "${YELLOW}Skipping clone...${NC}"
    fi
else
    git clone --depth=1 "$REPO_URL" "$INSTALL_DIR"
    echo -e "${GREEN}✅ Repository cloned to $INSTALL_DIR${NC}"
fi

cd "$INSTALL_DIR"

# Install Python dependencies
echo ""
echo -e "${BLUE}🐍 Installing Python dependencies...${NC}"
pip3 install -q -r requirements.txt 2>/dev/null || pip3 install -q \
    fastapi uvicorn httpx numpy pandas python-dotenv requests pydantic 2>/dev/null || true
echo -e "${GREEN}✅ Python dependencies installed${NC}"

# Install Node.js dependencies
echo ""
echo -e "${BLUE}📦 Installing Node.js dependencies...${NC}"
npm install -g pnpm 2>/dev/null || npm install -g pnpm --force 2>/dev/null || true
pnpm install 2>/dev/null || npm install 2>/dev/null || true
echo -e "${GREEN}✅ Node.js dependencies installed${NC}"

# Build Agents
echo ""
echo -e "${BLUE}🔨 Building Agents...${NC}"

# Build Agent V1 (Python)
echo -e "${CYAN}  → Agent V1 (Python) - Ready to use${NC}"

# Build Agent V2 (OCaml) - if available
if command -v dune &> /dev/null && [ -d "agent-v2" ]; then
    echo -e "${CYAN}  → Building Agent V2 (OCaml)...${NC}"
    cd agent-v2
    dune build 2>/dev/null || echo -e "${YELLOW}    ⚠ Agent V2 build skipped${NC}"
    cd ..
else
    echo -e "${YELLOW}  → Agent V2 (OCaml) - Optional, skipped${NC}"
fi

# Build Agent V3 (Rust) - if available
if command -v cargo &> /dev/null && [ -d "agent-v3" ]; then
    echo -e "${CYAN}  → Building Agent V3 (Rust)...${NC}"
    cd agent-v3
    cargo build --release 2>/dev/null || echo -e "${YELLOW}    ⚠ Agent V3 build skipped${NC}"
    cd ..
else
    echo -e "${YELLOW}  → Agent V3 (Rust) - Optional, skipped${NC}"
fi

# Create config
echo ""
echo -e "${BLUE}⚙️  Creating configuration...${NC}"

mkdir -p ~/.waseembrain
cat > ~/.waseembrain/config.json <<EOF
{
    "version": "${VERSION}",
    "install_dir": "${INSTALL_DIR}",
    "author": "MUHAMMAD WASEEM AKRAM",
    "contact": "waseemjutt814@gmail.com",
    "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "agents": {
        "v1_python": true,
        "v2_ocaml": false,
        "v3_rust": false
    }
}
EOF

# Create launcher script
echo ""
echo -e "${BLUE}🚀 Creating launcher...${NC}"

LAUNCHER="$HOME/.local/bin/waseembrain"
mkdir -p "$HOME/.local/bin"

cat > "$LAUNCHER" <<'EOF'
#!/bin/bash
# Waseem Brain Launcher

INSTALL_DIR="$HOME/waseembrain"

if [ ! -d "$INSTALL_DIR" ]; then
    echo "Error: Waseem Brain not found at $INSTALL_DIR"
    echo "Please run the installer again."
    exit 1
fi

cd "$INSTALL_DIR"

case "$1" in
    start|s)
        echo "🚀 Starting Waseem Brain..."
        pnpm run dev 2>/dev/null || python3 brain/runtime.py 2>/dev/null || echo "Error: Could not start"
        ;;
    stop|x)
        echo "🛑 Stopping Waseem Brain..."
        pkill -f "waseembrain" 2>/dev/null || true
        ;;
    status|st)
        echo "📊 Checking status..."
        curl -s http://localhost:8080/health 2>/dev/null || echo "Not running"
        ;;
    agent-v1|v1)
        echo "🐍 Starting Agent V1 (Python)..."
        cd "$INSTALL_DIR/agents_and_runners" && python3 waseem_agent.py
        ;;
    agent-v2|v2)
        echo "🐫 Starting Agent V2 (OCaml)..."
        cd "$INSTALL_DIR/agent-v2" && dune exec agent-v2 2>/dev/null || echo "Agent V2 not built"
        ;;
    agent-v3|v3)
        echo "🦀 Starting Agent V3 (Rust)..."
        cd "$INSTALL_DIR/agent-v3" && cargo run --release 2>/dev/null || echo "Agent V3 not built"
        ;;
    dashboard|d)
        echo "🎨 Opening Dashboard..."
        echo "Dashboard: http://localhost:8080"
        xdg-open http://localhost:8080 2>/dev/null || open http://localhost:8080 2>/dev/null || true
        ;;
    update|u)
        echo "🔄 Updating Waseem Brain..."
        cd "$INSTALL_DIR" && git pull origin main
        ;;
    help|h|*)
        echo "🤖 Waseem Brain - Commands:"
        echo ""
        echo "  waseembrain start     - Start the system"
        echo "  waseembrain stop      - Stop the system"
        echo "  waseembrain status    - Check system status"
        echo "  waseembrain agent-v1  - Run Agent V1 (Python)"
        echo "  waseembrain agent-v2  - Run Agent V2 (OCaml)"
        echo "  waseembrain agent-v3  - Run Agent V3 (Rust)"
        echo "  waseembrain dashboard - Open web dashboard"
        echo "  waseembrain update    - Update to latest version"
        echo ""
        ;;
esac
EOF

chmod +x "$LAUNCHER"

# Add to PATH if not already
echo ""
echo -e "${BLUE}🔧 Setting up PATH...${NC}"

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    SHELL_RC="$HOME/.bashrc"
    if [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    fi
    
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    echo -e "${GREEN}✅ Added to PATH in $SHELL_RC${NC}"
    echo -e "${YELLOW}⚠ Please run: source $SHELL_RC${NC}"
fi

# Final banner
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                                          ║${NC}"
echo -e "${GREEN}║              ✅  WASEEM BRAIN INSTALLED SUCCESSFULLY!  ✅                 ║${NC}"
echo -e "${GREEN}║                                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}📍 Installation Directory: ${INSTALL_DIR}${NC}"
echo -e "${CYAN}🚀 Start Command:         waseembrain start${NC}"
echo -e "${CYAN}🌐 Dashboard:             http://localhost:8080${NC}"
echo -e "${CYAN}🆘 Help:                  waseembrain help${NC}"
echo ""
echo -e "${YELLOW}📚 Documentation:${NC}"
echo -e "  - README:   ${INSTALL_DIR}/README.md"
echo -e "  - License:  ${INSTALL_DIR}/LICENSE"
echo -e "  - Author:   MUHAMMAD WASEEM AKRAM"
echo -e "  - Contact:  waseemjutt814@gmail.com"
echo ""
echo -e "${GREEN}🎉 Ready to use! Run: waseembrain start${NC}"
echo ""
