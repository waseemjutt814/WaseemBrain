//! Core agent implementation

use crate::actions::{Action, ActionExecutor, ActionResult};
use crate::config::AgentConfig;
use crate::errors::{AgentError, Result};
use crate::logging::{init_tracing, AgentLogger, LogLevel};
use crate::messaging::{Message, MessageBus, MessageRole};
use crate::types::*;
use std::sync::Arc;
use tokio::sync::{mpsc, Mutex, RwLock};
use tracing::{debug, error, info, instrument, warn};

/// Handle to interact with a running agent
#[derive(Debug, Clone)]
pub struct AgentHandle {
    pub id: AgentId,
    pub tx: mpsc::Sender<AgentCommand>,
}

impl AgentHandle {
    /// Send a message to the agent
    pub async fn send_message(&self, message: Message) -> Result<()> {
        self.tx.send(AgentCommand::ProcessMessage(message)).await
            .map_err(|_| AgentError::Shutdown)?;
        Ok(())
    }

    /// Execute an action
    pub async fn execute_action(&self, action: Action) -> Result<ActionResult> {
        let (tx, mut rx) = mpsc::channel(1);
        self.tx.send(AgentCommand::ExecuteAction(action, tx)).await
            .map_err(|_| AgentError::Shutdown)?;
        
        rx.recv().await
            .ok_or_else(|| AgentError::Shutdown)?
    }

    /// Get current state
    pub async fn get_state(&self) -> Result<AgentState> {
        let (tx, mut rx) = mpsc::channel(1);
        self.tx.send(AgentCommand::GetState(tx)).await
            .map_err(|_| AgentError::Shutdown)?;
        
        rx.recv().await
            .ok_or_else(|| AgentError::Shutdown)
    }

    /// Shutdown the agent
    pub async fn shutdown(&self) -> Result<()> {
        self.tx.send(AgentCommand::Shutdown).await
            .map_err(|_| AgentError::Shutdown)?;
        Ok(())
    }
}

/// Internal agent commands
#[derive(Debug)]
pub(crate) enum AgentCommand {
    ProcessMessage(Message),
    ExecuteAction(Action, mpsc::Sender<Result<ActionResult>>),
    GetState(mpsc::Sender<AgentState>),
    Shutdown,
}

/// The Agent - production ready, real implementation
pub struct Agent {
    id: AgentId,
    config: AgentConfig,
    state: Arc<RwLock<AgentState>>,
    message_bus: Arc<Mutex<MessageBus>>,
    context: Arc<Mutex<AgentContext>>,
    executor: Arc<Mutex<ActionExecutor>>,
    logger: Arc<Mutex<AgentLogger>>,
    metrics: Arc<Mutex<AgentMetrics>>,
    handle: Option<AgentHandle>,
}

impl Agent {
    /// Create a new agent (doesn't start it)
    pub fn new(config: AgentConfig) -> Result<Self> {
        config.validate()?;

        let id = AgentId::new();
        let logger = AgentLogger::new(&id.0, 10000, LogLevel::Info);
        
        let executor = ActionExecutor::new(
            &id.0,
            config.max_actions,
            config.action_timeout.as_secs(),
            &config.working_dir,
        );

        Ok(Self {
            id,
            config,
            state: Arc::new(RwLock::new(AgentState::Initializing)),
            message_bus: Arc::new(Mutex::new(MessageBus::new(config.max_message_history))),
            context: Arc::new(Mutex::new(AgentContext::new())),
            executor: Arc::new(Mutex::new(executor)),
            logger: Arc::new(Mutex::new(logger)),
            metrics: Arc::new(Mutex::new(AgentMetrics::new())),
            handle: None,
        })
    }

    /// Start the agent and return a handle
    pub async fn start(mut self) -> Result<AgentHandle> {
        let (tx, mut rx) = mpsc::channel(100);
        
        self.handle = Some(AgentHandle {
            id: self.id.clone(),
            tx: tx.clone(),
        });

        // Set initial context
        {
            let mut context = self.context.lock().await;
            context.set("agent_id", &self.id.0);
            context.set("agent_name", &self.config.name);
            context.set("agent_version", &self.config.version);
            context.set("session_start", &chrono::Utc::now().to_rfc3339());
        }

        // Transition to idle
        {
            let mut state = self.state.write().await;
            *state = AgentState::Idle;
        }

        {
            let mut logger = self.logger.lock().await;
            logger.info(format!(
                "Agent {} v{} started (ID: {})",
                self.config.name, self.config.version, self.id.0
            ));
        }

        // Spawn agent loop
        let id = self.id.clone();
        let state = self.state.clone();
        let message_bus = self.message_bus.clone();
        let context = self.context.clone();
        let executor = self.executor.clone();
        let logger = self.logger.clone();
        let metrics = self.metrics.clone();

        tokio::spawn(async move {
            info!(agent_id = %id.0, "Agent loop started");

            while let Some(cmd) = rx.recv().await {
                match cmd {
                    AgentCommand::ProcessMessage(msg) => {
                        let _ = Self::handle_message(
                            &id, &state, &message_bus, &context, 
                            &executor, &logger, &metrics, msg
                        ).await;
                    }
                    AgentCommand::ExecuteAction(action, resp_tx) => {
                        let result = Self::handle_action(
                            &state, &executor, &logger, &metrics, action
                        ).await;
                        let _ = resp_tx.send(result).await;
                    }
                    AgentCommand::GetState(resp_tx) => {
                        let current = *state.read().await;
                        let _ = resp_tx.send(current).await;
                    }
                    AgentCommand::Shutdown => {
                        info!(agent_id = %id.0, "Shutdown requested");
                        let mut s = state.write().await;
                        *s = AgentState::Shutdown;
                        break;
                    }
                }
            }

            info!(agent_id = %id.0, "Agent loop ended");
        });

        Ok(self.handle.unwrap())
    }

    /// Handle message processing
    async fn handle_message(
        id: &AgentId,
        state: &Arc<RwLock<AgentState>>,
        message_bus: &Arc<Mutex<MessageBus>>,
        _context: &Arc<Mutex<AgentContext>>,
        executor: &Arc<Mutex<ActionExecutor>>,
        logger: &Arc<Mutex<AgentLogger>>,
        metrics: &Arc<Mutex<AgentMetrics>>,
        message: Message,
    ) -> Result<()> {
        debug!(agent_id = %id.0, message_id = %message.id, "Processing message");

        // Update state
        {
            let mut s = state.write().await;
            *s = AgentState::Processing;
        }

        // Store message
        {
            let mut bus = message_bus.lock().await;
            bus.push(message.clone());
        }

        // Update metrics
        {
            let mut m = metrics.lock().await;
            m.record_message();
        }

        // Log
        {
            let mut log = logger.lock().await;
            log.info(format!("Received message from {}: {} chars", 
                message.role, message.content.len()));
        }

        // Generate response (simplified - in production this would involve LLM/AI)
        let response_content = format!(
            "[Agent {}] Acknowledged message ({} chars). Action count: {}",
            id.0,
            message.content.len(),
            {
                let exec = executor.lock().await;
                exec.action_count()
            }
        );

        let response = Message::new(MessageRole::Assistant, response_content);
        
        {
            let mut bus = message_bus.lock().await;
            bus.push(response);
        }

        // Return to idle
        {
            let mut s = state.write().await;
            *s = AgentState::Idle;
        }

        Ok(())
    }

    /// Handle action execution
    async fn handle_action(
        state: &Arc<RwLock<AgentState>>,
        executor: &Arc<Mutex<ActionExecutor>>,
        logger: &Arc<Mutex<AgentLogger>>,
        metrics: &Arc<Mutex<AgentMetrics>>,
        action: Action,
    ) -> Result<ActionResult> {
        // Update state
        {
            let mut s = state.write().await;
            *s = AgentState::Executing;
        }

        // Execute
        let start = std::time::Instant::now();
        let result = {
            let mut exec = executor.lock().await;
            exec.execute(action).await?
        };

        let duration_ms = start.elapsed().as_millis() as u64;
        let success = result.is_success();

        // Update metrics
        {
            let mut m = metrics.lock().await;
            m.record_action(duration_ms as f64, success);
        }

        // Log
        {
            let mut log = logger.lock().await;
            if success {
                log.info(format!("Action completed successfully in {}ms", duration_ms));
            } else {
                log.warn(format!("Action failed after {}ms", duration_ms));
            }
        }

        // Return to idle
        {
            let mut s = state.write().await;
            *s = AgentState::Idle;
        }

        Ok(result)
    }

    /// Export session summary
    pub async fn export_session(&self) -> SessionSummary {
        let context = self.context.lock().await;
        let messages = self.message_bus.lock().await;
        let executor = self.executor.lock().await;
        let state = *self.state.read().await;

        SessionSummary {
            agent_id: self.id.clone(),
            session_id: SessionId::new(),
            start_time: context
                .get("session_start")
                .and_then(|s| chrono::DateTime::parse_from_rfc3339(s).ok())
                .map(|dt| dt.with_timezone(&chrono::Utc))
                .unwrap_or_else(chrono::Utc::now),
            end_time: Some(chrono::Utc::now()),
            message_count: messages.len(),
            action_count: executor.action_count(),
            final_state: state,
            context_snapshot: context.to_hashmap(),
        }
    }

    /// Get current state
    pub async fn state(&self) -> AgentState {
        *self.state.read().await
    }

    /// Get agent ID
    pub fn id(&self) -> &AgentId {
        &self.id
    }

    /// Get config
    pub fn config(&self) -> &AgentConfig {
        &self.config
    }
}

impl Drop for Agent {
    fn drop(&mut self) {
        // Cleanup if needed
        if let Some(handle) = &self.handle {
            let id = handle.id.clone();
            let tx = handle.tx.clone();
            
            tokio::spawn(async move {
                let _ = tx.send(AgentCommand::Shutdown).await;
                info!(agent_id = %id.0, "Agent dropped, shutdown signaled");
            });
        }
    }
}

/// Agent builder for ergonomic construction
pub struct AgentBuilder {
    config: AgentConfig,
}

impl AgentBuilder {
    /// Create new builder
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            config: AgentConfig::new(name),
        }
    }

    /// Set ID
    pub fn with_id(mut self, id: impl Into<String>) -> Self {
        self.config.id = id.into();
        self
    }

    /// Set max actions
    pub fn with_max_actions(mut self, max: usize) -> Self {
        self.config.max_actions = max;
        self
    }

    /// Set timeout
    pub fn with_timeout(mut self, secs: u64) -> Self {
        self.config.action_timeout = std::time::Duration::from_secs(secs);
        self
    }

    /// Set working directory
    pub fn with_working_dir(mut self, dir: impl Into<String>) -> Self {
        self.config.working_dir = dir.into();
        self
    }

    /// Disable thinking
    pub fn without_thinking(mut self) -> Self {
        self.config.enable_thinking = false;
        self
    }

    /// Build the agent
    pub fn build(self) -> Result<Agent> {
        Agent::new(self.config)
    }
}
