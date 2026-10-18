"""
Performance instrumentation, timing wrappers, data versioning, and caching for ThreatDesk.
Operates entirely from the outside layer without modifying off-limits internal files.
"""

import os
import time
import json
import hashlib
from datetime import datetime
from functools import wraps

LOG_DIR = "logs"
TIMING_LOG = os.path.join(LOG_DIR, "timing.log")

def ensure_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)

def log_stage_timing(question: str, stage: str, duration: float = 0.0, success: bool = True):
    """Log stage timing to logs/timing.log without secrets or result rows."""
    ensure_log_dir()
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "question_hash": hashlib.sha256(question.encode("utf-8")).hexdigest()[:10],
        "stage": stage,
        "duration_seconds": round(duration, 4),
        "success": success
    }
    try:
        with open(TIMING_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

def get_data_version(active_config_file: str) -> str:
    """
    Compute a data version marker based on config file modification time
    and dataset files (if any) to invalidate cache when data changes.
    """
    version_parts = []
    config_path = os.path.join("configs", active_config_file)
    if os.path.exists(config_path):
        version_parts.append(str(os.path.getmtime(config_path)))

    dataset_dir = "dataset"
    if os.path.exists(dataset_dir):
        for root, _, files in os.walk(dataset_dir):
            for file in files:
                fp = os.path.join(root, file)
                try:
                    version_parts.append(str(os.path.getmtime(fp)))
                except Exception:
                    pass

    combined = "_".join(version_parts)
    return hashlib.md5(combined.encode("utf-8")).hexdigest()[:8]

def normalize_query(query: str) -> str:
    """Normalize query by lowercasing and collapsing whitespace."""
    return " ".join(query.strip().lower().split())

class PipelineCache:
    """In-memory and session cache for full pipeline results."""
    def __init__(self):
        self._cache = {}

    def get(self, query: str, config_file: str, data_version: str):
        key = (normalize_query(query), config_file, data_version)
        return self._cache.get(key)

    def set(self, query: str, config_file: str, data_version: str, result: dict):
        key = (normalize_query(query), config_file, data_version)
        self._cache[key] = result

    def clear(self):
        self._cache.clear()

# Global cache instance
pipeline_cache = PipelineCache()
