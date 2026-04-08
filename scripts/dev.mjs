import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import readline from "node:readline/promises";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pythonRunner = path.join(root, "scripts", "run_python.mjs");
const interfaceLogPath = path.join(root, "tmp", "dev", "interface.log");
const interfaceHost = "127.0.0.1";
const interfacePort = Number.parseInt(process.env.API_PORT ?? "8080", 10) || 8080;

let backgroundInterface = null;
let isCleaningUp = false;

function pnpmLaunch(args) {
  const execPath = process.env.npm_execpath?.trim();
  if (execPath && execPath.toLowerCase().includes("pnpm")) {
    return {
      command: process.execPath,
      args: [execPath, ...args],
    };
  }
  return {
    command: process.platform === "win32" ? "pnpm.cmd" : "pnpm",
    args,
  };
}

function normalizeTarget(rawValue) {
  const normalized = rawValue?.trim().toLowerCase() ?? "";
  switch (normalized) {
    case "1":
    case "interface":
    case "web":
    case "browser":
      return "interface";
    case "2":
    case "terminal":
    case "cli":
    case "chat":
      return "terminal";
    case "3":
    case "both":
    case "all":
      return "both";
    case "4":
    case "backend":
    case "runtime":
      return "backend";
    default:
      return null;
  }
}

function parseTargetArg(argv = process.argv.slice(2)) {
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--help" || value === "-h") {
      return "help";
    }
    if (value === "--target" || value === "-t") {
      return normalizeTarget(argv[index + 1]);
    }
    if (value.startsWith("--target=")) {
      return normalizeTarget(value.slice("--target=".length));
    }
  }
  return null;
}

function printUsage() {
  console.log("Waseem Brain dev launcher");
  console.log("");
  console.log("Usage:");
  console.log("  pnpm run dev");
  console.log("  pnpm run dev -- --target interface|terminal|both|backend");
  console.log("");
  console.log("Shortcuts:");
  console.log("  pnpm run dev:interface");
  console.log("  pnpm run dev:terminal");
  console.log("  pnpm run dev:both");
  console.log("  pnpm run dev:backend");
}

async function selectTarget() {
  if (!process.stdin.isTTY || !process.stdout.isTTY) {
    return "interface";
  }

  const prompt = [
    "Waseem Brain dev launcher",
    "",
    "1. Interface only",
    "2. Terminal only",
    "3. Interface + Terminal",
    "4. Backend only",
    "",
    "Select a target (default 1): ",
  ].join("\n");

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  try {
    while (true) {
      const answer = await rl.question(prompt);
      if (!answer.trim()) {
        return "interface";
      }
      const target = normalizeTarget(answer);
      if (target) {
        return target;
      }
      console.log("[dev] Choose 1, 2, 3, or 4.");
    }
  } finally {
    rl.close();
  }
}

async function spawnProcess(command, args, options = {}) {
  return await new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: root,
      env: { ...process.env, ...(options.env ?? {}) },
      stdio: options.stdio ?? "inherit",
      shell: options.shell ?? false,
    });
    child.once("error", reject);
    child.once("exit", (code, signal) => {
      resolve({
        child,
        code: code ?? (signal ? 1 : 0),
        signal: signal ?? null,
      });
    });
  });
}

async function runChecked(label, command, args, options = {}) {
  console.log(`[dev] ${label}`);
  const result = await spawnProcess(command, args, options);
  if (result.code !== 0) {
    throw new Error(`${label} failed with exit code ${result.code}`);
  }
  return result;
}

async function runPython(args, options = {}) {
  return await spawnProcess(process.execPath, [pythonRunner, ...args], options);
}

async function ensureRuntimeDaemon() {
  console.log("[dev] Ensuring Python runtime daemon is available...");
  const result = await runPython(["scripts/manage_runtime_daemon.py", "start"]);
  if (result.code !== 0) {
    throw new Error("Python runtime daemon did not start cleanly.");
  }
}

async function maybeEnsureRouterDaemon() {
  const routerBackend = (process.env.ROUTER_BACKEND ?? "local").trim().toLowerCase();
  if (!routerBackend || routerBackend === "local") {
    console.log("[dev] Router backend is local; no detached router daemon is required.");
    return;
  }

  console.log(`[dev] Router backend is ${routerBackend}; checking router daemon...`);
  const args = ["scripts/manage_router_daemon.py", "start"];
  if (routerBackend === "auto") {
    args.push("--skip-build");
  }

  const result = await runPython(args);
  if (result.code === 0) {
    return;
  }

  if (routerBackend === "auto") {
    console.log(
      "[dev] Optional router daemon did not start in auto mode. Continuing with local artifact fallback.",
    );
    return;
  }

  throw new Error("Router backend is grpc but the router daemon could not be started.");
}

async function buildWeb() {
  const launch = pnpmLaunch(["run", "build:web"]);
  await runChecked("Building browser shell...", launch.command, launch.args);
}

function interfaceUrl() {
  return `http://${interfaceHost}:${interfacePort}/chat.html`;
}

function readInterfaceLogTail() {
  if (!fs.existsSync(interfaceLogPath)) {
    return "No interface log output was captured.";
  }
  const raw = fs.readFileSync(interfaceLogPath, "utf8").trim();
  if (!raw) {
    return "No interface log output was captured.";
  }
  return raw.slice(-4000);
}

async function waitForInterfaceReady(child, timeoutMs = 15000) {
  const healthUrl = `http://${interfaceHost}:${interfacePort}/health`;
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(
        `Interface server exited before becoming ready.\n\n${readInterfaceLogTail()}`,
      );
    }
    try {
      const response = await fetch(healthUrl);
      if (response.ok) {
        return;
      }
    } catch {
      // Keep polling until the timeout expires.
    }
    await delay(500);
  }

  throw new Error(
    `Interface server did not become ready within ${Math.round(timeoutMs / 1000)}s.\n\n${readInterfaceLogTail()}`,
  );
}

async function startInterfaceForeground() {
  await buildWeb();
  const launch = pnpmLaunch(["exec", "tsx", "interface/src/server.ts"]);
  const result = await spawnProcess(launch.command, launch.args, {
    env: { WB_GATEWAY_MODE: "daemon" },
    stdio: "inherit",
  });
  return result.code;
}

async function startInterfaceBackground() {
  await buildWeb();
  await mkdir(path.dirname(interfaceLogPath), { recursive: true });
  const logStream = fs.createWriteStream(interfaceLogPath, { flags: "a" });
  const launch = pnpmLaunch(["exec", "tsx", "interface/src/server.ts"]);
  const child = spawn(launch.command, launch.args, {
    cwd: root,
    env: { ...process.env, WB_GATEWAY_MODE: "daemon" },
    stdio: ["ignore", "pipe", "pipe"],
    shell: false,
  });
  child.stdout.pipe(logStream);
  child.stderr.pipe(logStream);
  backgroundInterface = { child, logStream };

  try {
    await waitForInterfaceReady(child);
  } catch (error) {
    await stopInterfaceBackground();
    throw error;
  }

  console.log(`[dev] Interface is live at ${interfaceUrl()}`);
  console.log(`[dev] Interface logs: ${path.relative(root, interfaceLogPath)}`);
}

async function stopInterfaceBackground() {
  if (!backgroundInterface) {
    return;
  }

  const active = backgroundInterface;
  backgroundInterface = null;

  if (active.child.exitCode === null) {
    if (process.platform === "win32") {
      spawnSync("taskkill", ["/PID", String(active.child.pid), "/T", "/F"], {
        stdio: "ignore",
      });
    } else {
      active.child.kill("SIGTERM");
    }
    await delay(250);
  }

  active.logStream.end();
}

async function runTerminal() {
  console.log("[dev] Launching terminal chat against the hot runtime daemon...");
  const result = await runPython(["scripts/chat_cli.py", "--runtime-daemon", "always"], {
    stdio: "inherit",
  });
  return result.code;
}

async function cleanup(code) {
  if (isCleaningUp) {
    return;
  }
  isCleaningUp = true;
  await stopInterfaceBackground();
  process.exit(code);
}

process.on("SIGINT", () => {
  void cleanup(130);
});

process.on("SIGTERM", () => {
  void cleanup(143);
});

async function main() {
  const requestedTarget = parseTargetArg();
  if (requestedTarget === "help") {
    printUsage();
    return 0;
  }

  const target = requestedTarget ?? await selectTarget();
  if (!target) {
    printUsage();
    return 1;
  }

  await ensureRuntimeDaemon();
  await maybeEnsureRouterDaemon();

  if (target === "backend") {
    console.log("[dev] Backend is ready.");
    console.log("[dev] Next: pnpm run dev:interface, pnpm run dev:terminal, or pnpm run runtime:stop");
    return 0;
  }

  if (target === "interface") {
    return await startInterfaceForeground();
  }

  if (target === "terminal") {
    return await runTerminal();
  }

  await startInterfaceBackground();
  try {
    return await runTerminal();
  } finally {
    await stopInterfaceBackground();
  }
}

try {
  const code = await main();
  await stopInterfaceBackground();
  process.exit(code);
} catch (error) {
  await stopInterfaceBackground();
  const message = error instanceof Error ? error.message : String(error);
  console.error(`[dev] ${message}`);
  process.exit(1);
}