import assert from "node:assert/strict";
import test from "node:test";

import {
  actionNeedsPreview,
  appendStreamChunk,
  buildConnectionLabel,
  completeStream,
  createStreamRenderState,
  panelLabel,
  routeForMode,
  validateSubmission,
} from "../../interface/src/web/core.js";
import {
  encodePcm16Wave,
  mergeAudioChunks,
  mixChannelsToMono,
  resampleLinear,
} from "../../interface/src/web/wav.js";

test("browser shell routes each mode to the maintained HTTP endpoint", () => {
  assert.equal(routeForMode("text"), "/query/text");
  assert.equal(routeForMode("url"), "/query/url");
  assert.equal(routeForMode("file"), "/query/file");
  assert.equal(routeForMode("voice"), "/query/voice");
});

test("browser shell validation guards text url file and voice submissions", () => {
  assert.deepEqual(
    validateSubmission({
      mode: "text",
      textInput: "plan the runtime hardening",
      urlInput: "",
      file: null,
      recording: null,
    }),
    { ok: true, summary: "plan the runtime hardening" },
  );

  const invalidUrl = validateSubmission({
    mode: "url",
    textInput: "",
    urlInput: "not-a-url",
    file: null,
    recording: null,
  });
  assert.equal(invalidUrl.ok, false);

  const fileValidation = validateSubmission({
    mode: "file",
    textInput: "",
    urlInput: "",
    file: { fileName: "spec.pdf", mimeType: "application/pdf", size: 2048 },
    recording: null,
  });
  assert.equal(fileValidation.ok, true);
  if (fileValidation.ok) {
    assert.match(fileValidation.summary, /spec\.pdf/);
  }

  const voiceValidation = validateSubmission({
    mode: "voice",
    textInput: "",
    urlInput: "",
    file: null,
    recording: { fileName: "voice.wav", mimeType: "audio/wav", size: 4096, durationMs: 2500 },
  });
  assert.equal(voiceValidation.ok, true);
  if (voiceValidation.ok) {
    assert.match(voiceValidation.summary, /2\.5s/);
  }
});

test("browser shell exposes readable connection labels", () => {
  assert.match(buildConnectionLabel("checking"), /Checking runtime/);
  assert.equal(buildConnectionLabel("ready", "Runtime healthy"), "Runtime healthy");
  assert.match(buildConnectionLabel("busy", "Voice query in progress"), /Voice query in progress/);
  assert.match(buildConnectionLabel("error", "health fetch failed"), /health fetch failed/);
});

test("browser shell includes the memory panel label", () => {
  assert.equal(panelLabel("memory"), "Memory");
});

test("browser shell stream renderer captures late stream errors without losing content", () => {
  let state = createStreamRenderState();
  state = appendStreamChunk(state, "Paris is ");
  state = appendStreamChunk(state, "the capital of France ");
  state = appendStreamChunk(state, "[stream-error] bridge disconnected");
  state = completeStream(state);

  assert.equal(state.content, "Paris is the capital of France ");
  assert.equal(state.error, "bridge disconnected");
  assert.equal(state.completed, true);
});

test("browser wav helpers mix, resample, and encode RIFF output", async () => {
  const mixed = mixChannelsToMono([
    new Float32Array([1, 0, -1]),
    new Float32Array([0, 1, -1]),
  ]);
  assert.deepEqual(Array.from(mixed), [0.5, 0.5, -1]);

  const merged = mergeAudioChunks([
    new Float32Array([0, 0.5]),
    new Float32Array([-0.5, 1]),
  ]);
  assert.deepEqual(Array.from(merged), [0, 0.5, -0.5, 1]);

  const resampled = resampleLinear(new Float32Array([0, 1, 0, -1]), 8000, 16000);
  assert.ok(resampled.length > 4);

  const wavBlob = encodePcm16Wave(resampled, 16000);
  assert.equal(wavBlob.type, "audio/wav");
  const bytes = new Uint8Array(await wavBlob.arrayBuffer());
  const signature = String.fromCharCode(...bytes.slice(0, 4));
  const waveTag = String.fromCharCode(...bytes.slice(8, 12));
  assert.equal(signature, "RIFF");
  assert.equal(waveTag, "WAVE");
});




test("browser shell only shows preview controls for confirmation-required actions", () => {
  assert.equal(actionNeedsPreview({ confirmation_required: true }), true);
  assert.equal(actionNeedsPreview({ confirmation_required: false }), false);
  assert.equal(actionNeedsPreview(null), false);
});

