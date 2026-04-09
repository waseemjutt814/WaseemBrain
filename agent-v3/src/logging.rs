//! Logging infrastructure for Agent v3

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use tracing::{debug, error, info, trace, warn};

/// Log levels
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum LogLevel {
    Trace,
    Debug,
    Info,
    Warn,
    Error,
}

impl std::fmt::Display for LogLevel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LogLevel::Trace => write!(f, "TRACE"),
            LogLevel::Debug => write!(f, "DEBUG"),
            LogLevel::Info => write!(f, "INFO"),
            LogLevel::Warn => write!(f, "WARN"),
            LogLevel::Error => write!(f, "ERROR"),
        }
    }
}

/// Log entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub timestamp: DateTime<Utc>,
    pub level: LogLevel,
    pub target: String,
    pub message: String,
    pub metadata: Option<serde_json::Value>,
}

impl LogEntry {
    /// Create a new log entry
    pub fn new(level: LogLevel, target: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            timestamp: Utc::now(),
            level,
            target: target.into(),
            message: message.into(),
            metadata: None,
        }
    }

    /// Add metadata
    pub fn with_metadata(mut self, metadata: impl Serialize) -> Self {
        self.metadata = serde_json::to_value(metadata).ok();
        self
    }

    /// Format for display
    pub fn format(&self) -> String {
        let meta = self.metadata.as_ref()
            .map(|m| format!(" {:?}", m))
            .unwrap_or_default();
        
        format!(
            "[{}] [{}] [{}] {}{}",
            self.timestamp.format("%Y-%m-%d %H:%M:%S%.3f"),
            self.level,
            self.target,
            self.message,
            meta
        )
    }
}

/// Logger for agents
pub struct AgentLogger {
    agent_id: String,
    entries: VecDeque<LogEntry>,
    max_entries: usize,
    min_level: LogLevel,
}

impl AgentLogger {
    /// Create a new logger
    pub fn new(agent_id: impl Into<String>, max_entries: usize, min_level: LogLevel) -> Self {
        Self {
            agent_id: agent_id.into(),
            entries: VecDeque::with_capacity(max_entries),
            max_entries,
            min_level,
        }
    }

    /// Log a message
    pub fn log(&mut self, level: LogLevel, message: impl Into<String>) {
        if level < self.min_level {
            return;
        }

        let entry = LogEntry::new(
            level,
            format!("agent-{}", self.agent_id),
            message,
        );

        // Store in buffer
        if self.entries.len() >= self.max_entries {
            self.entries.pop_front();
        }
        self.entries.push_back(entry.clone());

        // Output to tracing
        let msg = entry.message.clone();
        match level {
            LogLevel::Trace => trace!("{}", msg),
            LogLevel::Debug => debug!("{}", msg),
            LogLevel::Info => info!("{}", msg),
            LogLevel::Warn => warn!("{}", msg),
            LogLevel::Error => error!("{}", msg),
        }
    }

    /// Log at trace level
    pub fn trace(&mut self, message: impl Into<String>) {
        self.log(LogLevel::Trace, message);
    }

    /// Log at debug level
    pub fn debug(&mut self, message: impl Into<String>) {
        self.log(LogLevel::Debug, message);
    }

    /// Log at info level
    pub fn info(&mut self, message: impl Into<String>) {
        self.log(LogLevel::Info, message);
    }

    /// Log at warn level
    pub fn warn(&mut self, message: impl Into<String>) {
        self.log(LogLevel::Warn, message);
    }

    /// Log at error level
    pub fn error(&mut self, message: impl Into<String>) {
        self.log(LogLevel::Error, message);
    }

    /// Get all entries
    pub fn get_entries(&self) -> Vec<LogEntry> {
        self.entries.iter().cloned().collect()
    }

    /// Get recent entries
    pub fn get_recent(&self, count: usize) -> Vec<LogEntry> {
        self.entries
            .iter()
            .rev()
            .take(count)
            .cloned()
            .collect()
    }

    /// Get entries by level
    pub fn get_by_level(&self, level: LogLevel) -> Vec<LogEntry> {
        self.entries
            .iter()
            .filter(|e| e.level == level)
            .cloned()
            .collect()
    }

    /// Export to JSON
    pub fn export_json(&self) -> String {
        serde_json::to_string_pretty(&self.get_entries())
            .unwrap_or_else(|_| "[]".to_string())
    }

    /// Clear all entries
    pub fn clear(&mut self) {
        self.entries.clear();
    }

    /// Get entry count
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

/// Initialize global tracing subscriber
pub fn init_tracing(level: &str) {
    use tracing_subscriber::{fmt, prelude::*, EnvFilter};

    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(level));

    fmt::layer()
        .with_target(true)
        .with_thread_ids(true)
        .with_thread_names(true)
        .with_filter(filter)
        .init();
}
