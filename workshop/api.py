"""REST API for IDP Agent - FastAPI with OpenAPI docs.

Endpoints for external systems to submit documents, retrieve extractions,
and access audit trail / metrics.

Run: uvicorn workshop.api:app --port 8000
Docs: http://localhost:8000/docs (Swagger) or /redoc (ReDoc)
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from lib import config_loader, persistence, validator
from lib.retry import with_retry

app = FastAPI(
    title="IDP Agent - Pharma Manufacturing API",
    description="Intelligent Document Processing for pharmaceutical batch manufacturing records. "
                "Extracts structured data, validates against ALCOA+ principles, and provides compliance reporting.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Webhook subscribers (in-memory for hackathon)
_webhook_urls: list[str] = []


# --- Health ---

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# --- Document Processing ---

class ExtractionResponse(BaseModel):
    document_id: str
    document_name: str
    upload_timestamp: str
    pages: int | None = None
    extracted_data: dict | None = None
    composite_confidence: float | None = None
    validation: dict | None = None
    token_usage: dict | None = None
    flagged_for_review: bool = False


@app.post("/extract", response_model=ExtractionResponse, tags=["Extraction"])
async def extract_document(file: UploadFile = File(...)):
    """Upload a document and extract structured data.

    Accepts PDF, PNG, JPG, JPEG files. Returns extracted fields with
    confidence scores and ALCOA+ validation report.
    """
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext not in ("pdf", "png", "jpg", "jpeg"):
        raise HTTPException(400, f"Unsupported format: .{ext}. Use PDF, PNG, JPG, or JPEG.")

    file_bytes = await file.read()
    doc_hash = hashlib.sha256(file_bytes).hexdigest()[:16]
    upload_ts = datetime.now(timezone.utc).isoformat()

    persistence.log_audit("api_upload", {
        "filename": file.filename,
        "size_bytes": len(file_bytes),
        "hash": doc_hash,
    })

    # Get page count for PDFs
    pages = None
    if ext == "pdf":
        try:
            from lib.chunker import get_page_count
            pages = get_page_count(file_bytes)
        except Exception:
            pass

    # Call Bedrock
    cfg = config_loader.load()
    model_id = cfg["model_pinning"]["default_model"]
    region = os.environ.get("AWS_DEFAULT_REGION", os.environ.get("AWS_REGION", "us-east-1"))

    try:
        import boto3
        session = boto3.Session(region_name=region)
        client = session.client("bedrock-runtime")
    except Exception as e:
        raise HTTPException(500, f"AWS client error: {e}")

    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", file.filename)
    if not safe_name or not safe_name[0].isalpha():
        safe_name = "doc_" + safe_name
    safe_name = safe_name[:200]

    content_blocks: list[dict] = []
    if ext == "pdf":
        content_blocks.append({"document": {"name": safe_name, "format": "pdf", "source": {"bytes": file_bytes}}})
    else:
        fmt = "jpeg" if ext in ("jpg", "jpeg") else "png"
        content_blocks.append({"image": {"format": fmt, "source": {"bytes": file_bytes}}})

    content_blocks.append({"text": (
        "Extract all fields from this batch manufacturing record as structured JSON with "
        "confidence scores (0.0-1.0) for each field, source_page numbers, composite_confidence, "
        "and flag any anomalies with severity levels."
    )})

    system_text = (
        "You are an expert IDP agent for pharmaceutical documents. "
        "Return JSON with confidence scores per field, source_page, "
        "composite_confidence, anomalies array, and flagged_for_review boolean. "
        "Normalize dates to ISO 8601, units to mg/mL/kg/L."
    )

    token_usage = {}
    extracted_data = None

    def _call_bedrock():
        return client.converse(
            modelId=model_id,
            system=[{"text": system_text}],
            messages=[{"role": "user", "content": content_blocks}],
            inferenceConfig={"maxTokens": 4096, "temperature": 0.0},
        )

    try:
        response = with_retry(_call_bedrock, context=f"extract:{file.filename}")
        parts = []
        for block in response["output"]["message"]["content"]:
            if "text" in block:
                parts.append(block["text"])
        raw_text = "\n".join(parts)

        # Parse token usage
        usage = response.get("usage", {})
        token_usage = {
            "input_tokens": usage.get("inputTokens", 0),
            "output_tokens": usage.get("outputTokens", 0),
        }

        # Try to parse JSON
        try:
            extracted_data = json.loads(raw_text)
        except json.JSONDecodeError:
            if "```json" in raw_text:
                block = raw_text.split("```json")[1].split("```")[0].strip()
                try:
                    extracted_data = json.loads(block)
                except json.JSONDecodeError:
                    extracted_data = {"raw_response": raw_text}
            else:
                extracted_data = {"raw_response": raw_text}

    except Exception as e:
        raise HTTPException(500, f"Extraction failed: {e}")

    # Validate
    val_report = validator.validate(extracted_data) if extracted_data else None
    val_dict = None
    if val_report:
        val_dict = {
            "alcoa_plus": {
                "pass": val_report.pass_count == val_report.total_principles,
                "score": f"{val_report.pass_count}/{val_report.total_principles}",
                "principles": val_report.principles,
                "failures": [
                    {"principle": i.principle, "severity": i.severity, "field": i.field, "description": i.description}
                    for i in val_report.issues
                ],
            },
            "anomalies": [
                {"severity": a.severity, "field": a.field, "description": a.description}
                for a in val_report.anomalies
            ],
            "flagged_for_review": val_report.flagged_for_review,
        }

    # Persist
    persistence.save_extraction(file.filename, doc_hash, model_id, extracted_data, val_dict, token_usage)
    if val_report:
        persistence.save_validation(file.filename, doc_hash, val_dict)
        persistence.save_model_metrics(
            model_id, "bmr",
            val_report.composite_confidence,
            len(val_report.all_confidences),
            sum(1 for i in val_report.issues if i.severity in ("high", "critical")),
        )

    persistence.log_audit("api_extraction_complete", {
        "filename": file.filename,
        "model": model_id,
        "tokens": token_usage,
        "composite_confidence": val_report.composite_confidence if val_report else None,
    })

    # Fire webhooks
    _fire_webhooks({
        "event": "extraction_complete",
        "document_name": file.filename,
        "document_hash": doc_hash,
        "composite_confidence": val_report.composite_confidence if val_report else None,
        "flagged": val_report.flagged_for_review if val_report else False,
    })

    return ExtractionResponse(
        document_id=doc_hash,
        document_name=file.filename,
        upload_timestamp=upload_ts,
        pages=pages,
        extracted_data=extracted_data,
        composite_confidence=val_report.composite_confidence if val_report else None,
        validation=val_dict,
        token_usage=token_usage,
        flagged_for_review=val_report.flagged_for_review if val_report else False,
    )


# --- Audit Trail ---

@app.get("/audit", tags=["Audit"])
def get_audit_trail():
    """Retrieve the immutable audit trail."""
    return persistence.get_audit_trail()


# --- Extractions ---

@app.get("/extractions", tags=["Extraction"])
def list_extractions():
    """List all extraction results."""
    return persistence.get_extractions()


# --- Model Metrics ---

@app.get("/metrics", tags=["Monitoring"])
def get_model_metrics():
    """Get model accuracy metrics for monitoring."""
    metrics = persistence.get_model_metrics()
    if not metrics:
        return {"message": "No metrics recorded yet"}

    confidences = [m["composite_confidence"] for m in metrics if m.get("composite_confidence") is not None]
    return {
        "total_extractions": len(metrics),
        "mean_confidence": sum(confidences) / len(confidences) if confidences else None,
        "min_confidence": min(confidences) if confidences else None,
        "max_confidence": max(confidences) if confidences else None,
        "recent": metrics[-10:],
    }


# --- Training Data ---

@app.get("/training-data", tags=["Training"])
def get_training_data():
    """Export anonymized training data as JSONL."""
    data = persistence.export_training_jsonl()
    return JSONResponse(content={"jsonl": data, "count": len(data.strip().split("\n")) if data.strip() else 0})


# --- Config ---

@app.get("/config", tags=["Config"])
def get_config():
    """Get current configuration."""
    return config_loader.load()


# --- Webhooks ---

class WebhookRegistration(BaseModel):
    url: str


@app.post("/webhooks", tags=["Webhooks"])
def register_webhook(reg: WebhookRegistration):
    """Register a webhook URL for extraction completion events."""
    _webhook_urls.append(reg.url)
    persistence.log_audit("webhook_registered", {"url": reg.url})
    return {"message": "Webhook registered", "total": len(_webhook_urls)}


@app.get("/webhooks", tags=["Webhooks"])
def list_webhooks():
    """List registered webhooks."""
    return {"webhooks": _webhook_urls}


def _fire_webhooks(payload: dict):
    """Fire webhooks (best-effort, non-blocking)."""
    import threading
    import urllib.request

    def _send(url: str, data: bytes):
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass

    data = json.dumps(payload).encode()
    for url in _webhook_urls:
        threading.Thread(target=_send, args=(url, data), daemon=True).start()
