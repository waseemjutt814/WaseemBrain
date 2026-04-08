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

export const CitationSchema = z.object({
  id: z.string(),
  source_type: z.string(),
  label: z.string(),
  snippet: z.string(),
  uri: z.string(),
});

export const ProviderStatusSchema = z.object({
  configured: z.boolean(),
  mode: z.enum(["local_grounded", "openai_compatible"]),
  model: z.string(),
  reachable: z.boolean(),
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
  capabilities: z.object({
    model_free_core: z.boolean(),
    api_key_required: z.boolean(),
    self_improvement_scope: z.string(),
    router_acceleration_optional: z.boolean(),
    default_router_backend: z.string(),
  }),
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
  assistant_mode: z.string(),
  provider: ProviderStatusSchema,
  realtime_voice: z.object({
    supported: z.boolean(),
    mode: z.string(),
  }),
  automation: z.object({
    approval_required: z.boolean(),
    audit_enabled: z.boolean(),
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

export const IntegrationEndpointSchema = z.object({
  id: z.string(),
  method: z.enum(["GET", "POST", "WS"]),
  path: z.string(),
  summary: z.string(),
  request_format: z.string(),
  response_format: z.string(),
});

export const IntegrationCatalogSchema = z.object({
  project_name: z.string(),
  api_style: z.string(),
  auth: z.string(),
  local_only_default: z.boolean(),
  openai_compatible: z.boolean(),
  websocket_path: z.string(),
  default_surface: z.string(),
  conversation_modes: z.array(z.string()),
  voice_modes: z.array(z.string()),
  structured_session_ws_path: z.string(),
  notes: z.array(z.string()),
  endpoints: z.array(IntegrationEndpointSchema),
});

export const ActionInputSchema = z.object({
  id: z.string(),
  label: z.string(),
  kind: z.enum(["text", "number", "choice"]),
  required: z.boolean(),
  placeholder: z.string(),
  options: z.array(z.string()).optional(),
});

export const ActionDescriptorSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string(),
  risk: z.enum(["low", "medium", "high"]),
  read_only: z.boolean(),
  category: z.string(),
  required_inputs: z.array(ActionInputSchema),
  confirmation_required: z.boolean(),
});

export const ActionGroupSchema = z.object({
  id: z.string(),
  label: z.string(),
  actions: z.array(ActionDescriptorSchema),
});

export const ActionCatalogSchema = z.object({
  groups: z.array(ActionGroupSchema),
});

export const AssistantMetadataSchema = z.object({
  route: z.string(),
  provider: ProviderStatusSchema,
  tools: z.array(z.string()),
  citations_count: z.number().int().nonnegative(),
  render_strategy: z.string(),
  transcript: z.string(),
  local_mode: z.boolean(),
});

export const AssistantChatSubmitSchema = z.object({
  type: z.literal("chat.submit"),
  session_id: z.string().min(1),
  modality: z.enum(["text", "url", "file"]).default("text"),
  input: z.string().optional(),
  input_base64: z.string().optional(),
  filename: z.string().optional(),
  mime_type: z.string().optional(),
});

export const AssistantVoiceStartSchema = z.object({
  type: z.literal("voice.start"),
  session_id: z.string().min(1),
});

export const AssistantVoiceChunkSchema = z.object({
  type: z.literal("voice.chunk"),
  session_id: z.string().min(1),
  chunk_base64: z.string().min(1),
});

export const AssistantVoiceStopSchema = z.object({
  type: z.literal("voice.stop"),
  session_id: z.string().min(1),
  filename: z.string().default("voice.wav"),
  mime_type: z.string().default("audio/wav"),
});

export const AssistantActionPreviewSchema = z.object({
  type: z.literal("action.preview"),
  session_id: z.string().min(1),
  action_id: z.string().min(1),
  inputs: z.record(z.string()).default({}),
});

export const AssistantActionConfirmSchema = z.object({
  type: z.literal("action.confirm"),
  session_id: z.string().min(1),
  action_id: z.string().min(1),
  inputs: z.record(z.string()).default({}),
  confirmed: z.boolean(),
});

export const AssistantSessionUpdateSchema = z.object({
  type: z.literal("session.update"),
  session_id: z.string().min(1),
});

export const AssistantClientEventSchema = z.discriminatedUnion("type", [
  AssistantChatSubmitSchema,
  AssistantVoiceStartSchema,
  AssistantVoiceChunkSchema,
  AssistantVoiceStopSchema,
  AssistantActionPreviewSchema,
  AssistantActionConfirmSchema,
  AssistantSessionUpdateSchema,
]);

export const AssistantServerEventSchema = z.object({
  type: z.enum([
    "status",
    "transcript.partial",
    "message.delta",
    "message.done",
    "tool.start",
    "tool.result",
    "evidence",
    "approval.required",
    "error",
  ]),
  content: z.string().optional(),
  tool: z.string().optional(),
  route: z.string().optional(),
  citations: z.array(CitationSchema).optional(),
  descriptor: ActionDescriptorSchema.optional(),
  preview: z.object({
    action_id: z.string(),
    summary: z.string(),
    command_preview: z.string(),
    risk: z.enum(["low", "medium", "high"]),
    inputs: z.record(z.string()),
  }).optional(),
  metadata: AssistantMetadataSchema.optional(),
});

export type QueryRequest = z.infer<typeof QueryRequestSchema>;
export type LegacyQueryRequest = z.infer<typeof LegacyQueryRequestSchema>;
export type WsQueryRequest = z.infer<typeof WsQueryRequestSchema>;
export type StreamMessage = z.infer<typeof StreamMessageSchema>;
export type HealthResponse = z.infer<typeof HealthResponseSchema>;
export type MemoryNodeSummary = z.infer<typeof MemoryNodeSummarySchema>;
export type ExpertsStatus = z.infer<typeof ExpertsStatusSchema>;
export type IntegrationEndpoint = z.infer<typeof IntegrationEndpointSchema>;
export type IntegrationCatalog = z.infer<typeof IntegrationCatalogSchema>;
export type ActionDescriptor = z.infer<typeof ActionDescriptorSchema>;
export type ActionGroup = z.infer<typeof ActionGroupSchema>;
export type ActionCatalog = z.infer<typeof ActionCatalogSchema>;
export type AssistantClientEvent = z.infer<typeof AssistantClientEventSchema>;
export type AssistantServerEvent = z.infer<typeof AssistantServerEventSchema>;
