function clampSample(value: number): number {
  if (value > 1) {
    return 1;
  }
  if (value < -1) {
    return -1;
  }
  return value;
}

export function mixChannelsToMono(channels: Float32Array[]): Float32Array {
  if (channels.length === 0) {
    return new Float32Array(0);
  }
  if (channels.length === 1) {
    return channels[0].slice();
  }

  const length = channels[0].length;
  const mixed = new Float32Array(length);
  for (let index = 0; index < length; index += 1) {
    let total = 0;
    for (const channel of channels) {
      total += channel[index] ?? 0;
    }
    mixed[index] = total / channels.length;
  }
  return mixed;
}

export function mergeAudioChunks(chunks: Float32Array[]): Float32Array {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const merged = new Float32Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }
  return merged;
}

export function resampleLinear(
  input: Float32Array,
  fromSampleRate: number,
  toSampleRate: number,
): Float32Array {
  if (input.length === 0 || fromSampleRate === toSampleRate) {
    return input.slice();
  }

  const ratio = fromSampleRate / toSampleRate;
  const outputLength = Math.max(Math.round(input.length / ratio), 1);
  const output = new Float32Array(outputLength);

  for (let index = 0; index < outputLength; index += 1) {
    const sourceIndex = index * ratio;
    const lowerIndex = Math.floor(sourceIndex);
    const upperIndex = Math.min(lowerIndex + 1, input.length - 1);
    const interpolation = sourceIndex - lowerIndex;
    const lower = input[lowerIndex] ?? 0;
    const upper = input[upperIndex] ?? lower;
    output[index] = lower + (upper - lower) * interpolation;
  }

  return output;
}

export function encodePcm16Wave(samples: Float32Array, sampleRate: number): Blob {
  const bytesPerSample = 2;
  const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample);
  const view = new DataView(buffer);

  const writeString = (offset: number, value: string): void => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * bytesPerSample, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * bytesPerSample, true);
  view.setUint16(32, bytesPerSample, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples.length * bytesPerSample, true);

  let offset = 44;
  for (const sample of samples) {
    const normalized = clampSample(sample);
    const value = normalized < 0 ? normalized * 0x8000 : normalized * 0x7fff;
    view.setInt16(offset, Math.round(value), true);
    offset += bytesPerSample;
  }

  return new Blob([buffer], { type: "audio/wav" });
}
