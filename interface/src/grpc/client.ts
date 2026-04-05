export interface RouterDecision {
  expert_ids: string[];
  check_memory_first: boolean;
  internet_needed: boolean;
  confidence: number;
  reasoning_trace: string;
  latency_ms: number;
}

export interface RouterClient {
  decide(input: {
    text: string;
    modality: string;
    session_id: string;
    emotion_valence: number;
    emotion_arousal: number;
    emotion_primary: string;
  }): Promise<RouterDecision>;
}
