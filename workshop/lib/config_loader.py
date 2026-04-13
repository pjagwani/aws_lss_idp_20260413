"""Hot-reloadable configuration loader.

Reads config.json on every access so changes apply without restart.
Validates config before returning.
"""

import json
import os
from typing import Any

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
_REQUIRED_KEYS = {
    "confidence_thresholds", "critical_field_names", "anomaly_detection",
    "retry", "performance", "security", "model_pinning",
}


def _validate(cfg: dict) -> list[str]:
    errors = []
    missing = _REQUIRED_KEYS - set(cfg.keys())
    if missing:
        errors.append(f"Missing top-level keys: {missing}")
    ct = cfg.get("confidence_thresholds", {})
    if not (0 <= ct.get("critical_fields", 0) <= 1):
        errors.append("critical_fields threshold must be 0-1")
    if not (0 <= ct.get("standard_fields", 0) <= 1):
        errors.append("standard_fields threshold must be 0-1")
    return errors


def load() -> dict[str, Any]:
    """Load and validate config.json. Returns config dict."""
    with open(_CONFIG_PATH) as f:
        cfg = json.load(f)
    errors = _validate(cfg)
    if errors:
        raise ValueError(f"Config validation failed: {errors}")
    return cfg


def get(key: str, default: Any = None) -> Any:
    """Get a top-level config key."""
    return load().get(key, default)


def get_nested(*keys: str, default: Any = None) -> Any:
    """Get a nested config value by key path."""
    obj = load()
    for k in keys:
        if isinstance(obj, dict):
            obj = obj.get(k)
        else:
            return default
        if obj is None:
            return default
    return obj
