export type ShellMode = "text" | "url" | "file" | "voice";
export type ConnectionState = "checking" | "ready" | "busy" | "error";
export type DetailPanel = "overview" | "api" | "skills" | "actions" | "memory" | "settings";

export interface UploadSelection {
  fileName: string;
  mimeType: string;
  size: number;
}

export interface RecordingSelection extends UploadSelection {
  durationMs: number;
}

export interface SubmissionContext {
  mode: ShellMode;
  textInput: string;
  urlInput: string;
  file: UploadSelection | null;
  recording: RecordingSelection | null;
}

export type ValidationResult = { ok: true; summary: string } | { ok: false; error: string };

export interface StreamRenderState {
  content: string;
  error: string | null;
  completed: boolean;
}

export interface DashboardSettings {
  autoRefresh: boolean;
  autoSendVoice: boolean;
  speakReplies: boolean;
}

export interface RuntimeLocationLike {
  protocol: string;
  host: string;
  hostname: string;
}

export interface RuntimeUrls {
  baseUrl: string;
  websocketUrl: string;
  assistantWsUrl: string;
}

export interface CitationPayload {
  id: string;
  source_type: string;
  label: string;
  snippet: string;
  uri: string;
}

export interface HealthPayload {
  status: "ok";
  project_name: string;
  condition: "strong" | "ready" | "attention";
  condition_summary: string;
  ready: boolean;
  experts_loaded: number;
  experts_available: number;
  expert_ids: string[];
  memory_node_count: number;
  uptime_sec: number;
  router_backend: string;
  vector_backend: string;
  components: Record<string, string>;
  capabilities: {
    model_free_core: boolean;
    api_key_required: boolean;
    self_improvement_scope: string;
    router_acceleration_optional: boolean;
    default_router_backend: string;
  };
  learning: {
    enabled: boolean;
    backend: string;
    response_policy: string;
    trace_files: number;
    trace_turns: number;
    expert_trace_files: number;
    expert_trace_turns: number;
    training_jobs: number;
    datasets: number;
    trained_trace_count: number;
    last_event: string;
    phase: string;
  };
  knowledge: {
    status: string;
    datasets: number;
    cards: number;
    seeded_cards: number;
    seeded_this_run: number;
    source_dir: string;
    version: string;
    dataset_ids: string[];
    last_seeded_at: number;
    note: string;
  };
  router: {
    mode: string;
    artifact: string;
    target: string;
    daemon_state: string;
    pid?: number;
    port?: number;
    uptime_sec?: number;
    last_error?: string;
  };
  storage: {
    sqlite_path: string;
    vector_index_path: string;
    router_artifact_path: string;
    response_policy_path: string;
    trace_dir: string;
  };
  assistant_mode: string;
  provider: {
    configured: boolean;
    mode: "local_grounded" | "openai_compatible";
    model: string;
    reachable: boolean;
  };
  realtime_voice: {
    supported: boolean;
    mode: string;
  };
  automation: {
    approval_required: boolean;
    audit_enabled: boolean;
  };
}

export interface MemoryNodeSummary {
  id: string;
  content: string;
  confidence: number;
  source: string;
}

export interface ExpertsPayload {
  loaded: string[];
  count: number;
}

export interface IntegrationEndpointPayload {
  id: string;
  method: "GET" | "POST" | "WS";
  path: string;
  summary: string;
  request_format: string;
  response_format: string;
}

export interface IntegrationCatalogPayload {
  project_name: string;
  api_style: string;
  auth: string;
  local_only_default: boolean;
  openai_compatible: boolean;
  websocket_path: string;
  default_surface: string;
  conversation_modes: string[];
  voice_modes: string[];
  structured_session_ws_path: string;
  notes: string[];
  endpoints: IntegrationEndpointPayload[];
}

export interface ActionInputPayload {
  id: string;
  label: string;
  kind: "text" | "number" | "choice";
  required: boolean;
  placeholder: string;
  options?: string[];
}

export interface ActionDescriptorPayload {
  id: string;
  label: string;
  description: string;
  risk: "low" | "medium" | "high";
  read_only: boolean;
  category: string;
  required_inputs: ActionInputPayload[];
  confirmation_required: boolean;
}

export interface ActionGroupPayload {
  id: string;
  label: string;
  actions: ActionDescriptorPayload[];
}

export interface ActionCatalogPayload {
  groups: ActionGroupPayload[];
}

export function actionNeedsPreview(
  action: Pick<ActionDescriptorPayload, "confirmation_required"> | null,
): boolean {
  return Boolean(action?.confirmation_required);
}

export interface AssistantMetadataPayload {
  route: string;
  provider: HealthPayload["provider"];
  tools: string[];
  citations_count: number;
  render_strategy: string;
  transcript: string;
  local_mode: boolean;
}

export interface AssistantEventPayload {
  type:
    | "status"
    | "transcript.partial"
    | "message.delta"
    | "message.done"
    | "tool.start"
    | "tool.result"
    | "evidence"
    | "approval.required"
    | "error";
  content?: string;
  tool?: string;
  route?: string;
  citations?: CitationPayload[];
  descriptor?: ActionDescriptorPayload;
  preview?: {
    action_id: string;
    summary: string;
    command_preview: string;
    risk: "low" | "medium" | "high";
    inputs: Record<string, string>;
  };
  metadata?: AssistantMetadataPayload;
}

export interface HealthViewModel {
  title: string;
  summary: string;
  providerLabel: string;
  voiceLabel: string;
  automationLabel: string;
  expertsLabel: string;
  memoryLabel: string;
  routeLabel: string;
  capabilities: string[];
}

export const DEFAULT_SETTINGS: DashboardSettings = {
  autoRefresh: true,
  autoSendVoice: true,
  speakReplies: true,
};

export function buildSessionId(randomValue: number = Math.random()): string {
  return `web-${randomValue.toString(36).slice(2, 10)}`;
}

export function panelLabel(panel: DetailPanel): string {
  switch (panel) {
    case "overview":
      return "Overview";
    case "api":
      return "API";
    case "skills":
      return "Skills";
    case "actions":
      return "Actions";
    case "memory":
      return "Memory";
    case "settings":
      return "Settings";
  }
}

export function modeLabel(mode: ShellMode): string {
  switch (mode) {
    case "text":
      return "Chat";
    case "url":
      return "URL";
    case "file":
      return "Document";
    case "voice":
      return "Live Talk";
  }
}

export function routeForMode(mode: ShellMode): string {
  switch (mode) {
    case "text":
      return "/query/text";
    case "url":
      return "/query/url";
    case "file":
      return "/query/file";
    case "voice":
      return "/query/voice";
  }
}

export function buildConnectionLabel(state: ConnectionState, detail = ""): string {
  const suffix = detail ? `: ${detail}` : "";
  switch (state) {
    case "checking":
      return `Checking runtime${suffix}`;
    case "ready":
      return detail || "Runtime ready";
    case "busy":
      return detail || "Assistant is working";
    case "error":
      return detail ? `Runtime unavailable: ${detail}` : "Runtime unavailable";
  }
}

export function formatBytes(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function summariseUpload(upload: UploadSelection): string {
  return `${upload.fileName} / ${formatBytes(upload.size)} / ${upload.mimeType || "unknown type"}`;
}

export function buildRuntimeUrls(locationLike: RuntimeLocationLike, websocketPath: string = "/ws"): RuntimeUrls {
  const baseUrl = `${locationLike.protocol}//${locationLike.host}`;
  const normalizedWsPath = websocketPath.startsWith("/") ? websocketPath : `/${websocketPath}`;
  const websocketProtocol = locationLike.protocol === "https:" ? "wss:" : "ws:";
  return {
    baseUrl,
    websocketUrl: `${websocketProtocol}//${locationLike.host}${normalizedWsPath}`,
    assistantWsUrl: `${websocketProtocol}//${locationLike.host}/ws/assistant`,
  };
}

export function describeAccessMode(hostname: string, localOnlyDefault: boolean): string {
  const normalized = hostname.trim().toLowerCase();
  if (normalized === "127.0.0.1" || normalized === "localhost") {
    return "Local only on this machine";
  }
  if (localOnlyDefault) {
    return `Local-first on ${hostname}`;
  }
  return `Reachable from other devices on ${hostname}`;
}

export function buildCatalogSummary(catalog: IntegrationCatalogPayload, baseUrl: string): string {
  return `${catalog.project_name} runs on ${baseUrl}. Structured assistant sessions use ${catalog.structured_session_ws_path}; compatibility REST routes remain available for direct tool integrations.`;
}

export function buildHealthCurl(baseUrl: string): string {
  return `curl.exe ${baseUrl}/health`;
}

export function buildTextCurl(baseUrl: string, sessionId: string, prompt = "hello from another local tool"): string {
  const payload = JSON.stringify({ modality: "text", input: prompt, session_id: sessionId }).replaceAll("'", "''");
  return `curl.exe -X POST ${baseUrl}/query/text -H "Content-Type: application/json" -d '${payload}'`;
}

export function validateSubmission(context: SubmissionContext): ValidationResult {
  if (context.mode === "text") {
    const value = context.textInput.trim();
    if (!value) {
      return { ok: false, error: "Write a message before sending chat." };
    }
    return { ok: true, summary: value };
  }
  if (context.mode === "url") {
    const value = context.urlInput.trim();
    if (!value) {
      return { ok: false, error: "Paste a URL before using the URL tool." };
    }
    try {
      return { ok: true, summary: new URL(value).toString() };
    } catch {
      return { ok: false, error: "Enter a valid absolute URL." };
    }
  }
  if (context.mode === "file") {
    if (!context.file) {
      return { ok: false, error: "Choose a file before using the document tool." };
    }
    return { ok: true, summary: `Document tool: ${summariseUpload(context.file)}` };
  }
  if (!context.recording) {
    return { ok: false, error: "Start talking before using live talk." };
  }
  const seconds = Math.max(context.recording.durationMs / 1000, 0.1).toFixed(1);
  return { ok: true, summary: `Live talk turn: ${seconds}s / ${formatBytes(context.recording.size)}` };
}

export function createStreamRenderState(): StreamRenderState {
  return { content: "", error: null, completed: false };
}

export function appendStreamChunk(state: StreamRenderState, chunk: string): StreamRenderState {
  if (chunk.startsWith("[stream-error]")) {
    return { ...state, error: chunk.replace("[stream-error]", "").trim() };
  }
  return { ...state, content: `${state.content}${chunk}` };
}

export function completeStream(state: StreamRenderState): StreamRenderState {
  return { ...state, completed: true };
}

export function failStream(state: StreamRenderState, error: string): StreamRenderState {
  return { ...state, error, completed: true };
}

export function toHealthViewModel(payload: HealthPayload): HealthViewModel {
  const providerLabel = payload.provider.configured
    ? `${payload.provider.mode} / ${payload.provider.model} / ${payload.provider.reachable ? "reachable" : "offline"}`
    : "Local grounded mode";
  return {
    title: `${payload.project_name} / ${payload.condition}`,
    summary: payload.condition_summary,
    providerLabel,
    voiceLabel: payload.realtime_voice.supported ? payload.realtime_voice.mode : "not available",
    automationLabel: payload.automation.approval_required ? "Approval required" : "direct execution",
    expertsLabel: `${payload.experts_loaded}/${payload.experts_available} experts active`,
    memoryLabel: `${payload.memory_node_count} memory nodes`,
    routeLabel: `${payload.assistant_mode} assistant mode`,
    capabilities: [
      payload.capabilities.model_free_core ? "Model-free local core" : "External core required",
      payload.automation.audit_enabled ? "Audit logging on" : "Audit logging off",
      payload.provider.configured ? `Provider: ${payload.provider.model}` : "Provider not configured",
    ],
  };
}

