import { z } from "zod";

export const TextQueryRequestSchema = z.object({
  modality: z.literal("text"),
  input: z.string().min(1),
  session_id: z.string().min(1),
});

export const UrlQueryRequestSchema = z.object({
  modality: z.literal("url"),
  url: z.string().url(),
  session_id: z.string().min(1),
});

export const BinaryQueryRequestSchema = z.object({
  modality: z.enum(["voice", "file"]),
  input_base64: z.string().min(1),
  filename: z.string().min(1),
  mime_type: z.string().min(1),
  session_id: z.string().min(1),
});

export const LegacyQueryRequestSchema = z.object({
  input: z.string().min(1),
  modality: z.literal("text"),
  session_id: z.string().min(1),
});

export const QueryRequestSchema = z.discriminatedUnion("modality", [
  TextQueryRequestSchema,
  UrlQueryRequestSchema,
  BinaryQueryRequestSchema,
]);

export const WsQueryRequestSchema = z.discriminatedUnion("modality", [
  TextQueryRequestSchema,
  UrlQueryRequestSchema,
]);

export const StreamMessageSchema = z.object({
  type: z.enum(["token", "done", "error"]),
  content: z.string(),
});

export const HealthResponseSchema = z.object({
  status: z.literal("ok"),
  project_name: z.string(),
  condition: z.enum(["strong", "ready", "attention"]),
  condition_summary: z.string(),
  ready: z.boolean(),
  experts_loaded: z.number().int().nonnegative(),
  experts_available: z.number().int().nonnegative(),
  expert_ids: z.array(z.string()),
  memory_node_count: z.number().int().nonnegative(),
  uptime_sec: z.number().nonnegative(),
  router_backend: z.string(),
  vector_backend: z.string(),
  components: z.record(z.string()),
  learning: z.object({
    enabled: z.boolean(),
    backend: z.string(),
    response_policy: z.string(),
    trace_files: z.number().int().nonnegative(),
    trace_turns: z.number().int().nonnegative(),
    expert_trace_files: z.number().int().nonnegative(),
    expert_trace_turns: z.number().int().nonnegative(),
    training_jobs: z.number().int().nonnegative(),
    datasets: z.number().int().nonnegative(),
    trained_trace_count: z.number().int().nonnegative(),
    last_event: z.string(),
    phase: z.string(),
  }),
  knowledge: z.object({
    status: z.string(),
    datasets: z.number().int().nonnegative(),
    cards: z.number().int().nonnegative(),
    seeded_cards: z.number().int().nonnegative(),
    seeded_this_run: z.number().int().nonnegative(),
    source_dir: z.string(),
    version: z.string(),
    dataset_ids: z.array(z.string()),
    last_seeded_at: z.number().nonnegative(),
    note: z.string(),
  }),
  router: z.object({
    mode: z.string(),
    artifact: z.string(),
    target: z.string(),
    daemon_state: z.string(),
    pid: z.number().int().nonnegative().optional(),
    port: z.number().int().nonnegative().optional(),
    uptime_sec: z.number().nonnegative().optional(),
    last_error: z.string().optional(),
  }),
  storage: z.object({
    sqlite_path: z.string(),
    vector_index_path: z.string(),
    router_artifact_path: z.string(),
    response_policy_path: z.string(),
    trace_dir: z.string(),
  }),
});

export const MemoryNodeSummarySchema = z.object({
  id: z.string(),
  content: z.string(),
  confidence: z.number(),
  source: z.string(),
});

export const MemoryRecallResponseSchema = z.array(MemoryNodeSummarySchema);

export const ExpertsStatusSchema = z.object({
  loaded: z.array(z.string()),
  count: z.number().int().nonnegative(),
});

export type QueryRequest = z.infer<typeof QueryRequestSchema>;
export type LegacyQueryRequest = z.infer<typeof LegacyQueryRequestSchema>;
export type WsQueryRequest = z.infer<typeof WsQueryRequestSchema>;
export type StreamMessage = z.infer<typeof StreamMessageSchema>;
export type HealthResponse = z.infer<typeof HealthResponseSchema>;
export type MemoryNodeSummary = z.infer<typeof MemoryNodeSummarySchema>;
export type ExpertsStatus = z.infer<typeof ExpertsStatusSchema>;
