import fs from "node:fs/promises";
import path from "node:path";

const banner = "// @ts-nocheck\n";

async function annotateDirectory(targetDir) {
  let entries = [];
  try {
    entries = await fs.readdir(targetDir, { withFileTypes: true });
  } catch {
    return;
  }

  for (const entry of entries) {
    const entryPath = path.join(targetDir, entry.name);
    if (entry.isDirectory()) {
      await annotateDirectory(entryPath);
      continue;
    }
    if (!entry.isFile() || !entry.name.endsWith(".js")) {
      continue;
    }
    const source = await fs.readFile(entryPath, "utf8");
    if (source.startsWith(banner)) {
      continue;
    }
    await fs.writeFile(entryPath, `${banner}${source}`, "utf8");
  }
}

async function main() {
  const targets = process.argv.slice(2);
  const resolvedTargets = targets.length > 0 ? targets : ["interface/generated"];
  for (const target of resolvedTargets) {
    await annotateDirectory(path.resolve(process.cwd(), target));
  }
}

await main();