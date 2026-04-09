//! Action system - REAL implementations only

use crate::errors::{AgentError, Result};
use crate::logging::{AgentLogger, LogLevel};
use serde::{Deserialize, Serialize};
use std::process::Stdio;
use std::time::{Duration, Instant};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::process::Command;
use tokio::time::timeout;

/// Action types - All execute for real
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Action {
    /// Execute system command (REAL)
    Execute {
        command: String,
        args: Vec<String>,
        working_dir: Option<String>,
        env_vars: Vec<(String, String)>,
    },

    /// Read file (REAL)
    ReadFile { path: String, limit_bytes: Option<usize> },

    /// Write file (REAL)
    WriteFile { path: String, content: String },

    /// HTTP GET request (REAL)
    HttpGet { url: String, headers: Vec<(String, String)> },

    /// HTTP POST request (REAL)
    HttpPost { url: String, body: String, headers: Vec<(String, String)> },

    /// Search files (REAL - uses find command)
    SearchFiles { pattern: String, directory: String, max_depth: Option<usize> },

    /// Git command (REAL)
    Git { subcommand: String, args: Vec<String> },

    /// Analyze code (REAL)
    AnalyzeCode { code: String, language: String },

    /// Thinking step (REAL - logs reasoning)
    Think { reasoning: String },

    /// Wait/sleep (REAL)
    Wait { milliseconds: u64 },
}

/// Action result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ActionResult {
    Success { output: String, duration_ms: u64 },
    Failure { error: String, duration_ms: u64 },
    Timeout { limit_secs: u64 },
    Cancelled,
}

impl ActionResult {
    /// Check if successful
    pub fn is_success(&self) -> bool {
        matches!(self, ActionResult::Success { .. })
    }

    /// Get output if success
    pub fn output(&self) -> Option<&str> {
        match self {
            ActionResult::Success { output, .. } => Some(output),
            _ => None,
        }
    }

    /// Get error if failure
    pub fn error(&self) -> Option<&str> {
        match self {
            ActionResult::Failure { error, .. } => Some(error),
            _ => None,
        }
    }

    /// Get duration
    pub fn duration_ms(&self) -> Option<u64> {
        match self {
            ActionResult::Success { duration_ms, .. } => Some(*duration_ms),
            ActionResult::Failure { duration_ms, .. } => Some(*duration_ms),
            _ => None,
        }
    }
}

/// Action executor - executes actions for real
pub struct ActionExecutor {
    logger: AgentLogger,
    default_timeout: Duration,
    action_count: usize,
    max_actions: usize,
    working_dir: String,
}

impl ActionExecutor {
    /// Create new executor
    pub fn new(
        agent_id: impl Into<String>,
        max_actions: usize,
        default_timeout_secs: u64,
        working_dir: impl Into<String>,
    ) -> Self {
        Self {
            logger: AgentLogger::new(agent_id, 10000, LogLevel::Info),
            default_timeout: Duration::from_secs(default_timeout_secs),
            action_count: 0,
            max_actions,
            working_dir: working_dir.into(),
        }
    }

    /// Execute an action (REAL implementation)
    pub async fn execute(&mut self, action: Action) -> Result<ActionResult> {
        // Check action limit
        if self.action_count >= self.max_actions {
            return Err(AgentError::ActionLimitExceeded(self.max_actions));
        }
        self.action_count += 1;

        let start = Instant::now();
        let action_num = self.action_count;

        self.logger.info(format!("Executing action {}/{}: {:?}", action_num, self.max_actions, action_type(&action)));

        let result = match action {
            Action::Execute { command, args, working_dir, env_vars } => {
                self.execute_real_command(command, args, working_dir, env_vars, start).await
            }
            Action::ReadFile { path, limit_bytes } => {
                self.read_file_real(&path, limit_bytes, start).await
            }
            Action::WriteFile { path, content } => {
                self.write_file_real(&path, &content, start).await
            }
            Action::HttpGet { url, headers } => {
                self.http_get_real(&url, headers, start).await
            }
            Action::HttpPost { url, body, headers } => {
                self.http_post_real(&url, &body, headers, start).await
            }
            Action::SearchFiles { pattern, directory, max_depth } => {
                self.search_files_real(&pattern, &directory, max_depth, start).await
            }
            Action::Git { subcommand, args } => {
                self.git_real(&subcommand, args, start).await
            }
            Action::AnalyzeCode { code, language } => {
                self.analyze_code_real(&code, &language, start).await
            }
            Action::Think { reasoning } => {
                self.think_real(&reasoning, start)
            }
            Action::Wait { milliseconds } => {
                self.wait_real(milliseconds, start).await
            }
        };

        match &result {
            ActionResult::Success { output, duration_ms } => {
                self.logger.info(format!("Action {} completed in {}ms, output: {} chars", action_num, duration_ms, output.len()));
            }
            ActionResult::Failure { error, duration_ms } => {
                self.logger.warn(format!("Action {} failed after {}ms: {}", action_num, duration_ms, error));
            }
            ActionResult::Timeout { limit_secs } => {
                self.logger.error(format!("Action {} timed out after {}s", action_num, limit_secs));
            }
            ActionResult::Cancelled => {
                self.logger.warn(format!("Action {} was cancelled", action_num));
            }
        }

        Ok(result)
    }

    /// REAL command execution
    async fn execute_real_command(
        &self,
        command: String,
        args: Vec<String>,
        working_dir: Option<String>,
        env_vars: Vec<(String, String)>,
        start: Instant,
    ) -> ActionResult {
        let mut cmd = Command::new(&command);
        cmd.args(&args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        // Set working directory
        if let Some(dir) = working_dir {
            cmd.current_dir(dir);
        } else {
            cmd.current_dir(&self.working_dir);
        }

        // Set environment variables
        for (key, value) in env_vars {
            cmd.env(key, value);
        }

        let result = timeout(self.default_timeout, cmd.spawn()).await;

        match result {
            Ok(Ok(mut child)) => {
                let output = timeout(self.default_timeout, child.wait_with_output()).await;

                match output {
                    Ok(Ok(output)) => {
                        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
                        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
                        let duration = start.elapsed().as_millis() as u64;

                        if output.status.success() {
                            let full_output = if stderr.is_empty() {
                                stdout
                            } else {
                                format!("{}\n[stderr]: {}", stdout, stderr)
                            };
                            ActionResult::Success { output: full_output, duration_ms: duration }
                        } else {
                            let error = format!(
                                "Exit code {}: {}\nstderr: {}",
                                output.status.code().unwrap_or(-1),
                                stdout,
                                stderr
                            );
                            ActionResult::Failure { error, duration_ms: duration }
                        }
                    }
                    Ok(Err(e)) => ActionResult::Failure {
                        error: format!("Failed to get output: {}", e),
                        duration_ms: start.elapsed().as_millis() as u64,
                    },
                    Err(_) => ActionResult::Timeout { limit_secs: self.default_timeout.as_secs() },
                }
            }
            Ok(Err(e)) => ActionResult::Failure {
                error: format!("Failed to spawn command: {}", e),
                duration_ms: start.elapsed().as_millis() as u64,
            },
            Err(_) => ActionResult::Timeout { limit_secs: self.default_timeout.as_secs() },
        }
    }

    /// REAL file read
    async fn read_file_real(&self, path: &str, limit_bytes: Option<usize>, start: Instant) -> ActionResult {
        let result = tokio::fs::read_to_string(path).await;
        let duration = start.elapsed().as_millis() as u64;

        match result {
            Ok(content) => {
                let output = if let Some(limit) = limit_bytes {
                    if content.len() > limit {
                        format!("{}\n... [{} more bytes]", &content[..limit], content.len() - limit)
                    } else {
                        content
                    }
                } else {
                    content
                };
                ActionResult::Success { output, duration_ms: duration }
            }
            Err(e) => ActionResult::Failure {
                error: format!("Failed to read file '{}': {}", path, e),
                duration_ms: duration,
            },
        }
    }

    /// REAL file write
    async fn write_file_real(&self, path: &str, content: &str, start: Instant) -> ActionResult {
        let result = tokio::fs::write(path, content).await;
        let duration = start.elapsed().as_millis() as u64;

        match result {
            Ok(_) => ActionResult::Success {
                output: format!("Wrote {} bytes to {}", content.len(), path),
                duration_ms: duration,
            },
            Err(e) => ActionResult::Failure {
                error: format!("Failed to write file '{}': {}", path, e),
                duration_ms: duration,
            },
        }
    }

    /// REAL HTTP GET
    async fn http_get_real(&self, url: &str, headers: Vec<(String, String)>, start: Instant) -> ActionResult {
        let client = match reqwest::Client::builder()
            .timeout(self.default_timeout)
            .build() {
            Ok(c) => c,
            Err(e) => return ActionResult::Failure {
                error: format!("Failed to build HTTP client: {}", e),
                duration_ms: start.elapsed().as_millis() as u64,
            },
        };

        let mut request = client.get(url);
        for (key, value) in headers {
            request = request.header(&key, &value);
        }

        match request.send().await {
            Ok(response) => {
                let status = response.status();
                match response.text().await {
                    Ok(body) => {
                        let output = format!("Status: {}\nBody: {}", status, body);
                        ActionResult::Success {
                            output,
                            duration_ms: start.elapsed().as_millis() as u64,
                        }
                    }
                    Err(e) => ActionResult::Failure {
                        error: format!("Failed to read response body: {}", e),
                        duration_ms: start.elapsed().as_millis() as u64,
                    },
                }
            }
            Err(e) => ActionResult::Failure {
                error: format!("HTTP GET failed: {}", e),
                duration_ms: start.elapsed().as_millis() as u64,
            },
        }
    }

    /// REAL HTTP POST
    async fn http_post_real(&self, url: &str, body: &str, headers: Vec<(String, String)>, start: Instant) -> ActionResult {
        let client = match reqwest::Client::builder()
            .timeout(self.default_timeout)
            .build() {
            Ok(c) => c,
            Err(e) => return ActionResult::Failure {
                error: format!("Failed to build HTTP client: {}", e),
                duration_ms: start.elapsed().as_millis() as u64,
            },
        };

        let mut request = client.post(url).body(body.to_string());
        for (key, value) in headers {
            request = request.header(&key, &value);
        }

        match request.send().await {
            Ok(response) => {
                let status = response.status();
                match response.text().await {
                    Ok(resp_body) => {
                        let output = format!("Status: {}\nResponse: {}", status, resp_body);
                        ActionResult::Success {
                            output,
                            duration_ms: start.elapsed().as_millis() as u64,
                        }
                    }
                    Err(e) => ActionResult::Failure {
                        error: format!("Failed to read response body: {}", e),
                        duration_ms: start.elapsed().as_millis() as u64,
                    },
                }
            }
            Err(e) => ActionResult::Failure {
                error: format!("HTTP POST failed: {}", e),
                duration_ms: start.elapsed().as_millis() as u64,
            },
        }
    }

    /// REAL file search using find command
    async fn search_files_real(&self, pattern: &str, directory: &str, max_depth: Option<usize>, start: Instant) -> ActionResult {
        let mut args = vec![directory.to_string(), "-type", "f"];
        
        if let Some(depth) = max_depth {
            args.push("-maxdepth".to_string());
            args.push(depth.to_string());
        }
        
        args.push("-name".to_string());
        args.push(pattern.to_string());

        self.execute_real_command(
            "find".to_string(),
            args,
            Some(self.working_dir.clone()),
            vec![],
            start,
        ).await
    }

    /// REAL git operations
    async fn git_real(&self, subcommand: &str, args: Vec<String>, start: Instant) -> ActionResult {
        let mut all_args = vec![subcommand.to_string()];
        all_args.extend(args);

        self.execute_real_command(
            "git".to_string(),
            all_args,
            Some(self.working_dir.clone()),
            vec![],
            start,
        ).await
    }

    /// REAL code analysis
    fn analyze_code_real(&self, code: &str, language: &str, start: Instant) -> ActionResult {
        let lines: Vec<&str> = code.lines().collect();
        let line_count = lines.len();
        
        let comment_count = lines.iter().filter(|l| {
            l.trim().starts_with("//") || 
            l.trim().starts_with("(*") || 
            l.trim().starts_with("#") ||
            l.contains("/*")
        }).count();
        
        let function_count = lines.iter().filter(|l| {
            l.contains("fn ") || 
            l.contains("let ") || 
            l.contains("def ") ||
            l.contains("function")
        }).count();

        let output = format!(
            "Language: {}\nTotal lines: {}\nComments: {} ({}%)\nFunctions: {}\nCode quality: {}",
            language,
            line_count,
            comment_count,
            if line_count > 0 { (comment_count * 100) / line_count } else { 0 },
            function_count,
            if comment_count > 0 { "Good" } else { "Add more comments" }
        );

        ActionResult::Success {
            output,
            duration_ms: start.elapsed().as_millis() as u64,
        }
    }

    /// REAL thinking (logs reasoning)
    fn think_real(&self, reasoning: &str, start: Instant) -> ActionResult {
        self.logger.info(format!("[THINK] {}", reasoning));
        
        ActionResult::Success {
            output: format!("[Analysis] {}", reasoning),
            duration_ms: start.elapsed().as_millis() as u64,
        }
    }

    /// REAL wait/sleep
    async fn wait_real(&self, milliseconds: u64, start: Instant) -> ActionResult {
        tokio::time::sleep(Duration::from_millis(milliseconds)).await;
        
        ActionResult::Success {
            output: format!("Waited {}ms", milliseconds),
            duration_ms: start.elapsed().as_millis() as u64,
        }
    }

    /// Get action count
    pub fn action_count(&self) -> usize {
        self.action_count
    }

    /// Get remaining actions
    pub fn remaining_actions(&self) -> usize {
        self.max_actions.saturating_sub(self.action_count)
    }
}

/// Helper to get action type name
fn action_type(action: &Action) -> &'static str {
    match action {
        Action::Execute { .. } => "Execute",
        Action::ReadFile { .. } => "ReadFile",
        Action::WriteFile { .. } => "WriteFile",
        Action::HttpGet { .. } => "HttpGet",
        Action::HttpPost { .. } => "HttpPost",
        Action::SearchFiles { .. } => "SearchFiles",
        Action::Git { .. } => "Git",
        Action::AnalyzeCode { .. } => "AnalyzeCode",
        Action::Think { .. } => "Think",
        Action::Wait { .. } => "Wait",
    }
}
