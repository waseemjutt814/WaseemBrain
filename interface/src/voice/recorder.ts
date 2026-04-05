export class VoiceRecorder {
  private recording = false;

  start(): void {
    this.recording = true;
  }

  stop(): void {
    this.recording = false;
  }

  isRecording(): boolean {
    return this.recording;
  }
}
