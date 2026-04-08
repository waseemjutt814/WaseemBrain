import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { PassThrough } from "node:stream";
import test from "node:test";

import { VoicePlayer } from "../../interface/src/voice/player.js";
import { VoiceRecorder } from "../../interface/src/voice/recorder.js";

test("VoiceRecorder captures audio chunks and returns capture metadata", () => {
  const stream = new PassThrough();
  let stopped = false;

  const recorder = new VoiceRecorder(() => ({
    stream: () => stream,
    stop: () => {
      stopped = true;
    },
    pause: () => undefined,
    resume: () => undefined,
    isPaused: () => false,
  }));

  recorder.start({ sampleRate: 8000, channels: 1, audioType: "raw" });
  stream.write(Buffer.from("abc", "utf-8"));
  stream.write(Buffer.from("def", "utf-8"));

  const capture = recorder.stop();
  assert.equal(stopped, true);
  assert.equal(recorder.isRecording(), false);
  assert.equal(capture.audio.toString("utf-8"), "abcdef");
  assert.equal(capture.bytes, 6);
  assert.equal(capture.sampleRate, 8000);
  assert.equal(capture.channels, 1);
  assert.equal(capture.mimeType, "audio/L16");
  assert.deepEqual(recorder.getLastCapture(), capture);
});

test("VoiceRecorder rejects invalid state transitions", () => {
  const recorder = new VoiceRecorder(() => ({
    stream: () => new PassThrough(),
    stop: () => undefined,
  }));

  assert.throws(() => recorder.stop(), /not active/i);
  recorder.start();
  assert.throws(() => recorder.start(), /already in progress/i);
});

test("VoicePlayer writes payloads to disk and can skip auto-open", async () => {
  const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), "waseem-brain-voice-"));
  const outputPath = path.join(tempRoot, "reply.wav");
  let openedPath = "";

  const player = new VoicePlayer(async (filePath) => {
    openedPath = filePath;
  });

  const payload = Buffer.from("voice-bytes", "utf-8");
  const result = await player.play(payload, {
    filePath: outputPath,
    mimeType: "audio/wav",
  });

  assert.equal(result.filePath, outputPath);
  assert.equal(result.bytesWritten, payload.length);
  assert.equal(result.opened, true);
  assert.equal(openedPath, outputPath);
  assert.equal((await fs.readFile(outputPath)).toString("utf-8"), "voice-bytes");

  const silentPath = path.join(tempRoot, "reply-2.wav");
  const silentResult = await player.play(payload, {
    filePath: silentPath,
    launch: false,
  });
  assert.equal(silentResult.opened, false);

  await fs.rm(tempRoot, { recursive: true, force: true });
});