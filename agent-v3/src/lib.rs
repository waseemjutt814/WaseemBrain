//! Agent v3 - Pure Rust Production Agent
//! 
//! Top-tier agent framework with real implementations.
//! No mocks, no fake data - everything executes for real.

pub mod agent;
pub mod actions;
pub mod config;
pub mod errors;
pub mod logging;
pub mod messaging;
pub mod runtime;
pub mod types;

pub use agent::{Agent, AgentHandle};
pub use actions::{Action, ActionExecutor, ActionResult};
pub use config::AgentConfig;
pub use errors::{AgentError, Result};
pub use messaging::{Message, MessageRole, MessageBus};
pub use types::*;
