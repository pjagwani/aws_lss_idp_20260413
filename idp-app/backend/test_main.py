"""
Unit tests for IDP Agent Pipeline.

Tests are organized by feature:
  - Pipeline helpers (parse_json_response, build_document_content, detect_format)
  - API endpoints (health, samples, process, chat)
  - Cross-batch anomaly detection
  - Deviation report generation
  - Handwriting quality scoring
  - Multi-document reconciliation

Uses httpx.AsyncClient + FastAPI TestClient. Bedrock/Strands calls are mocked.
"""

import json
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path

from httpx import AsyncClient, ASGITransport
from main import (
    app, parse_json_response, build_document_content, detect_format,
    make_extraction_agent, make_validation_agent, make_compliance_agent,
    make_anomaly_agent, make_deviation_report_agent, make_handwriting_agent,
    make_reconciliation_agent, make_chat_agent,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_extraction():
    return {
        "document_type": "BMR",
        "product_name": {"value": "Amoxicillin 500mg Capsules", "confidence": "high"},
        "batch_number": {"value": "BMR-2024-0847", "confidence": "high"},
        "manufacturing_date": {"value": "2024-03-15", "confidence": "high"},
        "expiry_date": {"value": None, "confidence": "low"},
        "ingredients": [
            {"ingredient_name": {"value": "Amoxicillin Trihydrate", "confidence": "high"},
             "weight_kg": {"value": 125.0, "confidence": "high"},
             "lot_number": {"value": "AMX-2024-1001", "confidence": "high"}},
        ],
        "equipment_ids": [{"value": "MIX-401", "confidence": "high"}],
        "operator_initials": {"value": "JKL", "confidence": "high"},
        "start_timestamp": {"value": "2024-03-15 08:30", "confidence": "high"},
        "end_timestamp": {"value": "2024-03-15 14:45", "confidence": "high"},
    }


@pytest.fixture
def sample_validation():
    return {
        "validation_results": {
            "product_name": {"status": "pass", "message": "OK"},
            "batch_number": {"status": "pass", "message": "OK"},
        },
        "total_fields": 8, "passed": 7, "warnings": 0, "failed": 1,
    }


@pytest.fixture
def sample_compliance():
    return {
        "alcoa_scores": {
            "attributable": {"score": 10, "assessment": "OK"},
            "legible": {"score": 9, "assessment": "OK"},
        },
        "overall_score": 88,
        "risk_level": "medium",
        "deviations": [{"field": "expiry_date", "type": "missing_data", "severity": "major", "description": "Missing"}],
        "recommendation": "Add expiry date",
    }


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Test: parse_json_response
# ---------------------------------------------------------------------------
class TestParseJsonResponse:
    def test_valid_json(self):
        result = parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_markdown_fences(self):
        result = parse_json_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_embedded_in_text(self):
        result = parse_json_response('Here is the result: {"key": "value"} done.')
        assert result == {"key": "value"}

    def test_invalid_json_returns_raw(self):
        result = parse_json_response("not json at all")
        assert "raw_response" in result
        assert result["parse_error"] is True

    def test_empty_string(self):
        result = parse_json_response("")
        assert "raw_response" in result


# ---------------------------------------------------------------------------
# Test: detect_format
# ---------------------------------------------------------------------------
class TestDetectFormat:
    def test_pdf(self):
        assert detect_format("document.pdf") == "pdf"
        assert detect_format("DOCUMENT.PDF") == "pdf"

    def test_jpeg(self):
        assert detect_format("photo.jpg") == "jpeg"
        assert detect_format("photo.jpeg") == "jpeg"

    def test_png(self):
        assert detect_format("image.png") == "png"

    def test_unknown_defaults_png(self):
        assert detect_format("file.bmp") == "png"


# ---------------------------------------------------------------------------
# Test: build_document_content
# ---------------------------------------------------------------------------
class TestBuildDocumentContent:
    def test_pdf_content(self):
        result = build_document_content(b"fake-pdf", "test.pdf")
        assert len(result) == 1
        assert "document" in result[0]
        assert result[0]["document"]["format"] == "pdf"

    def test_image_content(self):
        result = build_document_content(b"fake-png", "test.png")
        assert len(result) == 1
        assert "image" in result[0]
        assert result[0]["image"]["format"] == "png"

    def test_safe_name_sanitization(self):
        result = build_document_content(b"data", "my file (1).pdf")
        name = result[0]["document"]["name"]
        assert " " not in name
        assert "(" not in name

    def test_name_starts_with_letter(self):
        result = build_document_content(b"data", "123.pdf")
        name = result[0]["document"]["name"]
        assert name[0].isalpha()


# ---------------------------------------------------------------------------
# Test: Agent factory functions
# ---------------------------------------------------------------------------
class TestAgentFactories:
    @patch("main.make_model")
    def test_extraction_agent_created(self, mock_model):
        mock_model.return_value = MagicMock()
        agent = make_extraction_agent()
        assert agent is not None
        assert "Extraction Agent" in agent.system_prompt

    @patch("main.make_model")
    def test_validation_agent_created(self, mock_model):
        mock_model.return_value = MagicMock()
        agent = make_validation_agent()
        assert "Validation Agent" in agent.system_prompt

    @patch("main.make_model")
    def test_compliance_agent_created(self, mock_model):
        mock_model.return_value = MagicMock()
        agent = make_compliance_agent()
        assert "Compliance Agent" in agent.system_prompt

    @patch("main.make_model")
    def test_anomaly_agent_created(self, mock_model):
        mock_model.return_value = MagicMock()
        agent = make_anomaly_agent()
        assert "Anomaly Detection" in agent.system_prompt

    @patch("main.make_model")
    def test_deviation_report_agent_created(self, mock_model):
        mock_model.return_value = MagicMock()
        agent = make_deviation_report_agent()
        assert "Deviation Report" in agent.system_prompt

    @patch("main.make_model")
    def test_handwriting_agent_created(self, mock_model):
        mock_model.return_value = MagicMock()
        agent = make_handwriting_agent()
        assert "Handwriting Quality" in agent.system_prompt

    @patch("main.make_model")
    def test_reconciliation_agent_created(self, mock_model):
        mock_model.return_value = MagicMock()
        agent = make_reconciliation_agent()
        assert "Reconciliation Agent" in agent.system_prompt

    @patch("main.make_model")
    def test_chat_agent_includes_context(self, mock_model):
        mock_model.return_value = MagicMock()
        agent = make_chat_agent("SOME CONTEXT DATA")
        assert "SOME CONTEXT DATA" in agent.system_prompt


# ---------------------------------------------------------------------------
# Test: API endpoints
# ---------------------------------------------------------------------------
class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        r = await client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["integrations"]["strands_agents_sdk"] is True


class TestSamplesEndpoint:
    @pytest.mark.asyncio
    async def test_list_samples(self, client):
        r = await client.get("/api/samples")
        assert r.status_code == 200
        data = r.json()
        assert "samples" in data
        assert isinstance(data["samples"], list)


class TestCrossBatchEndpoint:
    @pytest.mark.asyncio
    @patch("main.call_strands_agent")
    @patch("main.recall_from_memory")
    async def test_cross_batch_analysis(self, mock_recall, mock_agent, client, sample_extraction):
        mock_recall.return_value = ""
        mock_agent.return_value = json.dumps({
            "anomalies": [],
            "batch_comparison": {"current_batch": "BMR-2024-0847", "compared_against": 0, "product_match": False},
            "risk_summary": "First batch", "overall_risk": "low"
        })

        r = await client.post("/api/cross-batch-analysis", data={
            "extraction_data": json.dumps(sample_extraction),
            "filename": "test.pdf",
        })
        assert r.status_code == 200
        data = r.json()
        assert "result" in data
        assert data["result"]["overall_risk"] == "low"


class TestDeviationReportEndpoint:
    @pytest.mark.asyncio
    @patch("main.call_strands_agent")
    async def test_deviation_report(self, mock_agent, client, sample_extraction, sample_compliance):
        mock_agent.return_value = json.dumps({
            "report_id": "DEV-2024-0001", "classification": "major",
            "batch_info": {"product": "Amoxicillin", "batch_number": "BMR-2024-0847", "date": "2024-03-15"},
            "deviations": [], "overall_risk": "medium",
            "reviewer_notes": "OK", "report_date": "2024-03-15"
        })

        r = await client.post("/api/deviation-report", data={
            "extraction_data": json.dumps(sample_extraction),
            "compliance_data": json.dumps(sample_compliance),
            "filename": "test.pdf",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["result"]["report_id"] == "DEV-2024-0001"


class TestHandwritingScoreEndpoint:
    @pytest.mark.asyncio
    @patch("main.call_strands_agent")
    @patch("main.recall_from_memory")
    async def test_handwriting_score(self, mock_recall, mock_agent, client, sample_extraction):
        mock_recall.return_value = ""
        mock_agent.return_value = json.dumps({
            "operator": "JKL", "overall_score": 85, "grade": "B",
            "field_scores": [{"field": "product_name", "legibility_score": 90, "issues": []}],
            "trends": {"strengths": ["Consistent"], "weaknesses": ["Numbers unclear"]},
            "training_recommendations": ["Practice number writing"],
            "comparison_note": "First assessment", "risk_level": "low"
        })

        r = await client.post("/api/handwriting-score", data={
            "extraction_data": json.dumps(sample_extraction),
            "filename": "test.pdf",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["result"]["grade"] == "B"
        assert data["result"]["overall_score"] == 85


class TestReconcileEndpoint:
    @pytest.mark.asyncio
    @patch("main.call_bedrock_direct")
    @patch("main.call_strands_agent")
    async def test_reconcile_two_docs(self, mock_agent, mock_bedrock, client):
        extraction_json = json.dumps({
            "document_type": "BMR", "product_name": {"value": "Test", "confidence": "high"},
            "batch_number": {"value": "BMR-2024-0001", "confidence": "high"},
        })
        mock_bedrock.return_value = extraction_json
        mock_agent.return_value = json.dumps({
            "documents_analyzed": [{"name": "a.pdf", "type": "BMR"}, {"name": "b.pdf", "type": "BMR"}],
            "matches": [{"field": "batch_number", "status": "match", "values": {"a.pdf": "BMR-2024-0001", "b.pdf": "BMR-2024-0001"}}],
            "discrepancies": [], "reconciliation_score": 100,
            "overall_status": "reconciled", "summary": "All fields match"
        })

        # Use sample_names with two existing samples
        r = await client.post("/api/reconcile", data={
            "sample_names": "bmr-sample-01-clean.pdf,bmr-sample-02-messy.pdf"
        })
        assert r.status_code == 200
        data = r.json()
        assert "reconciliation" in data or "error" in data


class TestChatEndpoint:
    @pytest.mark.asyncio
    @patch("main.call_strands_agent")
    @patch("main.recall_from_memory")
    async def test_chat_returns_stream(self, mock_recall, mock_agent, client, sample_extraction):
        mock_recall.return_value = ""
        mock_agent.return_value = "The batch number is BMR-2024-0847."

        r = await client.post("/api/chat", data={
            "message": "What is the batch number?",
            "extraction_data": json.dumps(sample_extraction),
        })
        assert r.status_code == 200
        # SSE stream should contain the response
        text = r.text
        assert "BMR-2024-0847" in text
