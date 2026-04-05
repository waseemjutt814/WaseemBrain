use std::sync::atomic::{AtomicU64, Ordering};

#[derive(Default)]
pub struct Metrics {
    request_count: AtomicU64,
}

impl Metrics {
    pub fn record_request(&self) {
        self.request_count.fetch_add(1, Ordering::Relaxed);
    }

    pub fn request_count(&self) -> u64 {
        self.request_count.load(Ordering::Relaxed)
    }
}

#[cfg(test)]
mod tests {
    use super::Metrics;

    #[test]
    fn increments_request_count() {
        let metrics = Metrics::default();
        metrics.record_request();
        metrics.record_request();
        assert_eq!(metrics.request_count(), 2);
    }
}
