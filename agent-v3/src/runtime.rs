//! Runtime for Agent v3
//! 
//! Manages the async runtime and provides utilities for running agents.

use crate::agent::{Agent, AgentHandle};
use crate::errors::Result;
use crate::logging::init_tracing;
use tracing::{info, warn};

/// Agent runtime - manages the tokio runtime
pub struct AgentRuntime;

impl AgentRuntime {
    /// Initialize and run an agent to completion
    pub fn run<F, Fut>(log_level: &str, f: F) 
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<()>>,
    {
        // Initialize tracing
        init_tracing(log_level);

        // Create and run tokio runtime
        let rt = tokio::runtime::Runtime::new()
            .expect("Failed to create Tokio runtime");

        rt.block_on(async {
            info!("Agent runtime starting");
            
            if let Err(e) = f().await {
                warn!("Agent execution failed: {}", e);
                std::process::exit(1);
            }
            
            info!("Agent runtime completed");
        });
    }

    /// Run with custom configuration
    pub fn run_with_threads<F, Fut>(log_level: &str, worker_threads: usize, f: F)
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<()>>,
    {
        init_tracing(log_level);

        let rt = tokio::runtime::Builder::new_multi_thread()
            .worker_threads(worker_threads)
            .enable_all()
            .build()
            .expect("Failed to create Tokio runtime");

        rt.block_on(async {
            info!("Agent runtime starting with {} threads", worker_threads);
            
            if let Err(e) = f().await {
                warn!("Agent execution failed: {}", e);
                std::process::exit(1);
            }
            
            info!("Agent runtime completed");
        });
    }
}

/// Utility functions for common agent operations
pub mod utils {
    use crate::actions::{Action, ActionResult};
    use crate::agent::AgentHandle;
    use crate::errors::Result;
    use crate::messaging::Message;

    /// Execute a command via agent
    pub async fn exec(agent: &AgentHandle, command: impl Into<String>, args: Vec<String>) -> Result<ActionResult> {
        agent.execute_action(Action::Execute {
            command: command.into(),
            args,
            working_dir: None,
            env_vars: vec![],
        }).await
    }

    /// Read file via agent
    pub async fn read_file(agent: &AgentHandle, path: impl Into<String>) -> Result<ActionResult> {
        agent.execute_action(Action::ReadFile {
            path: path.into(),
            limit_bytes: None,
        }).await
    }

    /// Write file via agent
    pub async fn write_file(agent: &AgentHandle, path: impl Into<String>, content: impl Into<String>) -> Result<ActionResult> {
        agent.execute_action(Action::WriteFile {
            path: path.into(),
            content: content.into(),
        }).await
    }

    /// HTTP GET via agent
    pub async fn http_get(agent: &AgentHandle, url: impl Into<String>) -> Result<ActionResult> {
        agent.execute_action(Action::HttpGet {
            url: url.into(),
            headers: vec![],
        }).await
    }

    /// Search files via agent
    pub async fn search(agent: &AgentHandle, pattern: impl Into<String>, directory: impl Into<String>) -> Result<ActionResult> {
        agent.execute_action(Action::SearchFiles {
            pattern: pattern.into(),
            directory: directory.into(),
            max_depth: None,
        }).await
    }

    /// Git command via agent
    pub async fn git(agent: &AgentHandle, subcommand: impl Into<String>, args: Vec<String>) -> Result<ActionResult> {
        agent.execute_action(Action::Git {
            subcommand: subcommand.into(),
            args,
        }).await
    }

    /// Send message to agent
    pub async fn say(agent: &AgentHandle, content: impl Into<String>) -> Result<()> {
        agent.send_message(Message::user(content)).await
    }
}
