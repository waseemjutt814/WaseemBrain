import { execFile } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export interface VoicePlaybackOptions {
  filePath?: string;
  mimeType?: string;
  extension?: string;
  launch?: boolean;
}

export interface VoicePlaybackResult {
  filePath: string;
  mimeType: string;
  bytesWritten: number;
  opened: boolean;
}

function inferExtension(mimeType: string, preferred?: string): string {
  if (preferred) {
    return preferred.startsWith(".") ? preferred : `.${preferred}`;
  }
  if (mimeType === "audio/wav" || mimeType === "audio/x-wav") {
    return ".wav";
  }
  if (mimeType === "audio/mpeg") {
    return ".mp3";
  }
  return ".bin";
}

async function openWithSystemPlayer(filePath: string): Promise<void> {
  if (process.platform === "win32") {
    await execFileAsync("cmd", ["/d", "/c", "start", "", filePath]);
    return;
  }
  if (process.platform === "darwin") {
    await execFileAsync("open", [filePath]);
    return;
  }
  await execFileAsync("xdg-open", [filePath]);
}

export class VoicePlayer {
  constructor(private readonly opener: (filePath: string) => Promise<void> = openWithSystemPlayer) {}

  async play(payload: Buffer, options: VoicePlaybackOptions = {}): Promise<VoicePlaybackResult> {
    if (payload.length === 0) {
      throw new Error("Cannot play an empty voice payload");
    }

    const mimeType = options.mimeType ?? "audio/wav";
    const filePath =
      options.filePath ??
      path.join(
        os.tmpdir(),
        `waseem-brain-playback-${Date.now()}-${Math.random().toString(36).slice(2, 8)}${inferExtension(mimeType, options.extension)}`,
      );

    await mkdir(path.dirname(filePath), { recursive: true });
    await writeFile(filePath, payload);

    let opened = false;
    if (options.launch !== false) {
      await this.opener(filePath);
      opened = true;
    }

    return {
      filePath,
      mimeType,
      bytesWritten: payload.length,
      opened,
    };
  }
}