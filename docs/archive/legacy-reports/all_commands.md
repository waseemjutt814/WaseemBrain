# WaseemBrain - Master Command Index

This document outlines all critical commands to initialize, run, test, and interact with the WaseemBrain ecosystem. 
Always run these commands from the root directory of the repository.

## Installation & Setup
Installs all TypeScript interface boundaries, Rust execution daemons, and builds the Python environments explicitly via `package.json`.

```bash
npm run install:all
```

*This command automatically triggers `npm install`, the Python dependency setup (`npm run setup:python`), and `npm run build:all`.*

---

## 🚀 Live Functional Interaction (Terminal Chat)
To directly interact with WaseemBrain via an API-free terminal chat session, run the CLI chat script.

**(Windows native):**
```bash
py -3.11 scripts/chat_cli.py
```
**(Mac/Linux natively):**
```bash
python3 scripts/chat_cli.py
```

### Direct CLI Modes:
You can also bypass the CLI wizard by passing a direct argument:
```bash
py -3.11 scripts/chat_cli.py "What is your primary reasoning protocol?" --once
```

---

## ⚙️ Running The Daemons

### 1. Interface Gateway (TypeScript Frontend)
Starts the Fastify WebSockets/HTTP gateway that orchestrates routing paths to the Python core and Rust engine.
```bash
npm start
# or for development:
npm run dev
```

### 2. Brain Runtime (Python)
If running manually outside of the Gateway, you can boot the coordinator runtime directly.
```bash
npm run start:python
```

---

## 🧪 Testing Matrices

WaseemBrain operates with a strictly configured test suite validating its Offline, API-Free capabilities.

### Run ALL tests automatically (Python, TS, Rust)
```bash
npm run test:all
```

### Run Python Core Evaluators (Professional Report)
```bash
npm run test:python
# Generates a professional validation output inside tests/python/test_report_professional.json
```

### Run Typescript Gateway Tests
Validates the Python bridging layer built inside `interface/src/python_gateway.ts`.
```bash
npm run test:ts
```

### Run Rust Daemon Tests
```bash
npm run test:rust
```

---

## Maintenance & Code Auditing

**Format Codebase (`black` & `ruff`)**
```bash
npm run format
```

**Lint Codebase (`mypy` & `ruff`)**
```bash
npm run lint
```

**Hard Clean Directories**
```bash
npm run clean
```
