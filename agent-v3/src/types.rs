//! Core types for Agent v3

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

/// Unique identifier for agents
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct AgentId(pub String);

impl AgentId {
    pub fn new() -> Self {
        Self(Uuid::new_v4().to_string())
    }
}

impl Default for AgentId {
    fn default() -> Self {
        Self::new()
    }
}

/// Unique identifier for sessions
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SessionId(pub String);

impl SessionId {
    pub fn new() -> Self {
        Self(Uuid::new_v4().to_string())
    }
}

impl Default for SessionId {
    fn default() -> Self {
        Self::new()
    }
}

/// Agent state enumeration
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AgentState {
    Initializing,
    Idle,
    Processing,
    Executing,
    Error,
    ShuttingDown,
    Shutdown,
}

impl std::fmt::Display for AgentState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AgentState::Initializing => write!(f, "initializing"),
            AgentState::Idle => write!(f, "idle"),
            AgentState::Processing => write!(f, "processing"),
            AgentState::Executing => write!(f, "executing"),
            AgentState::Error => write!(f, "error"),
            AgentState::ShuttingDown => write!(f, "shutting_down"),
            AgentState::Shutdown => write!(f, "shutdown"),
        }
    }
}

/// Context storage for agents
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct AgentContext {
    data: HashMap<String, String>,
}

impl AgentContext {
    pub fn new() -> Self {
        Self {
            data: HashMap::new(),
        }
    }

    pub fn set(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.data.insert(key.into(), value.into());
    }

    pub fn get(&self, key: &str) -> Option<&String> {
        self.data.get(key)
    }

    pub fn remove(&mut self, key: &str) -> Option<String> {
        self.data.remove(key)
    }

    pub fn clear(&mut self) {
        self.data.clear();
    }

    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }

    pub fn len(&self) -> usize {
        self.data.len()
    }

    pub fn to_hashmap(&self) -> HashMap<String, String> {
        self.data.clone()
    }
}

/// Session summary for exporting
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionSummary {
    pub agent_id: AgentId,
    pub session_id: SessionId,
    pub start_time: DateTime<Utc>,
    pub end_time: Option<DateTime<Utc>>,
    pub message_count: usize,
    pub action_count: usize,
    pub final_state: AgentState,
    pub context_snapshot: HashMap<String, String>,
}

/// Metrics for monitoring
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct AgentMetrics {
    pub messages_processed: u64,
    pub actions_executed: u64,
    pub actions_failed: u64,
    pub average_action_duration_ms: f64,
    pub errors_count: u64,
}

impl AgentMetrics {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn record_message(&mut self) {
        self.messages_processed += 1;
    }

    pub fn record_action(&mut self, duration_ms: f64, success: bool) {
        self.actions_executed += 1;
        if !success {
            self.actions_failed += 1;
        }
        // Update rolling average
        let total = self.actions_executed as f64;
        self.average_action_duration_ms = 
            (self.average_action_duration_ms * (total - 1.0) + duration_ms) / total;
    }

    pub fn record_error(&mut self) {
        self.errors_count += 1;
    }
}
