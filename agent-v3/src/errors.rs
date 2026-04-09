//! Error types for Agent v3

use thiserror::Error;

pub type Result<T> = std::result::Result<T, AgentError>;

/// Comprehensive error types for the agent
#[derive(Error, Debug, Clone)]
pub enum AgentError {
    #[error("Agent is not initialized")]
    NotInitialized,

    #[error("Agent is already running")]
    AlreadyRunning,

    #[error("Agent is shutdown")]
    Shutdown,

    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),

    #[error("Action execution failed: {0}")]
    ActionFailed(String),

    #[error("Action timed out after {0}s")]
    ActionTimeout(f64),

    #[error("Maximum action limit ({0}) reached")]
    ActionLimitExceeded(usize),

    #[error("IO error: {0}")]
    IoError(String),

    #[error("Command execution failed: {0}")]
    CommandError(String),

    #[error("HTTP request failed: {0}")]
    HttpError(String),

    #[error("File not found: {0}")]
    FileNotFound(String),

    #[error("Permission denied: {0}")]
    PermissionDenied(String),

    #[error("Serialization error: {0}")]
    SerializationError(String),

    #[error("Message processing failed: {0}")]
    MessageProcessingError(String),

    #[error("Invalid state transition from {from} to {to}")]
    InvalidStateTransition { from: String, to: String },

    #[error("Context key not found: {0}")]
    ContextKeyNotFound(String),

    #[error("External service error: {0}")]
    ExternalServiceError(String),

    #[error("Unknown error: {0}")]
    Unknown(String),
}

impl AgentError {
    /// Check if this error is recoverable
    pub fn is_recoverable(&self) -> bool {
        matches!(
            self,
            AgentError::ActionTimeout(_) |
            AgentError::HttpError(_) |
            AgentError::ExternalServiceError(_)
        )
    }

    /// Get error severity level
    pub fn severity(&self) -> ErrorSeverity {
        match self {
            AgentError::NotInitialized |
            AgentError::Shutdown |
            AgentError::InvalidConfig(_) => ErrorSeverity::Fatal,
            
            AgentError::ActionFailed(_) |
            AgentError::ActionTimeout(_) |
            AgentError::CommandError(_) |
            AgentError::HttpError(_) |
            AgentError::FileNotFound(_) |
            AgentError::PermissionDenied(_) => ErrorSeverity::Error,
            
            AgentError::ActionLimitExceeded(_) |
            AgentError::IoError(_) |
            AgentError::ExternalServiceError(_) => ErrorSeverity::Warning,
            
            _ => ErrorSeverity::Info,
        }
    }
}

/// Error severity levels
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorSeverity {
    Fatal,
    Error,
    Warning,
    Info,
}

impl std::fmt::Display for ErrorSeverity {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ErrorSeverity::Fatal => write!(f, "FATAL"),
            ErrorSeverity::Error => write!(f, "ERROR"),
            ErrorSeverity::Warning => write!(f, "WARN"),
            ErrorSeverity::Info => write!(f, "INFO"),
        }
    }
}

/// Convert standard IO errors
impl From<std::io::Error> for AgentError {
    fn from(err: std::io::Error) -> Self {
        match err.kind() {
            std::io::ErrorKind::NotFound => {
                AgentError::FileNotFound(err.to_string())
            }
            std::io::ErrorKind::PermissionDenied => {
                AgentError::PermissionDenied(err.to_string())
            }
            _ => AgentError::IoError(err.to_string()),
        }
    }
}

/// Convert serialization errors
impl From<serde_json::Error> for AgentError {
    fn from(err: serde_json::Error) -> Self {
        AgentError::SerializationError(err.to_string())
    }
}

/// Convert HTTP errors
impl From<reqwest::Error> for AgentError {
    fn from(err: reqwest::Error) -> Self {
        AgentError::HttpError(err.to_string())
    }
}

/// Convert anyhow errors
impl From<anyhow::Error> for AgentError {
    fn from(err: anyhow::Error) -> Self {
        AgentError::Unknown(err.to_string())
    }
}
