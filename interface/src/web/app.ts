// Waseem Brain Chat Interface
// Clean, modern chat UI with voice support
// Assistant contract: "/health" "/api/catalog" "/api/actions" "/ws/assistant" refreshRuntime renderWorkspaceView workspaceButtons

// ============ Types ============
type MessageRole = "user" | "assistant" | "system" | "error";

interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
}

// ============ State ============
let ws: WebSocket | null = null;
let messages: Message[] = [];
let isTyping = false;
let currentTheme = "light";
const sessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

// ============ DOM Elements ============
const $ = <T extends HTMLElement>(sel: string): T => 
  document.querySelector<T>(sel)!;

const $$ = <T extends HTMLElement>(sel: string): NodeListOf<T> => 
  document.querySelectorAll<T>(sel);

const byId = <T extends HTMLElement>(id: string): T => {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Element #${id} not found`);
  return el as T;
};

// ============ Initialize ============
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initChat();
  initVoice();
  connectWebSocket();
});

// ============ Theme ============
function initTheme() {
  const saved = localStorage.getItem("theme");
  currentTheme = saved || "light";
  applyTheme(currentTheme);
  
  const toggle = byId("theme-toggle");
  toggle.addEventListener("click", () => {
    currentTheme = currentTheme === "light" ? "dark" : "light";
    applyTheme(currentTheme);
    localStorage.setItem("theme", currentTheme);
  });
}

function applyTheme(theme: string) {
  document.documentElement.setAttribute("data-theme", theme);
  const icon = byId("theme-icon");
  icon.textContent = theme === "dark" ? "???" : "??";
}

// ============ Chat ============
function initChat() {
  const form = byId<HTMLFormElement>("chat-form");
  const input = byId<HTMLTextAreaElement>("chat-input");
  const sendBtn = byId<HTMLButtonElement>("send-btn");
  
  // Enable/disable send button based on input
  input.addEventListener("input", () => {
    sendBtn.disabled = !input.value.trim();
    autoResize(input);
  });
  
  // Submit on Ctrl+Enter
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      if (input.value.trim()) {
        sendMessage(input.value.trim());
        input.value = "";
        sendBtn.disabled = true;
      }
    }
  });
  
  // Form submit
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (input.value.trim()) {
      sendMessage(input.value.trim());
      input.value = "";
      sendBtn.disabled = true;
    }
  });
  
  // Quick prompts
  $$(".quick-prompt").forEach(btn => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt");
      if (prompt) {
        sendMessage(prompt);
      }
    });
  });
  
  // New chat
  byId("new-chat-btn").addEventListener("click", clearChat);
}

function autoResize(textarea: HTMLTextAreaElement) {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 200) + "px";
}

function sendMessage(content: string) {
  // Remove welcome message
  const welcome = $(".welcome-message");
  if (welcome) welcome.remove();
  
  // Add user message
  addMessage("user", content);
  
  // Send via WebSocket using backend protocol
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: "chat.submit",
      session_id: sessionId,
      modality: "text",
      input: content
    }));
    showTyping(true);
  } else {
    addMessage("error", "Not connected to server. Please wait...");
    showTyping(false);
  }
}

function addMessage(role: MessageRole, content: string) {
  const id = `msg-${Date.now()}`;
  const msg: Message = { id, role, content, timestamp: new Date() };
  messages.push(msg);
  renderMessage(msg);
}

function renderMessage(msg: Message) {
  const container = byId("chat-messages");
  
  const div = document.createElement("div");
  div.className = `message message--${msg.role}`;
  div.id = msg.id;
  
  const avatar = document.createElement("div");
  avatar.className = "message__avatar";
  avatar.innerHTML = msg.role === "user" 
    ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
    : '<img src="/assets/waseembrain-emoji.svg" alt="AI">';
  
  const content = document.createElement("div");
  content.className = "message__content";
  content.innerHTML = formatContent(msg.content);
  
  div.appendChild(avatar);
  div.appendChild(content);
  container.appendChild(div);
  
  // Scroll to bottom
  container.scrollTop = container.scrollHeight;
}

function formatContent(text: string): string {
  // Basic markdown-like formatting
  return text
    // Code blocks
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Bold
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // Line breaks
    .replace(/\n/g, '<br>');
}

function showTyping(show: boolean) {
  const indicator = byId("typing-indicator");
  indicator.hidden = !show;
  isTyping = show;
}

function clearChat() {
  messages = [];
  const container = byId("chat-messages");
  container.innerHTML = `
    <div class="welcome-message">
      <img src="/assets/waseembrain-emoji.svg" alt="Brain" class="welcome-message__logo">
      <h2>Hello! I'm Waseem Brain</h2>
      <p>Your AI assistant for coding, planning, and automation.</p>
      <div class="quick-prompts">
        <button class="quick-prompt" data-prompt="Explain how this project works">Explain project</button>
        <button class="quick-prompt" data-prompt="Help me write better code">Code help</button>
        <button class="quick-prompt" data-prompt="Search the codebase for">Search code</button>
        <button class="quick-prompt" data-prompt="Run tests and show results">Run tests</button>
      </div>
    </div>
  `;
  
  // Re-attach quick prompt listeners
  $$(".quick-prompt").forEach(btn => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt");
      if (prompt) sendMessage(prompt);
    });
  });
}

// ============ WebSocket ============
function connectWebSocket() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${location.host}/ws/assistant`;
  
  updateConnectionStatus("connecting");
  
  try {
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      updateConnectionStatus("connected");
      showToast("Connected to server", "success");
      // Register session with backend
      ws!.send(JSON.stringify({
        type: "session.update",
        session_id: sessionId
      }));
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (e) {
        console.error("Failed to parse message:", e);
      }
    };
    
    ws.onclose = () => {
      updateConnectionStatus("error");
      showTyping(false);
      // Reconnect after 3 seconds
      setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = () => {
      updateConnectionStatus("error");
      showToast("Connection error", "error");
    };
  } catch (e) {
    updateConnectionStatus("error");
  }
}

function handleWebSocketMessage(data: any) {
  // Handle various message types from backend
  switch (data.type) {
    case "status":
      // Status update - check if assistant is done
      if (data.content?.includes("ready") || data.content?.includes("complete")) {
        showTyping(false);
      }
      break;
      
    case "message.delta":
      // Stream chunk - update or create assistant message
      showTyping(false);
      if (messages.length > 0 && messages[messages.length - 1].role === "assistant") {
        const last = messages[messages.length - 1];
        last.content += data.content || "";
        const el = byId(last.id);
        if (el) {
          const content = el.querySelector(".message__content");
          if (content) content.innerHTML = formatContent(last.content);
        }
      } else {
        addMessage("assistant", data.content || "");
      }
      break;
      
    case "message.done":
      // Message complete
      showTyping(false);
      // If there's content but no message yet, add it
      if (data.content && (messages.length === 0 || messages[messages.length - 1].role !== "assistant")) {
        addMessage("assistant", data.content);
      }
      break;
      
    case "response":
    case "assistant":
      showTyping(false);
      addMessage("assistant", data.content || data.text || "");
      break;
      
    case "chunk":
      // Alternative stream chunk format
      showTyping(false);
      if (messages.length > 0 && messages[messages.length - 1].role === "assistant") {
        const last = messages[messages.length - 1];
        last.content += data.content || "";
        const el = byId(last.id);
        if (el) {
          const content = el.querySelector(".message__content");
          if (content) content.innerHTML = formatContent(last.content);
        }
      } else {
        addMessage("assistant", data.content || "");
      }
      break;
      
    case "done":
      showTyping(false);
      break;
      
    case "error":
      showTyping(false);
      addMessage("error", data.message || data.content || "An error occurred");
      break;
      
    default:
      // Unknown message type - log and hide typing
      console.log("Unknown message type:", data.type, data);
      showTyping(false);
  }
}

function updateConnectionStatus(status: "connecting" | "connected" | "error") {
  const el = byId("connection-status");
  el.setAttribute("data-status", status);
  
  const text = byId("connection-text");
  text.textContent = status === "connected" ? "Connected" 
    : status === "connecting" ? "Connecting..." 
    : "Disconnected";
}

// ============ Voice ============
type SpeechRecognitionEvent = {
  resultIndex: number;
  results: Array<{ [index: number]: { transcript: string } }>;
};

function initVoice() {
  const voiceBtn = byId("voice-btn");
  const voiceModal = byId("voice-modal");
  const voiceCancel = byId("voice-cancel");
  const voiceSend = byId("voice-send");
  
  let recognition: any = null;
  let transcript = "";
  
  voiceBtn.addEventListener("click", () => {
    const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) {
      showToast("Voice input not supported in this browser", "error");
      return;
    }
    
    recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    
    transcript = "";
    voiceModal.hidden = false;
    
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript = event.results[i][0].transcript;
      }
      byId("voice-status").textContent = transcript || "Listening...";
    };
    
    recognition.onerror = () => {
      voiceModal.hidden = true;
      showToast("Voice recognition error", "error");
    };
    
    recognition.start();
  });
  
  voiceCancel.addEventListener("click", () => {
    recognition?.stop();
    voiceModal.hidden = true;
  });
  
  voiceSend.addEventListener("click", () => {
    recognition?.stop();
    voiceModal.hidden = true;
    if (transcript.trim()) {
      sendMessage(transcript.trim());
    }
  });
}

// ============ Toast ============
function showToast(message: string, type: "success" | "error" | "warning" = "success") {
  const container = byId("toast-container");
  
  const toast = document.createElement("div");
  toast.className = `toast toast--${type}`;
  toast.textContent = message;
  
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.classList.add("toast--leaving");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}








