use std::fs;
use std::path::Path;
use std::time::Instant;

use crate::proto::{RouterDecision, RouterRequest};
use serde::Deserialize;
use thiserror::Error;

const FNV_OFFSET: u64 = 1469598103934665603;
const FNV_PRIME: u64 = 1099511628211;

#[derive(Debug)]
pub struct OnnxRouter {
    artifact: RouterArtifact,
}

#[derive(Debug, Deserialize)]
struct RouterArtifact {
    labels: Vec<String>,
    feature_count: usize,
    expert_weights: Vec<Vec<f32>>,
    expert_bias: Vec<f32>,
    internet_weights: Vec<f32>,
    internet_bias: f32,
    confidence_floor: f32,
}

#[derive(Debug, Error)]
pub enum RouterError {
    #[error("model load failed: {0}")]
    ModelLoadFailed(String),
    #[error("invalid input: {0}")]
    InvalidInput(String),
}

impl OnnxRouter {
    pub fn new(model_path: &Path, _confidence_threshold: f32) -> Result<Self, RouterError> {
        let raw = fs::read_to_string(model_path).map_err(|err| {
            RouterError::ModelLoadFailed(format!("router artifact not found at {}: {err}", model_path.display()))
        })?;
        let artifact: RouterArtifact = serde_json::from_str(&raw)
            .map_err(|err| RouterError::ModelLoadFailed(format!("invalid router artifact: {err}")))?;
        Ok(Self { artifact })
    }

    pub fn decide(&self, request: RouterRequest) -> Result<RouterDecision, RouterError> {
        if request.text.trim().is_empty() {
            return Err(RouterError::InvalidInput("request text cannot be empty".into()));
        }

        let started_at = Instant::now();
        let features = build_feature_vector(&request.text, self.artifact.feature_count);
        let scores: Vec<f32> = self
            .artifact
            .expert_weights
            .iter()
            .zip(self.artifact.expert_bias.iter())
            .map(|(weights, bias)| dot(weights, &features) + bias)
            .collect();
        let probabilities = softmax(&scores);
        let best_index = probabilities
            .iter()
            .enumerate()
            .max_by(|left, right| left.1.partial_cmp(right.1).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(index, _)| index)
            .unwrap_or(0);
        let internet_score = dot(&self.artifact.internet_weights, &features) + self.artifact.internet_bias;
        let internet_probability = sigmoid(internet_score);
        let latency_ms = started_at.elapsed().as_secs_f32() * 1000.0;

        Ok(RouterDecision {
            expert_ids: vec![self.artifact.labels[best_index].clone()],
            check_memory_first: true,
            internet_needed: internet_probability >= 0.5,
            confidence: self
                .artifact
                .confidence_floor
                .max(*probabilities.get(best_index).unwrap_or(&self.artifact.confidence_floor)),
            reasoning_trace: format!(
                "artifact-router:label={}:internet={internet_probability:.3}",
                self.artifact.labels[best_index]
            ),
            latency_ms,
        })
    }
}

fn build_feature_vector(text: &str, feature_count: usize) -> Vec<f32> {
    let mut vector = vec![0.0_f32; feature_count];
    for token in tokenize(text) {
        let digest = fnv1a(&token);
        let index = (digest % feature_count as u64) as usize;
        let sign = if digest & (1_u64 << 63) != 0 { -1.0 } else { 1.0 };
        vector[index] += sign;
    }
    let norm = vector.iter().map(|value| value * value).sum::<f32>().sqrt().max(1.0);
    vector.iter_mut().for_each(|value| *value /= norm);
    vector
}

fn tokenize(text: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut current = String::new();
    for ch in text.chars().flat_map(|ch| ch.to_lowercase()) {
        if ch.is_ascii_alphanumeric() || matches!(ch, '_' | '.' | '/' | '-') {
            current.push(ch);
            continue;
        }
        if current.len() >= 2 {
            tokens.push(current.clone());
        }
        current.clear();
    }
    if current.len() >= 2 {
        tokens.push(current);
    }
    tokens
}

fn fnv1a(token: &str) -> u64 {
    let mut value = FNV_OFFSET;
    for byte in token.as_bytes() {
        value ^= *byte as u64;
        value = value.wrapping_mul(FNV_PRIME);
    }
    value
}

fn dot(left: &[f32], right: &[f32]) -> f32 {
    left.iter().zip(right.iter()).map(|(a, b)| a * b).sum()
}

fn sigmoid(value: f32) -> f32 {
    1.0 / (1.0 + (-value).exp())
}

fn softmax(values: &[f32]) -> Vec<f32> {
    let maximum = values
        .iter()
        .copied()
        .fold(f32::NEG_INFINITY, |best, value| best.max(value));
    let scaled: Vec<f32> = values.iter().map(|value| (value - maximum).exp()).collect();
    let total = scaled.iter().sum::<f32>().max(1.0);
    scaled.iter().map(|value| value / total).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn make_model_file() -> std::path::PathBuf {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be after unix epoch")
            .as_nanos();
        let path = env::temp_dir().join(format!("router-model-{unique}.json"));
        fs::write(
            &path,
            r#"{
              "labels":["language-en","code-general","geography"],
              "feature_count":8,
              "expert_weights":[
                [0.1,0.1,0.0,0.0,0.0,0.0,0.0,0.0],
                [0.8,0.2,0.0,0.0,0.0,0.0,0.0,0.0],
                [0.0,0.0,0.8,0.2,0.0,0.0,0.0,0.0]
              ],
              "expert_bias":[0.0,1.0,-1.0],
              "internet_weights":[0.0,0.0,0.0,0.0,0.0,0.8,0.0,0.0],
              "internet_bias":0.0,
              "confidence_floor":0.5
            }"#,
        )
        .expect("failed to write router artifact");
        path
    }

    #[test]
    fn rejects_missing_model() {
        let missing = env::temp_dir().join("router-model-missing.json");
        let error = OnnxRouter::new(&missing, 0.7).expect_err("missing model should fail");
        assert!(matches!(error, RouterError::ModelLoadFailed(_)));
    }

    #[test]
    fn routes_queries_from_artifact() {
        let model_path = make_model_file();
        let router = OnnxRouter::new(&model_path, 0.8).expect("artifact should load");
        let decision = router
            .decide(RouterRequest {
                text: "latest python bridge".into(),
                modality: "text".into(),
                session_id: "session-1".into(),
                emotion_valence: 0.0,
                emotion_arousal: 0.0,
                emotion_primary: "calm".into(),
            })
            .expect("router should produce a decision");
        assert_eq!(decision.expert_ids, vec!["code-general".to_string()]);
        fs::remove_file(model_path).ok();
    }
}
