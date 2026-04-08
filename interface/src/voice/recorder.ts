import { createRequire } from "node:module";
import type { Readable } from "node:stream";

const require = createRequire(import.meta.url);

type RecorderProgram = "sox" | "rec" | "arecord";
type AudioType = "wav" | "raw";

type RecorderOptions = {
  sampleRate: number;
  channels: number;
  threshold: number;
  silence: string;
  recorder: RecorderProgram;
  audioType: AudioType;
};

type RecorderHandle = {
  stream(): Readable;
  stop(): void;
  pause?(): void;
  resume?(): void;
  isPaused?(): boolean;
};

type RecorderModule = {
  record(options: RecorderOptions): RecorderHandle;
};

const recorderModule = require("node-record-lpcm16") as RecorderModule;

export interface VoiceRecorderOptions {
  sampleRate?: number;
  channels?: number;
  threshold?: number;
  silence?: string;
  recorder?: RecorderProgram;
  audioType?: AudioType;
  onChunk?: (chunk: Buffer) => void;
}

export interface VoiceCapture {
  audio: Buffer;
  bytes: number;
  mimeType: string;
  sampleRate: number;
  channels: number;
  startedAt: number;
  stoppedAt: number;
  durationMs: number;
}

const DEFAULT_OPTIONS: RecorderOptions = {
  sampleRate: 16000,
  channels: 1,
  threshold: 0,
  silence: "1.0",
  recorder: "sox",
  audioType: "wav",
};

function normalizeOptions(options: VoiceRecorderOptions): RecorderOptions {
  return {
    sampleRate: options.sampleRate ?? DEFAULT_OPTIONS.sampleRate,
    channels: options.channels ?? DEFAULT_OPTIONS.channels,
    threshold: options.threshold ?? DEFAULT_OPTIONS.threshold,
    silence: options.silence ?? DEFAULT_OPTIONS.silence,
    recorder: options.recorder ?? DEFAULT_OPTIONS.recorder,
    audioType: options.audioType ?? DEFAULT_OPTIONS.audioType,
  };
}

function inferMimeType(audioType: AudioType): string {
  if (audioType === "raw") {
    return "audio/L16";
  }
  return "audio/wav";
}

export class VoiceRecorder {
  private recording = false;
  private chunks: Buffer[] = [];
  private activeHandle: RecorderHandle | null = null;
  private activeStream: Readable | null = null;
  private activeOptions: RecorderOptions = DEFAULT_OPTIONS;
  private startedAt = 0;
  private lastCapture: VoiceCapture | null = null;

  constructor(
    private readonly recordFactory: (options: RecorderOptions) => RecorderHandle = (options) =>
      recorderModule.record(options),
  ) {}

  start(options: VoiceRecorderOptions = {}): void {
    if (this.recording) {
      throw new Error("Voice recording is already in progress");
    }

    this.activeOptions = normalizeOptions(options);
    this.chunks = [];
    this.lastCapture = null;
    this.startedAt = Date.now();

    const handle = this.recordFactory(this.activeOptions);
    const stream = handle.stream();

    stream.on("data", (chunk: Buffer | string) => {
      const bufferChunk = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk, "binary");
      this.chunks.push(bufferChunk);
      options.onChunk?.(bufferChunk);
    });

    stream.on("error", () => {
      this.recording = false;
      this.activeHandle = null;
      this.activeStream = null;
    });

    this.activeHandle = handle;
    this.activeStream = stream;
    this.recording = true;
  }

  stop(): VoiceCapture {
    if (!this.recording || this.activeHandle === null) {
      throw new Error("Voice recording is not active");
    }

    this.activeHandle.stop();
    const stoppedAt = Date.now();
    const audio = Buffer.concat(this.chunks);
    const capture: VoiceCapture = {
      audio,
      bytes: audio.length,
      mimeType: inferMimeType(this.activeOptions.audioType),
      sampleRate: this.activeOptions.sampleRate,
      channels: this.activeOptions.channels,
      startedAt: this.startedAt,
      stoppedAt,
      durationMs: Math.max(stoppedAt - this.startedAt, 0),
    };

    this.recording = false;
    this.activeHandle = null;
    this.activeStream = null;
    this.chunks = [];
    this.lastCapture = capture;
    return capture;
  }

  pause(): void {
    if (!this.recording || this.activeHandle?.pause === undefined) {
      throw new Error("Voice recorder pause is unavailable");
    }
    this.activeHandle.pause();
  }

  resume(): void {
    if (!this.recording || this.activeHandle?.resume === undefined) {
      throw new Error("Voice recorder resume is unavailable");
    }
    this.activeHandle.resume();
  }

  isPaused(): boolean {
    if (!this.recording || this.activeHandle?.isPaused === undefined) {
      return false;
    }
    return this.activeHandle.isPaused();
  }

  isRecording(): boolean {
    return this.recording;
  }

  getLastCapture(): VoiceCapture | null {
    return this.lastCapture;
  }
}