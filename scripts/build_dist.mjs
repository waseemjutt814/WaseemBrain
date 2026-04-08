import { spawnSync } from "node:child_process";
import { copyFile, cp, mkdir, rm, writeFile } from "node:fs/promises";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const distDir = path.join(root, "dist");
const publicSourceDir = path.join(root, "interface", "public");
const generatedSourceDir = path.join(root, "interface", "generated");
const publicTargetDir = path.join(distDir, "interface", "public");
const generatedTargetDir = path.join(distDir, "interface", "generated");
const pythonDistDir = path.join(distDir, "python");
const tscEntrypoint = path.join(root, "node_modules", "typescript", "bin", "tsc");
const pythonRunner = path.join(root, "scripts", "run_python.mjs");
const annotateGeneratedScript = path.join(root, "scripts", "annotate_generated_js.mjs");
const packageJsonPath = path.join(root, "package.json");
const rootPackage = JSON.parse(fs.readFileSync(packageJsonPath, "utf8"));

const rootFilesToCopy = [
  ".env.example",
  "LICENSE.md",
  "NOTICE.md",
  "pyproject.toml",
  "waseem.manifest.json",
  "docker-compose.yml",
];

const runtimeSourceDirectories = [
  "assets",
  "brain",
  path.join("experts", "base"),
  path.join("experts", "bootstrap"),
];

const runtimeSourceFiles = [
  path.join("experts", "registry.json"),
  path.join("experts", "router.json"),
  path.join("experts", "response-policy.json"),
  path.join("experts", "knowledge-manifest.json"),
  path.join("scripts", "coordinator_bridge.py"),
  path.join("scripts", "run_python.mjs"),
  path.join("scripts", "runtime_daemon.py"),
  path.join("scripts", "manage_runtime_daemon.py"),
];

function runOrExit(command, args) {
  const result = spawnSync(command, args, {
    cwd: root,
    stdio: "inherit",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function shouldCopyPath(sourcePath) {
  const normalized = sourcePath.replace(/\\/g, "/");
  if (normalized.endsWith("/__pycache__") || normalized.includes("/__pycache__/")) {
    return false;
  }
  if (normalized.endsWith(".pyc") || normalized.endsWith(".pyo")) {
    return false;
  }
  return true;
}

async function copyIfExists(sourceRelativePath, targetRelativePath = sourceRelativePath) {
  const sourcePath = path.join(root, sourceRelativePath);
  if (!fs.existsSync(sourcePath)) {
    return;
  }
  const targetPath = path.join(distDir, targetRelativePath);
  await mkdir(path.dirname(targetPath), { recursive: true });
  await copyFile(sourcePath, targetPath);
}

async function copyDirectoryIfExists(sourceRelativePath, targetRelativePath = sourceRelativePath) {
  const sourcePath = path.join(root, sourceRelativePath);
  if (!fs.existsSync(sourcePath)) {
    return;
  }
  const targetPath = path.join(distDir, targetRelativePath);
  await mkdir(path.dirname(targetPath), { recursive: true });
  await cp(sourcePath, targetPath, {
    recursive: true,
    force: true,
    filter: shouldCopyPath,
  });
}

function createDistPackage() {
  return {
    name: rootPackage.name,
    version: rootPackage.version,
    description: rootPackage.description,
    author: rootPackage.author,
    license: rootPackage.license,
    private: true,
    type: rootPackage.type,
    packageManager: rootPackage.packageManager,
    engines: rootPackage.engines,
    scripts: {
      start: "node interface/src/server.js",
      "install:python": "node scripts/run_python.mjs -m pip install -r python/requirements-runtime.txt",
      "install:all": "pnpm install && pnpm run install:python",
      "start:python": "node scripts/run_python.mjs -m brain.runtime",
    },
    dependencies: rootPackage.dependencies,
  };
}

function createDistReadme() {
  return `# Waseem Brain Dist Bundle

Deployable Waseem Brain runtime bundle produced by \`pnpm run build\`.

## Ownership
Created and owned by Muhammad Waseem Akram.

Source-visible and restricted-use. See \`LICENSE.md\` and \`NOTICE.md\` before any reuse, redistribution, or deployment.

## What Is Included
- Compiled Fastify interface server in \`interface/src/\`
- Generated browser shell in \`interface/generated/\`
- Runtime public assets in \`interface/public/\`
- Shared brand assets in \`assets/\`
- Python runtime sources in \`brain/\`
- Expert manifests, datasets, and bootstrap knowledge in \`experts/\`
- Dist-local bridge scripts in \`scripts/\`
- Python wheel and runtime dependency list in \`python/\`
- Ownership and restricted-use notice files at the dist root

## Requirements
- Node.js ${rootPackage.engines.node}
- Python ${rootPackage.engines.python}

## Install
\`pnpm install\`

\`pnpm run install:python\`

If your Python 3.11 executable is not on the default path, set \`PYTHON_EXECUTABLE\` before running the install or start commands.

## Run
\`pnpm start\`

The server will start from this directory and use the dist-local bridge, public interface, and shared brand assets.

## Layout
- \`interface/src/server.js\`: Node entrypoint
- \`interface/generated/app.js\`: typed browser shell bundle
- \`assets/\`: shared Waseem Brain SVG branding assets
- \`brain/\`: Python runtime source
- \`experts/\`: expert registry, manifests, and built-in knowledge
- \`python/requirements-runtime.txt\`: runtime dependency snapshot
- \`python/*.whl\`: packaged Python wheel artifact

## Notes
- This bundle is deployable, not fully vendored. Install Node and Python dependencies on the target machine.
- The preserved WebSocket route remains available for text and URL compatibility, but the browser shell uses the maintained HTTP query routes for all modes.
- Ownership and usage restrictions travel with this bundle and are not limited to the source repository view.
`;
}

async function writeRuntimeRequirements() {
  const requirements = Array.isArray(rootPackage.pythonDependencyGroups?.runtime)
    ? rootPackage.pythonDependencyGroups.runtime.join("\n") + "\n"
    : "";
  await writeFile(path.join(pythonDistDir, "requirements-runtime.txt"), requirements, "utf8");
}

async function writeDistMetadata() {
  await writeFile(
    path.join(distDir, "package.json"),
    `${JSON.stringify(createDistPackage(), null, 2)}\n`,
    "utf8",
  );
  await writeFile(path.join(distDir, "README.md"), createDistReadme(), "utf8");
}

async function main() {
  await rm(distDir, { recursive: true, force: true });
  await rm(generatedSourceDir, { recursive: true, force: true });

  runOrExit(process.execPath, [tscEntrypoint, "-p", "tsconfig.json"]);
  runOrExit(process.execPath, [tscEntrypoint, "-p", "tsconfig.web.json"]);
  runOrExit(process.execPath, [annotateGeneratedScript, generatedSourceDir]);

  if (fs.existsSync(publicSourceDir)) {
    await mkdir(path.dirname(publicTargetDir), { recursive: true });
    await cp(publicSourceDir, publicTargetDir, { recursive: true, force: true });
    console.log(`[build] copied static assets to ${path.relative(root, publicTargetDir)}`);
  }

  if (fs.existsSync(generatedSourceDir)) {
    await mkdir(path.dirname(generatedTargetDir), { recursive: true });
    await cp(generatedSourceDir, generatedTargetDir, { recursive: true, force: true });
    console.log(`[build] copied generated browser assets to ${path.relative(root, generatedTargetDir)}`);
  }

  for (const relativePath of rootFilesToCopy) {
    await copyIfExists(relativePath);
  }
  for (const relativePath of runtimeSourceFiles) {
    await copyIfExists(relativePath);
  }
  for (const relativePath of runtimeSourceDirectories) {
    await copyDirectoryIfExists(relativePath);
  }

  await mkdir(pythonDistDir, { recursive: true });
  runOrExit(process.execPath, [
    pythonRunner,
    "-m",
    "pip",
    "wheel",
    "--no-deps",
    "--wheel-dir",
    pythonDistDir,
    ".",
  ]);
  console.log(`[build] built Python wheel into ${path.relative(root, pythonDistDir)}`);

  await writeRuntimeRequirements();
  await writeDistMetadata();
  console.log(`[build] dist ready at ${distDir}`);
}

await main();