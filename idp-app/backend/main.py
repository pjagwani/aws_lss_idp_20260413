"""
IDP Agent Backend — Multi-Agent Pipeline for Pharmaceutical Document Processing

Three-stage pipeline:
  1. Extraction Agent  — pulls structured fields from handwritten documents
  2. Validation Agent  — checks extracted values against schemas & specs
  3. Compliance Agent  — ALCOA+ scoring and deviation detection

Streams progress to the React frontend via Server-Sent Events.
"""

import asyncio
import base64
import json
import os
import re
import time
import uuid
from pathlib import Path

import boto3
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="IDP Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
WORKSHOP_DATA = Path(__file__).resolve().parent.parent.parent / "workshop" / "test-data" / "bmr"
KIRO_DATA = Path(__file__).resolve().parent.parent.parent / "kiro workshop" / "workshop" / "test-data" / "bmr"

# ---------------------------------------------------------------------------
# Bedrock client
# ---------------------------------------------------------------------------
def get_bedrock_client():
    region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    return boto3.Session(region_name=region).client("bedrock-runtime")


def detect_format(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith((".jpg", ".jpeg")):
        return "jpeg"
    return "png"


# ---------------------------------------------------------------------------
# Agent calls via Bedrock Converse API
# ---------------------------------------------------------------------------
def call_bedrock(system_prompt: str, user_content: list, model_id: str = None) -> str:
    if model_id is None:
        model_id = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")
    client = get_bedrock_client()
    response = client.converse(
        modelId=model_id,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": user_content}],
        inferenceConfig={"maxTokens": 4096, "temperature": 0.0},
    )
    parts = []
    for block in response["output"]["message"]["content"]:
        if "text" in block:
            parts.append(block["text"])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Stage 1: Extraction Agent
# ---------------------------------------------------------------------------
EXTRACTION_SYSTEM = """You are the Extraction Agent — an expert in reading handwritten pharmaceutical documents.

TASK: Extract ALL handwritten fields from the uploaded Batch Manufacturing Record (BMR) or QC form.

RULES:
1. Read every handwritten character carefully — distinguish 0/O, 1/l, 5/S, 6/G.
2. If a field is illegible, smudged, or missing, set its value to null.
3. For each extracted field, provide a confidence score: "high", "medium", or "low".
4. Return ONLY valid JSON — no markdown fences, no explanatory text.

SCHEMA for BMR documents:
{
  "document_type": "BMR",
  "product_name": {"value": string|null, "confidence": "high"|"medium"|"low"},
  "batch_number": {"value": string|null, "confidence": "high"|"medium"|"low"},
  "manufacturing_date": {"value": string|null, "confidence": "high"|"medium"|"low"},
  "expiry_date": {"value": string|null, "confidence": "high"|"medium"|"low"},
  "ingredients": [
    {
      "ingredient_name": {"value": string|null, "confidence": "high"|"medium"|"low"},
      "weight_kg": {"value": number|null, "confidence": "high"|"medium"|"low"},
      "lot_number": {"value": string|null, "confidence": "high"|"medium"|"low"}
    }
  ],
  "equipment_ids": [{"value": string|null, "confidence": "high"|"medium"|"low"}],
  "operator_initials": {"value": string|null, "confidence": "high"|"medium"|"low"},
  "start_timestamp": {"value": string|null, "confidence": "high"|"medium"|"low"},
  "end_timestamp": {"value": string|null, "confidence": "high"|"medium"|"low"}
}

Return ONLY the JSON object."""


# ---------------------------------------------------------------------------
# Stage 2: Validation Agent
# ---------------------------------------------------------------------------
VALIDATION_SYSTEM = """You are the Validation Agent — a pharmaceutical quality specialist.

You receive extracted data (JSON) from a Batch Manufacturing Record. Your job is to validate each field.

VALIDATION CHECKS:
1. batch_number: Must match pattern like BMR-YYYY-NNNN or similar standard format
2. weights: Must be positive numbers within reasonable pharma ranges (0.001 - 10000 kg)
3. timestamps: Must be valid date/time formats; end > start
4. operator_initials: Must be 2-4 uppercase letters
5. lot_numbers: Must not be empty if ingredient is present
6. equipment_ids: Must follow alphanumeric pattern
7. Required fields: product_name, batch_number, at least 1 ingredient

For each field, report:
- "status": "pass" | "warning" | "fail"
- "message": brief explanation

Return ONLY valid JSON with this structure:
{
  "validation_results": {
    "field_name": {"status": "pass"|"warning"|"fail", "message": "..."},
    ...
  },
  "total_fields": number,
  "passed": number,
  "warnings": number,
  "failed": number
}"""


# ---------------------------------------------------------------------------
# Stage 3: Compliance Agent
# ---------------------------------------------------------------------------
COMPLIANCE_SYSTEM = """You are the Compliance Agent — a GMP/ALCOA+ data integrity specialist.

You receive extracted data and validation results from a pharmaceutical Batch Manufacturing Record. Score the document against ALCOA+ data integrity principles.

ALCOA+ PRINCIPLES:
- Attributable: Can the record be traced to the person who performed the activity? (operator_initials present?)
- Legible: Are all entries clearly readable? (confidence scores)
- Contemporaneous: Were entries made at the time of activity? (timestamps present and logical?)
- Original: Is this the original record? (document quality assessment)
- Accurate: Are values within expected ranges? (validation results)
- Complete: Are all required fields filled? (null field count)
- Consistent: Are formats and units consistent across the record?
- Enduring: Is the document in a durable format?
- Available: Is the data accessible for review?

For each principle, score 0-10 and provide a brief assessment.

Also identify specific DEVIATIONS — any anomaly that would trigger an investigation in a GMP environment.

Return ONLY valid JSON:
{
  "alcoa_scores": {
    "attributable": {"score": 0-10, "assessment": "..."},
    "legible": {"score": 0-10, "assessment": "..."},
    "contemporaneous": {"score": 0-10, "assessment": "..."},
    "original": {"score": 0-10, "assessment": "..."},
    "accurate": {"score": 0-10, "assessment": "..."},
    "complete": {"score": 0-10, "assessment": "..."},
    "consistent": {"score": 0-10, "assessment": "..."},
    "enduring": {"score": 0-10, "assessment": "..."},
    "available": {"score": 0-10, "assessment": "..."}
  },
  "overall_score": 0-100,
  "risk_level": "low"|"medium"|"high"|"critical",
  "deviations": [
    {"field": "...", "type": "...", "severity": "minor"|"major"|"critical", "description": "..."}
  ],
  "recommendation": "..."
}"""


# ---------------------------------------------------------------------------
# Pipeline executor with SSE streaming
# ---------------------------------------------------------------------------
def build_document_content(doc_bytes: bytes, filename: str) -> list:
    """Build the Bedrock content blocks for a document."""
    fmt = detect_format(filename)
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", filename)
    if not safe_name or not safe_name[0].isalpha():
        safe_name = "doc_" + safe_name
    safe_name = safe_name[:200]

    if fmt == "pdf":
        return [{"document": {"name": safe_name, "format": "pdf", "source": {"bytes": doc_bytes}}}]
    else:
        return [{"image": {"format": fmt, "source": {"bytes": doc_bytes}}}]


def parse_json_response(text: str) -> dict:
    """Extract JSON from a model response, tolerating markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_response": text, "parse_error": True}


async def run_pipeline(doc_bytes: bytes, filename: str, session_id: str):
    """Generator that yields SSE events as the pipeline progresses."""

    doc_content = build_document_content(doc_bytes, filename)
    pipeline_start = time.time()

    # --- Event helper ---
    def sse(event_type: str, data: dict) -> str:
        data["session_id"] = session_id
        data["timestamp"] = time.time()
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    yield sse("pipeline_start", {
        "filename": filename,
        "stages": ["extraction", "validation", "compliance"],
        "message": "Pipeline initiated — processing document"
    })

    # ---- STAGE 1: Extraction ----
    yield sse("stage_start", {"stage": "extraction", "label": "Extraction Agent", "message": "Reading handwritten fields..."})

    try:
        extraction_prompt = [*doc_content, {"text": "Extract all handwritten fields from this pharmaceutical batch manufacturing record. Return structured JSON per the schema."}]
        raw = await asyncio.to_thread(call_bedrock, EXTRACTION_SYSTEM, extraction_prompt)
        extraction_data = parse_json_response(raw)
        yield sse("stage_complete", {
            "stage": "extraction",
            "label": "Extraction Agent",
            "result": extraction_data,
            "message": "Fields extracted successfully"
        })
    except Exception as e:
        yield sse("stage_error", {"stage": "extraction", "error": str(e)})
        yield sse("pipeline_complete", {"status": "error", "error": str(e), "duration": time.time() - pipeline_start})
        return

    # ---- STAGE 2: Validation ----
    yield sse("stage_start", {"stage": "validation", "label": "Validation Agent", "message": "Validating extracted fields..."})

    try:
        validation_prompt = [{"text": f"Validate the following extracted BMR data:\n\n{json.dumps(extraction_data, indent=2)}"}]
        raw = await asyncio.to_thread(call_bedrock, VALIDATION_SYSTEM, validation_prompt)
        validation_data = parse_json_response(raw)
        yield sse("stage_complete", {
            "stage": "validation",
            "label": "Validation Agent",
            "result": validation_data,
            "message": "Validation complete"
        })
    except Exception as e:
        yield sse("stage_error", {"stage": "validation", "error": str(e)})
        validation_data = {"error": str(e)}

    # ---- STAGE 3: Compliance ----
    yield sse("stage_start", {"stage": "compliance", "label": "Compliance Agent", "message": "Scoring ALCOA+ compliance..."})

    try:
        compliance_input = {
            "extracted_data": extraction_data,
            "validation_results": validation_data,
        }
        compliance_prompt = [{"text": f"Assess ALCOA+ compliance for this BMR extraction:\n\n{json.dumps(compliance_input, indent=2)}"}]
        raw = await asyncio.to_thread(call_bedrock, COMPLIANCE_SYSTEM, compliance_prompt)
        compliance_data = parse_json_response(raw)
        yield sse("stage_complete", {
            "stage": "compliance",
            "label": "Compliance Agent",
            "result": compliance_data,
            "message": "Compliance assessment complete"
        })
    except Exception as e:
        yield sse("stage_error", {"stage": "compliance", "error": str(e)})
        compliance_data = {"error": str(e)}

    # ---- Done ----
    duration = time.time() - pipeline_start
    yield sse("pipeline_complete", {
        "status": "success",
        "duration": round(duration, 2),
        "extraction": extraction_data,
        "validation": validation_data,
        "compliance": compliance_data,
        "message": f"Pipeline complete in {duration:.1f}s"
    })


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "idp-agent-pipeline"}


@app.get("/api/samples")
def list_samples():
    """Return available test BMR documents."""
    samples = []
    for folder in [WORKSHOP_DATA, KIRO_DATA]:
        if folder.exists():
            for f in sorted(folder.glob("*.pdf")):
                entry = {"name": f.name, "path": str(f), "size": f.stat().st_size}
                if not any(s["name"] == entry["name"] for s in samples):
                    samples.append(entry)
    return {"samples": samples}


@app.get("/api/samples/{filename}")
def get_sample(filename: str):
    """Serve a sample PDF for the viewer."""
    for folder in [WORKSHOP_DATA, KIRO_DATA]:
        fp = folder / filename
        if fp.exists():
            return FileResponse(fp, media_type="application/pdf", filename=filename)
    return {"error": "not found"}


@app.post("/api/process")
async def process_document(
    file: UploadFile = File(None),
    sample_name: str = Form(None),
):
    """Run the multi-agent pipeline on an uploaded or sample document."""
    if file:
        doc_bytes = await file.read()
        filename = file.filename
    elif sample_name:
        for folder in [WORKSHOP_DATA, KIRO_DATA]:
            fp = folder / sample_name
            if fp.exists():
                doc_bytes = fp.read_bytes()
                filename = sample_name
                break
        else:
            return {"error": "Sample not found"}
    else:
        return {"error": "No file or sample_name provided"}

    session_id = str(uuid.uuid4())[:8]

    return StreamingResponse(
        run_pipeline(doc_bytes, filename, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Chat endpoint — follow-up questions on the processed document
# ---------------------------------------------------------------------------
CHAT_SYSTEM = """You are an IDP (Intelligent Document Processing) assistant for pharmaceutical manufacturing.

You have access to a document that has already been processed by the extraction pipeline.
The extracted data and compliance results are provided below.

Answer the user's question based on the document and extracted data.
- For targeted extraction requests, return the specific fields requested as JSON.
- For validation requests, compare extracted values against expected values and report matches.
- For general questions, answer based on what was extracted from the document.
- Always be precise and cite specific values from the extraction.
- If asked to format as JSON, return clean JSON.

EXTRACTED DATA:
{extraction_json}

VALIDATION RESULTS:
{validation_json}

COMPLIANCE RESULTS:
{compliance_json}
"""

# In-memory session store for document context
_sessions: dict = {}


@app.post("/api/chat")
async def chat_endpoint(
    message: str = Form(...),
    session_id: str = Form(None),
    sample_name: str = Form(None),
    extraction_data: str = Form(None),
    validation_data: str = Form(None),
    compliance_data: str = Form(None),
    history: str = Form("[]"),
):
    """Chat with the agent about the processed document."""
    ext = json.loads(extraction_data) if extraction_data else {}
    val = json.loads(validation_data) if validation_data else {}
    comp = json.loads(compliance_data) if compliance_data else {}
    conv_history = json.loads(history) if history else []

    system = CHAT_SYSTEM.format(
        extraction_json=json.dumps(ext, indent=2),
        validation_json=json.dumps(val, indent=2),
        compliance_json=json.dumps(comp, indent=2),
    )

    # Build conversation as a single user message with history context
    history_text = ""
    for msg in conv_history[-10:]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        history_text += f"{role}: {msg.get('content', '')}\n"

    prompt_text = message
    if history_text.strip():
        prompt_text = f"Previous conversation:\n{history_text}\nCurrent question: {message}"

    # If we have the document, include it
    doc_content = []
    if sample_name:
        for folder in [WORKSHOP_DATA, KIRO_DATA]:
            fp = folder / sample_name
            if fp.exists():
                doc_content = build_document_content(fp.read_bytes(), sample_name)
                break

    user_content = [*doc_content, {"text": prompt_text}]

    async def stream():
        try:
            raw = await asyncio.to_thread(call_bedrock, system, user_content)
            # Stream word by word for a nice effect
            words = raw.split(' ')
            buffer = ''
            for i, word in enumerate(words):
                buffer += word + (' ' if i < len(words) - 1 else '')
                if len(buffer) > 20 or i == len(words) - 1:
                    yield f"data: {json.dumps({'chunk': buffer})}\n\n"
                    buffer = ''
            yield f"data: {json.dumps({'done': True, 'full_response': raw})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Serve React build (production)
# ---------------------------------------------------------------------------
frontend_build = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(frontend_build), html=True), name="spa")
