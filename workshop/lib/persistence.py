"""Disk-backed persistence for audit trail, extractions, and training data.

All logs are append-only (immutable). Data stored as JSONL files in workshop/data/.
"""

from __future__ import annotations

import json
import os
import hashlib
from datetime import datetime, timezone
from typing import Any

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _ensure_dir():
    os.makedirs(_DATA_DIR, exist_ok=True)


def _append_jsonl(filename: str, record: dict):
    """Append a JSON record to a JSONL file (append-only / immutable)."""
    _ensure_dir()
    path = os.path.join(_DATA_DIR, filename)
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _read_jsonl(filename: str) -> list[dict]:
    """Read all records from a JSONL file."""
    path = os.path.join(_DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# --- Audit Trail ---

def log_audit(action: str, details: dict[str, Any] | None = None):
    """Append an immutable audit log entry."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
    }
    if details:
        record["details"] = details
    _append_jsonl("audit_trail.jsonl", record)
    return record


def get_audit_trail() -> list[dict]:
    return _read_jsonl("audit_trail.jsonl")


# --- Extraction Results ---

def save_extraction(doc_name: str, doc_hash: str, model_id: str,
                    extracted_data: dict, validation_summary: dict | None = None,
                    token_usage: dict | None = None):
    """Save an extraction result."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "document_name": doc_name,
        "document_hash": doc_hash,
        "model_id": model_id,
        "extracted_data": extracted_data,
    }
    if validation_summary:
        record["validation_summary"] = validation_summary
    if token_usage:
        record["token_usage"] = token_usage
    _append_jsonl("extractions.jsonl", record)
    return record


def get_extractions() -> list[dict]:
    return _read_jsonl("extractions.jsonl")


# --- Training Data Collection ---

def save_correction(doc_name: str, doc_hash: str, field: str,
                    original_value: Any, corrected_value: Any, reviewer: str = "anonymous"):
    """Store a human correction as a training example."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "document_name": doc_name,
        "document_hash": doc_hash,
        "field": field,
        "original_value": original_value,
        "corrected_value": corrected_value,
        "reviewer": reviewer,
    }
    _append_jsonl("training_corrections.jsonl", record)
    log_audit("correction", {
        "field": field,
        "original": str(original_value)[:100],
        "corrected": str(corrected_value)[:100],
        "reviewer": reviewer,
    })
    return record


def get_corrections() -> list[dict]:
    return _read_jsonl("training_corrections.jsonl")


def export_training_jsonl() -> str:
    """Export corrections as JSONL for fine-tuning (anonymized)."""
    corrections = get_corrections()
    lines = []
    for c in corrections:
        anonymized = {
            "field": c["field"],
            "original": c["original_value"],
            "corrected": c["corrected_value"],
            "document_hash": c["document_hash"],
        }
        lines.append(json.dumps(anonymized))
    return "\n".join(lines)


# --- Validation Logs ---

def save_validation(doc_name: str, doc_hash: str, report_dict: dict):
    """Log a validation check result."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "document_name": doc_name,
        "document_hash": doc_hash,
        "validation": report_dict,
    }
    _append_jsonl("validations.jsonl", record)
    return record


# --- Model Monitoring ---

def save_model_metrics(model_id: str, doc_type: str, composite_confidence: float | None,
                       field_count: int, critical_failures: int):
    """Track model accuracy metrics."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": model_id,
        "doc_type": doc_type,
        "composite_confidence": composite_confidence,
        "field_count": field_count,
        "critical_failures": critical_failures,
    }
    _append_jsonl("model_metrics.jsonl", record)
    return record


def get_model_metrics() -> list[dict]:
    return _read_jsonl("model_metrics.jsonl")


def compute_hash(data: bytes) -> str:
    """SHA-256 hash of bytes, truncated to 16 chars."""
    return hashlib.sha256(data).hexdigest()[:16]
