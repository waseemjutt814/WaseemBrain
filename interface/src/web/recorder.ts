import { encodePcm16Wave, mergeAudioChunks, mixChannelsToMono, resampleLinear } from "./wav.js";

export interface RecordedVoiceClip {
  blob: Blob;
  durationMs: number;
  fileName: string;
  mimeType: string;
  size: number;
  sampleRate: number;
}

type AudioContextFactory = typeof AudioContext;

function resolveAudioContextFactory(): AudioContextFactory | null {
  if (typeof window === "undefined") {
    return null;
  }
  const candidate = window.AudioContext ?? (window as Window & { webkitAudioContext?: AudioContextFactory }).webkitAudioContext;
  return candidate ?? null;
}

export class BrowserVoiceRecorder {
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private processorNode: ScriptProcessorNode | null = null;
  private sinkNode: GainNode | null = null;
  private chunks: Float32Array[] = [];
  private startedAt = 0;

  isRecording(): boolean {
    return this.mediaStream !== null;
  }

  async start(): Promise<void> {
    if (this.isRecording()) {
      throw new Error("Voice recording is already active.");
    }
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      throw new Error("This browser does not expose microphone capture.");
    }

    const AudioContextCtor = resolveAudioContextFactory();
    if (!AudioContextCtor) {
      throw new Error("This browser does not support the Web Audio API required for WAV capture.");
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 2,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    const audioContext = new AudioContextCtor();
    const sourceNode = audioContext.createMediaStreamSource(stream);
    const processorNode = audioContext.createScriptProcessor(4096, Math.max(sourceNode.channelCount, 1), 1);
    const sinkNode = audioContext.createGain();
    sinkNode.gain.value = 0;

    this.chunks = [];
    this.startedAt = Date.now();
    processorNode.onaudioprocess = (event) => {
      const channels: Float32Array[] = [];
      for (let channelIndex = 0; channelIndex < event.inputBuffer.numberOfChannels; channelIndex += 1) {
        channels.push(new Float32Array(event.inputBuffer.getChannelData(channelIndex)));
      }
      this.chunks.push(mixChannelsToMono(channels));
    };

    sourceNode.connect(processorNode);
    processorNode.connect(sinkNode);
    sinkNode.connect(audioContext.destination);

    this.mediaStream = stream;
    this.audioContext = audioContext;
    this.sourceNode = sourceNode;
    this.processorNode = processorNode;
    this.sinkNode = sinkNode;
  }

  async stop(): Promise<RecordedVoiceClip> {
    if (!this.isRecording() || this.audioContext === null) {
      throw new Error("Voice recording is not active.");
    }

    const sourceSampleRate = this.audioContext.sampleRate;
    const merged = mergeAudioChunks(this.chunks);
    const resampled = resampleLinear(merged, sourceSampleRate, 16000);
    const blob = encodePcm16Wave(resampled, 16000);
    const durationMs = Math.max(Date.now() - this.startedAt, 1);

    await this.cleanup();

    return {
      blob,
      durationMs,
      fileName: `voice-${Date.now()}.wav`,
      mimeType: "audio/wav",
      size: blob.size,
      sampleRate: 16000,
    };
  }

  async cancel(): Promise<void> {
    if (!this.isRecording()) {
      return;
    }
    await this.cleanup();
  }

  private async cleanup(): Promise<void> {
    this.processorNode?.disconnect();
    this.sourceNode?.disconnect();
    this.sinkNode?.disconnect();

    this.mediaStream?.getTracks().forEach((track) => track.stop());
    if (this.audioContext !== null && this.audioContext.state !== "closed") {
      await this.audioContext.close();
    }

    this.mediaStream = null;
    this.audioContext = null;
    this.sourceNode = null;
    this.processorNode = null;
    this.sinkNode = null;
    this.chunks = [];
    this.startedAt = 0;
  }
}
