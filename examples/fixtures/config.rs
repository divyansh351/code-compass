use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct Config {
    name: String,
    values: HashMap<String, String>,
}

impl Config {
    fn new(name: &str) -> Self {
        Config { name: name.to_string(), values: HashMap::new() }
    }

    fn set(&mut self, key: &str, value: &str) {
        self.values.insert(key.to_string(), value.to_string());
    }

    fn get(&self, key: &str) -> Option<&String> {
        self.values.get(key)
    }
}

fn load_config(path: &str) -> Result<Config, Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string(path)?;
    let cfg: Config = serde_json::from_str(&content)?;
    Ok(cfg)
}
