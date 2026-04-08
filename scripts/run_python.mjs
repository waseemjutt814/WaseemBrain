import { spawnSync } from "node:child_process";

const args = process.argv.slice(2);
const override = process.env.PYTHON_EXECUTABLE?.trim();
const isWindows = process.platform === "win32";

function attempt(command, commandArgs) {
  const result = spawnSync(command, commandArgs, {
    stdio: "inherit",
    shell: false,
  });
  if (result.error) {
    return { ok: false, error: result.error };
  }
  process.exit(result.status ?? 1);
}

if (override) {
  attempt(override, args);
  console.error(`Configured PYTHON_EXECUTABLE was not runnable: ${override}`);
  process.exit(1);
}

const candidates = isWindows
  ? [{ command: "py", args: ["-3.11", ...args] }, { command: "python", args }]
  : [
      { command: "python3.11", args },
      { command: "python3", args },
      { command: "python", args },
    ];

for (const candidate of candidates) {
  const result = attempt(candidate.command, candidate.args);
  if (result?.ok === false) {
    continue;
  }
}

console.error(
  "Unable to find a usable Python 3.11 executable. Set PYTHON_EXECUTABLE to override autodetection.",
);
process.exit(1);