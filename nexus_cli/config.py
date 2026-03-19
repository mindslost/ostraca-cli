"""
Configuration management for the Nexus CLI.

This module handles loading and saving user preferences like themes
from a JSON configuration file in the user's home directory.
"""

import json
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH: Path = Path.home() / ".nexus_config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "theme": "textual-dark",
}


def load_config() -> Dict[str, Any]:
    """Load configuration from the JSON file."""
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
            # Merge defaults for missing keys
            return {**DEFAULT_CONFIG, **config}
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to the JSON file."""
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
    except OSError:
        pass


def get_preference(key: str) -> Any:
    """Get a single preference value."""
    config = load_config()
    return config.get(key, DEFAULT_CONFIG.get(key))


def set_preference(key: str, value: Any) -> None:
    """Set a single preference value."""
    config = load_config()
    config[key] = value
    save_config(config)
