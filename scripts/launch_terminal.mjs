import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pythonRunner = path.join(root, "scripts", "run_python.mjs");
const forwardedArgs = process.argv.slice(2);

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: root,
      env: { ...process.env, ...(options.env ?? {}) },
      stdio: options.stdio ?? "inherit",
      shell: false,
    });
    child.once("error", reject);
    child.once("exit", (code, signal) => {
      resolve({ code: code ?? (signal ? 1 : 0), signal: signal ?? null });
    });
  });
}

async function ensureRuntimeDaemon() {
  const result = await run(process.execPath, [pythonRunner, "scripts/manage_runtime_daemon.py", "start"]);
  if (result.code !== 0) {
    throw new Error(`Runtime daemon did not start cleanly (exit ${result.code}).`);
  }
}

async function main() {
  await ensureRuntimeDaemon();
  const result = await run(process.execPath, [
    pythonRunner,
    "scripts/chat_cli.py",
    "--runtime-daemon",
    "always",
    ...forwardedArgs,
  ]);
  process.exit(result.code);
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`[chat] ${message}`);
  process.exit(1);
});
