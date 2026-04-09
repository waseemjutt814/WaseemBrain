//! Messaging system for Agent v3

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use uuid::Uuid;

/// Message roles
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MessageRole {
    User,
    Assistant,
    System,
    Tool,
}

impl std::fmt::Display for MessageRole {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MessageRole::User => write!(f, "user"),
            MessageRole::Assistant => write!(f, "assistant"),
            MessageRole::System => write!(f, "system"),
            MessageRole::Tool => write!(f, "tool"),
        }
    }
}

/// Message structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub id: String,
    pub role: MessageRole,
    pub content: String,
    pub timestamp: DateTime<Utc>,
    pub metadata: serde_json::Value,
}

impl Message {
    /// Create a new message
    pub fn new(role: MessageRole, content: impl Into<String>) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            role,
            content: content.into(),
            timestamp: Utc::now(),
            metadata: serde_json::Value::Object(serde_json::Map::new()),
        }
    }

    /// Create a user message
    pub fn user(content: impl Into<String>) -> Self {
        Self::new(MessageRole::User, content)
    }

    /// Create an assistant message
    pub fn assistant(content: impl Into<String>) -> Self {
        Self::new(MessageRole::Assistant, content)
    }

    /// Create a system message
    pub fn system(content: impl Into<String>) -> Self {
        Self::new(MessageRole::System, content)
    }

    /// Create a tool message
    pub fn tool(content: impl Into<String>) -> Self {
        Self::new(MessageRole::Tool, content)
    }

    /// Add metadata
    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Serialize) -> Self {
        if let serde_json::Value::Object(ref mut map) = self.metadata {
            if let Ok(val) = serde_json::to_value(value) {
                map.insert(key.into(), val);
            }
        }
        self
    }

    /// Get content length
    pub fn content_len(&self) -> usize {
        self.content.len()
    }

    /// Check if content is empty
    pub fn is_empty(&self) -> bool {
        self.content.is_empty()
    }

    /// Format for display
    pub fn format(&self) -> String {
        format!(
            "[{}] {}: {}",
            self.timestamp.format("%Y-%m-%d %H:%M:%S"),
            self.role,
            if self.content.len() > 100 {
                format!("{}...", &self.content[..100])
            } else {
                self.content.clone()
            }
        )
    }
}

/// Message bus for handling message flow
#[derive(Debug, Clone)]
pub struct MessageBus {
    messages: VecDeque<Message>,
    max_size: usize,
}

impl MessageBus {
    /// Create a new message bus
    pub fn new(max_size: usize) -> Self {
        Self {
            messages: VecDeque::with_capacity(max_size),
            max_size,
        }
    }

    /// Add a message
    pub fn push(&mut self, message: Message) {
        if self.messages.len() >= self.max_size {
            self.messages.pop_front();
        }
        self.messages.push_back(message);
    }

    /// Get all messages
    pub fn get_all(&self) -> Vec<Message> {
        self.messages.iter().cloned().collect()
    }

    /// Get recent messages
    pub fn get_recent(&self, count: usize) -> Vec<Message> {
        self.messages
            .iter()
            .rev()
            .take(count)
            .cloned()
            .collect()
    }

    /// Get message count
    pub fn len(&self) -> usize {
        self.messages.len()
    }

    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.messages.is_empty()
    }

    /// Clear all messages
    pub fn clear(&mut self) {
        self.messages.clear();
    }

    /// Get the last message
    pub fn last(&self) -> Option<&Message> {
        self.messages.back()
    }

    /// Get the first message
    pub fn first(&self) -> Option<&Message> {
        self.messages.front()
    }

    /// Filter messages by role
    pub fn filter_by_role(&self, role: MessageRole) -> Vec<Message> {
        self.messages
            .iter()
            .filter(|m| m.role == role)
            .cloned()
            .collect()
    }

    /// Search messages by content
    pub fn search(&self, query: &str) -> Vec<Message> {
        self.messages
            .iter()
            .filter(|m| m.content.contains(query))
            .cloned()
            .collect()
    }
}

impl Default for MessageBus {
    fn default() -> Self {
        Self::new(1000)
    }
}
