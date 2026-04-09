//! Agent configuration

use crate::errors::{AgentError, Result};
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Agent configuration with sensible defaults
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfig {
    /// Agent identifier
    pub id: String,
    
    /// Human-readable name
    pub name: String,
    
    /// Version string
    pub version: String,
    
    /// Maximum actions per session
    pub max_actions: usize,
    
    /// Default timeout for actions
    #[serde(with = "serde_duration")]
    pub action_timeout: Duration,
    
    /// Enable thinking/reasoning steps
    pub enable_thinking: bool,
    
    /// Working directory for file operations
    pub working_dir: String,
    
    /// Log level (trace, debug, info, warn, error)
    pub log_level: String,
    
    /// Maximum message history
    pub max_message_history: usize,
    
    /// Enable metrics collection
    pub enable_metrics: bool,
    
    /// HTTP request timeout
    #[serde(with = "serde_duration")]
    pub http_timeout: Duration,
    
    /// Maximum file size to read (bytes)
    pub max_file_size: usize,
    
    /// Allowed commands (empty = all allowed)
    pub allowed_commands: Vec<String>,
    
    /// Blocked commands (security)
    pub blocked_commands: Vec<String>,
}

impl Default for AgentConfig {
    fn default() -> Self {
        Self {
            id: format!("agent-v3-{}", uuid::Uuid::new_v4()),
            name: "Agent v3".to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
            max_actions: 1000,
            action_timeout: Duration::from_secs(120),
            enable_thinking: true,
            working_dir: ".".to_string(),
            log_level: "info".to_string(),
            max_message_history: 1000,
            enable_metrics: true,
            http_timeout: Duration::from_secs(30),
            max_file_size: 10 * 1024 * 1024, // 10MB
            allowed_commands: vec![],
            blocked_commands: vec![
                "rm -rf /".to_string(),
                "format".to_string(),
                "mkfs".to_string(),
                "dd".to_string(),
            ],
        }
    }
}

impl AgentConfig {
    /// Create a new configuration with defaults
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            ..Default::default()
        }
    }

    /// Validate the configuration
    pub fn validate(&self) -> Result<()> {
        if self.id.is_empty() {
            return Err(AgentError::InvalidConfig("Agent ID cannot be empty".to_string()));
        }
        
        if self.name.is_empty() {
            return Err(AgentError::InvalidConfig("Agent name cannot be empty".to_string()));
        }
        
        if self.max_actions == 0 {
            return Err(AgentError::InvalidConfig("max_actions must be > 0".to_string()));
        }
        
        if self.action_timeout.is_zero() {
            return Err(AgentError::InvalidConfig("action_timeout must be > 0".to_string()));
        }

        Ok(())
    }

    /// Builder pattern: set ID
    pub fn with_id(mut self, id: impl Into<String>) -> Self {
        self.id = id.into();
        self
    }

    /// Builder pattern: set max actions
    pub fn with_max_actions(mut self, max: usize) -> Self {
        self.max_actions = max;
        self
    }

    /// Builder pattern: set timeout
    pub fn with_timeout(mut self, secs: u64) -> Self {
        self.action_timeout = Duration::from_secs(secs);
        self
    }

    /// Builder pattern: set working directory
    pub fn with_working_dir(mut self, dir: impl Into<String>) -> Self {
        self.working_dir = dir.into();
        self
    }

    /// Builder pattern: disable thinking
    pub fn without_thinking(mut self) -> Self {
        self.enable_thinking = false;
        self
    }

    /// Load from file
    pub fn from_file(path: &str) -> Result<Self> {
        let content = std::fs::read_to_string(path)
            .map_err(|e| AgentError::IoError(format!("Failed to read config: {}", e)))?;
        
        let config: AgentConfig = toml::from_str(&content)
            .map_err(|e| AgentError::SerializationError(format!("Failed to parse config: {}", e)))?;
        
        config.validate()?;
        Ok(config)
    }

    /// Save to file
    pub fn save_to_file(&self, path: &str) -> Result<()> {
        let content = toml::to_string_pretty(self)
            .map_err(|e| AgentError::SerializationError(e.to_string()))?;
        
        std::fs::write(path, content)
            .map_err(|e| AgentError::IoError(e.to_string()))?;
        
        Ok(())
    }
}

/// Serde helper for Duration
mod serde_duration {
    use serde::{Deserialize, Deserializer, Serializer};
    use std::time::Duration;

    pub fn serialize<S: Serializer>(duration: &Duration, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_u64(duration.as_secs())
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(deserializer: D) -> Result<Duration, D::Error> {
        let secs = u64::deserialize(deserializer)?;
        Ok(Duration::from_secs(secs))
    }
}
