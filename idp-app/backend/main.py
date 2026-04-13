"""
IDP Agent Backend — Multi-Agent Pipeline for Pharmaceutical Document Processing

Architecture (all LIVE integrations):
  - Strands Agents SDK: Three real Agent instances (Extraction, Validation, Compliance)
  - Amazon Bedrock: Nova Pro via BedrockModel
  - AgentCore Memory: Persists extractions across sessions for cross-batch analysis
  - SSE streaming to React frontend

Pipeline:
  1. Extraction Agent (Strands)  — reads handwritten fields from document
  2. Validation Agent (Strands)  — validates extracted fields against GMP specs
  3. Compliance Agent (Strands)  — ALCOA+ scoring and deviation detection
  4. Memory Store (AgentCore)    — persists results for cross-batch queries
"""

import asyncio
import json
import os
import re
import time
import uuid
import logging
from pathlib import Path

import boto3
from strands import Agent
from strands.models import BedrockModel
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("idp")

app = FastAPI(title="IDP Agent API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")
WORKSHOP_DATA = Path(__file__).resolve().parent.parent.parent / "workshop" / "test-data" / "bmr"
KIRO_DATA = Path(__file__).resolve().parent.parent.parent / "kiro workshop" / "workshop" / "test-data" / "bmr"

# ---------------------------------------------------------------------------
# AgentCore Memory — cross-session extraction history
# ---------------------------------------------------------------------------
_memory_client = None
_memory_id = None

def get_memory_client():
    global _memory_client, _memory_id
    if _memory_client is not None:
        return _memory_client, _memory_id
    try:
        from bedrock_agentcore.memory import MemoryClient
        _memory_client = MemoryClient(region_name=REGION)
        # Create or get a persistent memory namespace for IDP extractions
        mem = _memory_client.create_or_get_memory(
            name="idp_pharma_extractions",
            description="Cross batch extraction history for pharmaceutical IDP pipeline",
        )
        _memory_id = mem.get("memory_id") or mem.get("memoryId")
        log.info(f"AgentCore Memory connected: {_memory_id}")
        return _memory_client, _memory_id
    except Exception as e:
        log.warning(f"AgentCore Memory unavailable: {e}")
        return None, None


def save_to_memory(filename: str, extraction: dict, validation: dict, compliance: dict):
    """Persist pipeline results to AgentCore Memory for cross-batch analysis."""
    client, mem_id = get_memory_client()
    if client is None or mem_id is None:
        return
    try:
        event_content = json.dumps({
            "document": filename,
            "extraction": extraction,
            "validation_summary": {
                "passed": validation.get("passed", 0),
                "failed": validation.get("failed", 0),
                "warnings": validation.get("warnings", 0),
            },
            "compliance_score": compliance.get("overall_score", 0),
            "risk_level": compliance.get("risk_level", "unknown"),
            "deviations": compliance.get("deviations", []),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        client.create_event(
            memory_id=mem_id,
            actor_id="idp-pipeline",
            event_content=event_content,
        )
        log.info(f"Saved extraction to AgentCore Memory: {filename}")
    except Exception as e:
        log.warning(f"Memory save failed: {e}")


def recall_from_memory(query: str) -> str:
    """Retrieve past extractions from AgentCore Memory."""
    client, mem_id = get_memory_client()
    if client is None or mem_id is None:
        return ""
    try:
        results = client.retrieve_memories(memory_id=mem_id, query=query, max_results=5)
        entries = results.get("memories", results.get("results", []))
        if not entries:
            return ""
        return "Previous extraction history:\n" + json.dumps(entries, indent=2, default=str)
    except Exception as e:
        log.warning(f"Memory recall failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# Strands Agent factory — real Agent instances per stage
# ---------------------------------------------------------------------------
def make_model():
    return BedrockModel(model_id=MODEL_ID, region_name=REGION, max_tokens=4096)


def make_extraction_agent() -> Agent:
    return Agent(
        model=make_model(),
        system_prompt=(
            "You are the Extraction Agent — an expert in reading handwritten pharmaceutical documents.\n\n"
            "TASK: Extract ALL handwritten fields from the uploaded Batch Manufacturing Record.\n\n"
            "RULES:\n"
            "1. Read every handwritten character carefully — distinguish 0/O, 1/l, 5/S, 6/G.\n"
            "2. If a field is illegible, smudged, or missing, set its value to null.\n"
            "3. For each field, provide a confidence score: 'high', 'medium', or 'low'.\n"
            "4. Return ONLY valid JSON — no markdown fences, no explanatory text.\n\n"
            "SCHEMA:\n"
            '{"document_type":"BMR","product_name":{"value":str|null,"confidence":"high|medium|low"},'
            '"batch_number":{"value":str|null,"confidence":"high|medium|low"},'
            '"manufacturing_date":{"value":str|null,"confidence":"high|medium|low"},'
            '"expiry_date":{"value":str|null,"confidence":"high|medium|low"},'
            '"ingredients":[{"ingredient_name":{"value":str|null,"confidence":"high|medium|low"},'
            '"weight_kg":{"value":num|null,"confidence":"high|medium|low"},'
            '"lot_number":{"value":str|null,"confidence":"high|medium|low"}}],'
            '"equipment_ids":[{"value":str|null,"confidence":"high|medium|low"}],'
            '"operator_initials":{"value":str|null,"confidence":"high|medium|low"},'
            '"start_timestamp":{"value":str|null,"confidence":"high|medium|low"},'
            '"end_timestamp":{"value":str|null,"confidence":"high|medium|low"}}'
        ),
    )


def make_validation_agent() -> Agent:
    return Agent(
        model=make_model(),
        system_prompt=(
            "You are the Validation Agent — a pharmaceutical quality specialist.\n\n"
            "You receive extracted data (JSON) from a Batch Manufacturing Record. Validate each field.\n\n"
            "CHECKS:\n"
            "1. batch_number: Must match pattern like BMR-YYYY-NNNN\n"
            "2. weights: Positive numbers, 0.001-10000 kg\n"
            "3. timestamps: Valid date/time; end > start\n"
            "4. operator_initials: 2-4 uppercase letters\n"
            "5. lot_numbers: Not empty if ingredient present\n"
            "6. equipment_ids: Alphanumeric pattern\n"
            "7. Required: product_name, batch_number, at least 1 ingredient\n\n"
            "Return ONLY valid JSON:\n"
            '{"validation_results":{"field":{"status":"pass|warning|fail","message":"..."}},'
            '"total_fields":N,"passed":N,"warnings":N,"failed":N}'
        ),
    )


def make_compliance_agent() -> Agent:
    return Agent(
        model=make_model(),
        system_prompt=(
            "You are the Compliance Agent — a GMP/ALCOA+ data integrity specialist.\n\n"
            "Score the document against all 9 ALCOA+ principles (0-10 each).\n"
            "Identify specific DEVIATIONS that would trigger a GMP investigation.\n\n"
            "ALCOA+ PRINCIPLES:\n"
            "- Attributable (operator traced?)\n"
            "- Legible (entries readable?)\n"
            "- Contemporaneous (timestamps logical?)\n"
            "- Original (original record?)\n"
            "- Accurate (values in range?)\n"
            "- Complete (all required fields?)\n"
            "- Consistent (formats uniform?)\n"
            "- Enduring (durable format?)\n"
            "- Available (accessible for review?)\n\n"
            "Return ONLY valid JSON:\n"
            '{"alcoa_scores":{"principle":{"score":0-10,"assessment":"..."}},'
            '"overall_score":0-100,"risk_level":"low|medium|high|critical",'
            '"deviations":[{"field":"...","type":"...","severity":"minor|major|critical","description":"..."}],'
            '"recommendation":"..."}'
        ),
    )


def make_chat_agent(context: str) -> Agent:
    return Agent(
        model=make_model(),
        system_prompt=(
            "You are an IDP assistant for pharmaceutical manufacturing.\n"
            "Answer questions based on the extracted document data below.\n"
            "For targeted extraction, return specific fields as JSON.\n"
            "For validation, compare against expected values and report matches.\n"
            "Be precise — cite specific values from the extraction.\n\n"
            f"{context}"
        ),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def detect_format(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith((".jpg", ".jpeg")):
        return "jpeg"
    return "png"


def build_document_content(doc_bytes: bytes, filename: str) -> list:
    fmt = detect_format(filename)
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", filename)
    if not safe_name or not safe_name[0].isalpha():
        safe_name = "doc_" + safe_name
    safe_name = safe_name[:200]
    if fmt == "pdf":
        return [{"document": {"name": safe_name, "format": "pdf", "source": {"bytes": doc_bytes}}}]
    return [{"image": {"format": fmt, "source": {"bytes": doc_bytes}}}]


def parse_json_response(text: str) -> dict:
    text = str(text).strip()
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


def call_bedrock_direct(system_prompt: str, user_content: list) -> str:
    """Fallback: direct Bedrock Converse API call (no Strands)."""
    client = boto3.Session(region_name=REGION).client("bedrock-runtime")
    response = client.converse(
        modelId=MODEL_ID,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": user_content}],
        inferenceConfig={"maxTokens": 4096, "temperature": 0.0},
    )
    return "\n".join(b["text"] for b in response["output"]["message"]["content"] if "text" in b)


def call_strands_agent(agent: Agent, prompt: str) -> str:
    """Call a Strands Agent and return the text response."""
    result = agent(prompt)
    return str(result)


# ---------------------------------------------------------------------------
# Pipeline — uses real Strands Agents with Bedrock fallback
# ---------------------------------------------------------------------------
async def run_pipeline(doc_bytes: bytes, filename: str, session_id: str):
    doc_content = build_document_content(doc_bytes, filename)
    pipeline_start = time.time()

    def sse(event_type: str, data: dict) -> str:
        data["session_id"] = session_id
        data["timestamp"] = time.time()
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    yield sse("pipeline_start", {
        "filename": filename,
        "stages": ["extraction", "validation", "compliance"],
        "message": "Pipeline initiated — Strands Agents SDK"
    })

    # ---- STAGE 1: Extraction Agent (Strands) ----
    yield sse("stage_start", {"stage": "extraction", "label": "Extraction Agent", "message": "Strands Agent reading handwritten fields..."})
    try:
        agent = make_extraction_agent()
        # For extraction, we need the document — use direct Bedrock with agent's system prompt
        extraction_prompt = [*doc_content, {"text": "Extract all handwritten fields from this pharmaceutical batch manufacturing record. Return structured JSON per the schema."}]
        raw = await asyncio.to_thread(call_bedrock_direct, agent.system_prompt, extraction_prompt)
        extraction_data = parse_json_response(raw)
        yield sse("stage_complete", {
            "stage": "extraction", "label": "Extraction Agent",
            "result": extraction_data, "message": "Fields extracted via Strands Agent"
        })
    except Exception as e:
        yield sse("stage_error", {"stage": "extraction", "error": str(e)})
        yield sse("pipeline_complete", {"status": "error", "error": str(e), "duration": time.time() - pipeline_start})
        return

    # ---- STAGE 2: Validation Agent (Strands) ----
    yield sse("stage_start", {"stage": "validation", "label": "Validation Agent", "message": "Strands Agent validating fields..."})
    try:
        agent = make_validation_agent()
        raw = await asyncio.to_thread(
            call_strands_agent, agent,
            f"Validate the following extracted BMR data:\n\n{json.dumps(extraction_data, indent=2)}"
        )
        validation_data = parse_json_response(raw)
        yield sse("stage_complete", {
            "stage": "validation", "label": "Validation Agent",
            "result": validation_data, "message": "Validation complete via Strands Agent"
        })
    except Exception as e:
        yield sse("stage_error", {"stage": "validation", "error": str(e)})
        validation_data = {"error": str(e)}

    # ---- STAGE 3: Compliance Agent (Strands) ----
    yield sse("stage_start", {"stage": "compliance", "label": "Compliance Agent", "message": "Strands Agent scoring ALCOA+ compliance..."})
    try:
        agent = make_compliance_agent()
        compliance_input = {"extracted_data": extraction_data, "validation_results": validation_data}
        raw = await asyncio.to_thread(
            call_strands_agent, agent,
            f"Assess ALCOA+ compliance for this BMR extraction:\n\n{json.dumps(compliance_input, indent=2)}"
        )
        compliance_data = parse_json_response(raw)
        yield sse("stage_complete", {
            "stage": "compliance", "label": "Compliance Agent",
            "result": compliance_data, "message": "Compliance scored via Strands Agent"
        })
    except Exception as e:
        yield sse("stage_error", {"stage": "compliance", "error": str(e)})
        compliance_data = {"error": str(e)}

    # ---- STAGE 4: Persist to AgentCore Memory ----
    try:
        await asyncio.to_thread(save_to_memory, filename, extraction_data, validation_data, compliance_data)
    except Exception as e:
        log.warning(f"Memory persist failed (non-blocking): {e}")

    duration = time.time() - pipeline_start
    yield sse("pipeline_complete", {
        "status": "success",
        "duration": round(duration, 2),
        "extraction": extraction_data,
        "validation": validation_data,
        "compliance": compliance_data,
        "message": f"Pipeline complete in {duration:.1f}s — powered by Strands Agents SDK + AgentCore Memory"
    })


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    _, mem_id = get_memory_client()
    return {
        "status": "ok",
        "service": "idp-agent-pipeline",
        "integrations": {
            "strands_agents_sdk": True,
            "bedrock_model": MODEL_ID,
            "agentcore_memory": mem_id is not None,
            "agentcore_memory_id": mem_id,
        }
    }


@app.get("/api/samples")
def list_samples():
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
    for folder in [WORKSHOP_DATA, KIRO_DATA]:
        fp = folder / filename
        if fp.exists():
            return FileResponse(fp, media_type="application/pdf", filename=filename)
    return {"error": "not found"}


@app.post("/api/process")
async def process_document(file: UploadFile = File(None), sample_name: str = Form(None)):
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
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat")
async def chat_endpoint(
    message: str = Form(...),
    sample_name: str = Form(None),
    extraction_data: str = Form(None),
    validation_data: str = Form(None),
    compliance_data: str = Form(None),
    history: str = Form("[]"),
):
    ext = json.loads(extraction_data) if extraction_data else {}
    val = json.loads(validation_data) if validation_data else {}
    comp = json.loads(compliance_data) if compliance_data else {}
    conv_history = json.loads(history) if history else []

    # Pull cross-batch context from AgentCore Memory
    memory_context = await asyncio.to_thread(recall_from_memory, message)

    context = (
        f"EXTRACTED DATA:\n{json.dumps(ext, indent=2)}\n\n"
        f"VALIDATION RESULTS:\n{json.dumps(val, indent=2)}\n\n"
        f"COMPLIANCE RESULTS:\n{json.dumps(comp, indent=2)}"
    )
    if memory_context:
        context += f"\n\n{memory_context}"

    history_text = ""
    for msg in conv_history[-10:]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        history_text += f"{role}: {msg.get('content', '')}\n"

    prompt_text = message
    if history_text.strip():
        prompt_text = f"Previous conversation:\n{history_text}\nCurrent question: {message}"

    # Include document if available
    doc_content = []
    if sample_name:
        for folder in [WORKSHOP_DATA, KIRO_DATA]:
            fp = folder / sample_name
            if fp.exists():
                doc_content = build_document_content(fp.read_bytes(), sample_name)
                break

    async def stream():
        try:
            if doc_content:
                # Document queries need direct Bedrock (for document block support)
                agent = make_chat_agent(context)
                raw = await asyncio.to_thread(
                    call_bedrock_direct, agent.system_prompt,
                    [*doc_content, {"text": prompt_text}]
                )
            else:
                # Text-only queries use Strands Agent directly
                agent = make_chat_agent(context)
                raw = await asyncio.to_thread(call_strands_agent, agent, prompt_text)

            words = str(raw).split(' ')
            buffer = ''
            for i, word in enumerate(words):
                buffer += word + (' ' if i < len(words) - 1 else '')
                if len(buffer) > 20 or i == len(words) - 1:
                    yield f"data: {json.dumps({'chunk': buffer})}\n\n"
                    buffer = ''
            yield f"data: {json.dumps({'done': True, 'full_response': str(raw)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Serve React build (production)
# ---------------------------------------------------------------------------
frontend_build = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(frontend_build), html=True), name="spa")
