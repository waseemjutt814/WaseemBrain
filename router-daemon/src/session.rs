use std::collections::HashMap;
use std::time::Instant;

#[derive(Default)]
pub struct SessionTracker {
    started_at: HashMap<String, Instant>,
}

impl SessionTracker {
    pub fn touch(&mut self, session_id: &str) {
        self.started_at.entry(session_id.to_string()).or_insert_with(Instant::now);
    }

    pub fn uptime_seconds(&self, session_id: &str) -> Option<u64> {
        self.started_at
            .get(session_id)
            .map(|started_at| started_at.elapsed().as_secs())
    }
}

#[cfg(test)]
mod tests {
    use super::SessionTracker;

    #[test]
    fn tracks_session_uptime() {
        let mut tracker = SessionTracker::default();
        tracker.touch("session-1");
        assert!(tracker.uptime_seconds("session-1").is_some());
    }
}
