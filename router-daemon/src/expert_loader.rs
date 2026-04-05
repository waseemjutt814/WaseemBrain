use std::collections::HashMap;
use std::fs::File;
use std::path::Path;

use memmap2::{Mmap, MmapOptions};
use thiserror::Error;

#[derive(Default)]
pub struct ExpertFileCache {
    mapped: HashMap<String, Mmap>,
}

#[derive(Debug, Error)]
pub enum LoaderError {
    #[error("expert file not found: {0}")]
    MissingFile(String),
    #[error("expert map failed: {0}")]
    MapFailed(String),
}

impl ExpertFileCache {
    pub fn ensure_mapped(&mut self, expert_id: &str, file_path: &Path) -> Result<(), LoaderError> {
        if self.mapped.contains_key(expert_id) {
            return Ok(());
        }
        if !file_path.exists() {
            return Err(LoaderError::MissingFile(file_path.display().to_string()));
        }
        let file = File::open(file_path).map_err(|err| LoaderError::MapFailed(err.to_string()))?;
        let mapping = unsafe { MmapOptions::new().map(&file) }
            .map_err(|err| LoaderError::MapFailed(err.to_string()))?;
        self.mapped.insert(expert_id.to_string(), mapping);
        Ok(())
    }

    pub fn evict(&mut self, expert_id: &str) -> bool {
        self.mapped.remove(expert_id).is_some()
    }

    pub fn mapped_count(&self) -> usize {
        self.mapped.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn make_expert_file() -> std::path::PathBuf {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be after unix epoch")
            .as_nanos();
        let path = env::temp_dir().join(format!("expert-{unique}.onnx"));
        fs::write(&path, b"expert-bytes").expect("failed to write probe expert file");
        path
    }

    #[test]
    fn maps_and_evicts_files() {
        let file_path = make_expert_file();
        let mut cache = ExpertFileCache::default();

        cache
            .ensure_mapped("language-en", &file_path)
            .expect("mapping should succeed");
        assert_eq!(cache.mapped_count(), 1);
        assert!(cache.evict("language-en"));
        assert_eq!(cache.mapped_count(), 0);

        fs::remove_file(file_path).ok();
    }
}
