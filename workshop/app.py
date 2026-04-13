"""
IDP Agent - Pharma Workshop Chat Interface

Document-centric Q&A interface for the Intelligent Document Processing Agent.
Participants upload a handwritten document and ask questions about its contents.
The agent answers based on extracted document data, not general knowledge.

Tech Stack: Strands Agents SDK + BDA MCP Server + Amazon Bedrock AgentCore + Streamlit
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import json
import base64
import re
import csv
import io
import hashlib
from datetime import datetime, timezone

from lib import config_loader, persistence, validator
from lib.retry import with_retry
from lib.chunker import get_page_count


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="IDP Agent - Pharma Manufacturing",
    page_icon="https://em-content.zobj.net/source/apple/391/dna_1f9ec.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Design System CSS -- Deep Clinical Blue / Indigo palette
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ---- Fonts ---- */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Playfair+Display:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ---- CSS Variables ---- */
:root {
    --brand-900: #1E1B4B;
    --brand-800: #312E81;
    --brand-700: #3730A3;
    --brand-600: #4F46E5;
    --brand-500: #6366F1;
    --brand-400: #818CF8;
    --brand-300: #A5B4FC;
    --brand-200: #C7D2FE;
    --brand-100: #E0E7FF;
    --brand-50:  #EEF2FF;
    --brand-25:  #F5F7FF;

    --accent-600: #0891B2;
    --accent-500: #06B6D4;
    --accent-400: #22D3EE;
    --accent-100: #CFFAFE;

    --success-600: #059669;
    --success-500: #10B981;
    --success-100: #D1FAE5;

    --warn-600: #D97706;
    --warn-500: #F59E0B;
    --warn-100: #FEF3C7;

    --danger-600: #DC2626;
    --danger-500: #EF4444;
    --danger-100: #FEE2E2;

    --surface-primary: #FAFAFE;
    --surface-card: rgba(255,255,255,0.84);
    --surface-raised: #FFFFFF;
    --surface-dark: #0F172A;

    --text-primary: #1E293B;
    --text-secondary: #475569;
    --text-muted: #94A3B8;
    --text-on-dark: #F1F5F9;

    --border-light: rgba(99,102,241,0.08);
    --border-default: #E2E8F0;

    --shadow-soft: 0 1px 3px rgba(0,0,0,0.04);
    --shadow-card: 0 2px 8px rgba(0,0,0,0.04), 0 0 0 1px rgba(99,102,241,0.04);
    --shadow-elevated: 0 8px 24px rgba(0,0,0,0.06), 0 0 0 1px rgba(99,102,241,0.06);
    --shadow-glow: 0 0 24px 4px rgba(99,102,241,0.12);

    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 20px;
    --radius-pill: 9999px;

    --font-sans: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-display: 'Playfair Display', Georgia, serif;
    --font-mono: 'JetBrains Mono', 'SF Mono', monospace;
}

/* ---- Global ---- */
html, body, [class*="css"] {
    font-family: var(--font-sans) !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ---- Dot-grid mesh background ---- */
.stApp {
    background-color: var(--surface-primary) !important;
    background-image: radial-gradient(circle at 1px 1px, rgba(99,102,241,0.04) 1px, transparent 0) !important;
    background-size: 24px 24px !important;
}

/* ---- Custom scrollbar ---- */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-default); border-radius: var(--radius-pill); }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* ---- Header banner ---- */
.pharma-header {
    background: linear-gradient(135deg, var(--brand-600) 0%, var(--brand-900) 60%, #0F172A 100%);
    padding: 2rem 2.5rem;
    border-radius: var(--radius-xl);
    margin-bottom: 1.5rem;
    color: white;
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow-elevated);
}
.pharma-header::before {
    content: '';
    position: absolute;
    top: -60%;
    right: -8%;
    width: 320px;
    height: 320px;
    background: radial-gradient(circle, rgba(129,140,248,0.2) 0%, transparent 70%);
    border-radius: 50%;
}
.pharma-header::after {
    content: '';
    position: absolute;
    bottom: -40%;
    left: 10%;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(6,182,212,0.15) 0%, transparent 70%);
    border-radius: 50%;
}
.pharma-header h1 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.2;
    position: relative;
    z-index: 1;
}
.pharma-header p {
    margin: 0.4rem 0 0 0;
    opacity: 0.75;
    font-size: 0.9rem;
    font-weight: 400;
    letter-spacing: 0.02em;
    position: relative;
    z-index: 1;
}

/* ---- Glass cards ---- */
.glass-card {
    background: var(--surface-card);
    backdrop-filter: saturate(180%) blur(20px);
    -webkit-backdrop-filter: saturate(180%) blur(20px);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-lg);
    padding: 1.25rem 1.5rem;
    box-shadow: var(--shadow-card);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.glass-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-elevated);
}
.glass-card .card-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    font-weight: 600;
    margin-bottom: 0.35rem;
}
.glass-card .card-value {
    font-size: 1rem;
    font-weight: 600;
    color: var(--brand-700);
    line-height: 1.3;
}
.glass-card .card-icon {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--brand-25) 0%, #F8FAFC 100%) !important;
    border-right: 1px solid var(--border-light) !important;
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: var(--brand-800) !important;
    font-family: var(--font-sans) !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
}

/* ---- Tech stack pills ---- */
.tech-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: var(--brand-100);
    color: var(--brand-800);
    padding: 0.3rem 0.75rem;
    border-radius: var(--radius-pill);
    font-size: 0.72rem;
    font-weight: 600;
    margin: 0.15rem 0.1rem;
    border: 1px solid var(--brand-200);
    letter-spacing: 0.01em;
    transition: all 0.15s ease;
}
.tech-pill:hover {
    background: var(--brand-200);
    transform: translateY(-1px);
}

/* ---- Compliance badge ---- */
.compliance-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: linear-gradient(135deg, var(--brand-100), var(--brand-200));
    color: var(--brand-800);
    padding: 0.35rem 0.85rem;
    border-radius: var(--radius-pill);
    font-size: 0.72rem;
    font-weight: 700;
    border: 1px solid var(--brand-200);
    letter-spacing: 0.02em;
    box-shadow: 0 1px 4px rgba(99,102,241,0.1);
}

/* ---- Upload area ---- */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--brand-400) !important;
    border-radius: var(--radius-lg) !important;
    padding: 0.5rem !important;
    background: var(--brand-25) !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--brand-600) !important;
    background: var(--brand-50) !important;
    box-shadow: var(--shadow-glow) !important;
}

/* ---- Chat messages ---- */
[data-testid="stChatMessage"] {
    border-radius: var(--radius-lg) !important;
    border: 1px solid var(--border-light) !important;
    margin-bottom: 0.6rem !important;
    background: var(--surface-card) !important;
    backdrop-filter: saturate(180%) blur(12px) !important;
    -webkit-backdrop-filter: saturate(180%) blur(12px) !important;
}

/* ---- Chat input ---- */
[data-testid="stChatInput"] textarea {
    border-radius: var(--radius-lg) !important;
    border: 1px solid var(--border-default) !important;
    font-family: var(--font-sans) !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--brand-500) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.12) !important;
}

/* ---- Document status card (sidebar) ---- */
.doc-status {
    background: var(--surface-card);
    backdrop-filter: saturate(180%) blur(16px);
    border: 1px solid var(--brand-200);
    border-radius: var(--radius-md);
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    box-shadow: var(--shadow-soft);
}
.doc-status .label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    font-weight: 600;
}
.doc-status .value {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--brand-700);
    margin-top: 0.2rem;
}
.doc-status .value.empty {
    color: var(--text-muted);
    font-weight: 400;
    font-style: italic;
}

/* ---- Workflow steps ---- */
.workflow-step {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.55rem 0;
}
.workflow-step .step-num {
    background: var(--border-default);
    color: var(--text-muted);
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
    flex-shrink: 0;
    transition: all 0.25s ease;
}
.workflow-step .step-text {
    font-size: 0.85rem;
    color: var(--text-secondary);
    font-weight: 500;
}
.workflow-step.active .step-num {
    background: var(--brand-600);
    color: white;
    box-shadow: 0 0 0 4px rgba(99,102,241,0.15);
}
.workflow-step.active .step-text {
    color: var(--text-primary);
    font-weight: 600;
}
.workflow-step.done .step-num {
    background: var(--success-500);
    color: white;
}

/* ---- Stagger fade-up animations ---- */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}
.stagger-1 { animation: fadeUp 0.4s ease-out 0ms both; }
.stagger-2 { animation: fadeUp 0.4s ease-out 80ms both; }
.stagger-3 { animation: fadeUp 0.4s ease-out 160ms both; }
.stagger-4 { animation: fadeUp 0.4s ease-out 240ms both; }

/* ---- Section label ---- */
.section-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    font-weight: 600;
    margin-bottom: 0.5rem;
}

/* ---- Divider ---- */
.divider-gradient {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border-default), transparent);
    margin: 1rem 0;
    border: none;
}

/* ---- Onboarding cards ---- */
.onboard-card {
    background: var(--surface-card);
    backdrop-filter: saturate(180%) blur(16px);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: var(--shadow-card);
}
.onboard-card h4 {
    font-family: var(--font-sans);
    font-weight: 700;
    color: var(--brand-700);
    margin: 0 0 0.75rem 0;
    font-size: 1rem;
}

/* ---- ALCOA+ compliance card ---- */
.alcoa-card {
    background: var(--surface-card);
    backdrop-filter: saturate(180%) blur(16px);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-lg);
    padding: 1.25rem 1.5rem;
    box-shadow: var(--shadow-card);
    margin-top: 1rem;
}
.alcoa-card h4 {
    color: var(--brand-700);
    font-weight: 700;
    margin: 0 0 0.75rem 0;
    font-size: 0.95rem;
}
.alcoa-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.4rem 0;
    border-bottom: 1px solid rgba(0,0,0,0.04);
}
.alcoa-row:last-child { border-bottom: none; }
.alcoa-principle {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-primary);
}
.alcoa-desc {
    font-size: 0.75rem;
    color: var(--text-muted);
}
.alcoa-status {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.2rem 0.6rem;
    border-radius: var(--radius-pill);
}
.alcoa-pass {
    background: var(--success-100);
    color: var(--success-600);
}
.alcoa-warn {
    background: var(--warn-100);
    color: var(--warn-600);
}
.alcoa-na {
    background: #F1F5F9;
    color: var(--text-muted);
}

/* ---- Metric card (sidebar) ---- */
.metric-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.35rem 0;
}
.metric-label { font-size: 0.8rem; color: var(--text-secondary); }
.metric-value { font-size: 0.8rem; font-weight: 700; color: var(--brand-700); }

/* ---- Audit trail ---- */
.audit-entry {
    font-size: 0.72rem;
    color: var(--text-secondary);
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(0,0,0,0.03);
    font-family: var(--font-mono);
}
.audit-time { color: var(--text-muted); }

/* ---- JSON output styling ---- */
[data-testid="stJson"] {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border-light) !important;
    font-family: var(--font-mono) !important;
}

/* ---- Streamlit overrides ---- */
.stSelectbox > div > div { border-radius: var(--radius-sm) !important; }
.stTextInput > div > div > input { border-radius: var(--radius-sm) !important; }
hr { border-color: var(--border-light) !important; }
.stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-sm) !important;
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}

/* ---- Hide Streamlit branding ---- */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
defaults = {
    "document_path": None,
    "document_name": None,
    "extracted_data": None,
    "conversation_history": [],
    "document_bytes": None,
    "agent": None,
    "agent_initialised": False,
    "audit_trail": [],
    "extraction_count": 0,
    "review_status": None,
    "session_start": datetime.now(timezone.utc).isoformat(),
    "doc_hash": None,
    "last_activity": datetime.now(timezone.utc).isoformat(),
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "page_count": None,
    "validation_report": None,
    "corrections": {},
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# Session timeout check
_timeout_min = config_loader.get_nested("security", "session_timeout_minutes", default=30)
_last = datetime.fromisoformat(st.session_state.last_activity)
if (datetime.now(timezone.utc) - _last).total_seconds() > _timeout_min * 60:
    for k, v in defaults.items():
        st.session_state[k] = v if not isinstance(v, list) else []
    st.session_state["session_start"] = datetime.now(timezone.utc).isoformat()
st.session_state.last_activity = datetime.now(timezone.utc).isoformat()


def log_audit(action: str, details: dict | None = None):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    st.session_state.audit_trail.append({"time": ts, "action": action})
    persistence.log_audit(action, details)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### IDP Agent")
    st.markdown(
        '<span class="compliance-badge">ALCOA+ Compliant</span>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    # Tech stack pills
    st.markdown('<p class="section-label">Tech Stack</p>', unsafe_allow_html=True)
    st.markdown(
        '<span class="tech-pill">Strands SDK</span>'
        '<span class="tech-pill">BDA MCP</span>'
        '<span class="tech-pill">AgentCore</span>'
        '<span class="tech-pill">Bedrock</span>'
        '<span class="tech-pill">Streamlit</span>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="divider-gradient"></div>', unsafe_allow_html=True)

    # Agent config
    st.markdown('<p class="section-label">Agent Configuration</p>', unsafe_allow_html=True)
    aws_region = st.text_input(
        "AWS Region",
        value=os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")),
        help="AWS region for Bedrock API calls",
    )
    model_id = st.selectbox(
        "Bedrock Model",
        [
            "us.anthropic.claude-sonnet-4-6",
            "amazon.nova-pro-v1:0",
            "amazon.nova-lite-v1:0",
        ],
        index=0,
        help="Select the foundation model for document processing",
    )

    st.markdown('<div class="divider-gradient"></div>', unsafe_allow_html=True)

    # Document status
    st.markdown('<p class="section-label">Document Status</p>', unsafe_allow_html=True)
    if "document_name" in st.session_state and st.session_state.document_name:
        st.markdown(
            f'<div class="doc-status">'
            f'<div class="label">Loaded Document</div>'
            f'<div class="value">{st.session_state.document_name}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="doc-status">'
            '<div class="label">Document</div>'
            '<div class="value empty">No document loaded</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    # Session metrics
    if st.session_state.extraction_count > 0:
        st.markdown('<div class="divider-gradient"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-label">Session Metrics</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-row"><span class="metric-label">Extractions</span>'
            f'<span class="metric-value">{st.session_state.extraction_count}</span></div>'
            f'<div class="metric-row"><span class="metric-label">Messages</span>'
            f'<span class="metric-value">{len(st.session_state.conversation_history)}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="divider-gradient"></div>', unsafe_allow_html=True)

    # Workflow guide
    st.markdown('<p class="section-label">Workflow</p>', unsafe_allow_html=True)
    has_doc = st.session_state.get("document_name") is not None
    has_chat = len(st.session_state.get("conversation_history", [])) > 0

    step1_cls = "done" if has_doc else "active"
    step2_cls = "done" if has_chat else ("active" if has_doc else "")
    step3_cls = "active" if has_chat else ""

    st.markdown(
        f'<div class="workflow-step {step1_cls}">'
        f'<div class="step-num">1</div>'
        f'<div class="step-text">Upload document</div></div>'
        f'<div class="workflow-step {step2_cls}">'
        f'<div class="step-num">2</div>'
        f'<div class="step-text">Extract data</div></div>'
        f'<div class="workflow-step {step3_cls}">'
        f'<div class="step-num">3</div>'
        f'<div class="step-text">Validate & export</div></div>',
        unsafe_allow_html=True,
    )

    # Audit trail
    if st.session_state.audit_trail:
        st.markdown('<div class="divider-gradient"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-label">Audit Trail</p>', unsafe_allow_html=True)
        for entry in st.session_state.audit_trail[-8:]:
            st.markdown(
                f'<div class="audit-entry">'
                f'<span class="audit-time">{entry["time"]}</span> {entry["action"]}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Agent initialisation - Strands SDK + BDA MCP Server
# ---------------------------------------------------------------------------
@st.cache_resource
def build_agent(_region: str, _model_id: str):
    """Create a Strands Agent wired to the BDA MCP Server."""
    try:
        from strands import Agent
        from strands.models import BedrockModel
        from strands.tools.mcp import MCPClient
        from mcp import StdioServerParameters

        mcp_config_path = os.path.join(
            os.path.dirname(__file__), "setup", "mcp-config.json"
        )
        tools = []
        mcp_client = None

        if os.path.exists(mcp_config_path):
            with open(mcp_config_path) as f:
                mcp_cfg = json.load(f)
            bda_cfg = mcp_cfg.get("mcpServers", {}).get("bda", {})
            if bda_cfg:
                env = {}
                for k, v in bda_cfg.get("env", {}).items():
                    if v.startswith("${") and v.endswith("}"):
                        env[k] = os.environ.get(v[2:-1], v)
                    else:
                        env[k] = v
                mcp_client = MCPClient(
                    lambda: StdioServerParameters(
                        command=bda_cfg["command"],
                        args=bda_cfg.get("args", []),
                        env={**os.environ, **env},
                    )
                )
                tools = mcp_client.list_tools()

        model = BedrockModel(model_id=_model_id, region_name=_region, max_tokens=4096)
        system_prompt = (
            "You are an Intelligent Document Processing (IDP) agent specialising in "
            "pharmaceutical handwritten documents such as Batch Manufacturing Records (BMR) "
            "and QC Inspection Forms.\n\n"
            "RULES:\n"
            "1. Only answer questions based on the uploaded document content.\n"
            "2. If a field is unreadable or missing, return null for that field.\n"
            "3. When asked for extraction, return JSON with confidence scores per field.\n"
            "4. Follow ALCOA+ data integrity principles (all 9: Attributable, Legible, "
            "Contemporaneous, Original, Accurate, Complete, Consistent, Enduring, Available).\n"
            "5. Do NOT answer general knowledge questions unrelated to the document.\n"
            "6. Use this schema for extraction:\n"
            '{"batch_record":{"product_name":{"value":"...","confidence":0.95,"source_page":1},'
            '"batch_number":{"value":"...","confidence":0.98,"source_page":1},'
            '"mfg_date":{"value":"ISO8601","confidence":0.92,"source_page":1},'
            '"ingredients":[{"name":{"value":"...","confidence":0.91},'
            '"quantity":{"value":500.0,"unit":"mg","confidence":0.89},"source_page":3}],'
            '"equipment_ids":[{"value":"...","confidence":0.97,"source_page":2}],'
            '"operator":{"value":"...","confidence":0.88,"source_page":1},'
            '"start_timestamp":{"value":"ISO8601","confidence":0.90,"source_page":1},'
            '"end_timestamp":{"value":"ISO8601","confidence":0.90,"source_page":1},'
            '"process_steps":[{"step":1,"description":"...","operator":{"value":"...","confidence":0.88},'
            '"timestamp":{"value":"ISO8601","confidence":0.90},"source_page":4}]},'
            '"composite_confidence":0.91,'
            '"anomalies":[{"field":"...","severity":"low|medium|high|critical","description":"..."}],'
            '"flagged_for_review":false}\n'
            "7. Flag critical fields (batch_number, ingredient qty, equipment_id) with "
            "confidence < 0.90.\n"
            "8. Flag anomalies with severity (low/medium/high/critical): missing signatures, "
            "timestamps outside normal shift hours (06:00-22:00), "
            "quantities deviating >5% from expected ranges.\n"
            "9. Normalize dates to ISO 8601, normalize units to mg/mL/kg/L."
        )
        agent = Agent(model=model, tools=tools, system_prompt=system_prompt)
        return agent, mcp_client, None
    except ImportError as e:
        return None, None, f"Missing dependency: {e}. Run: pip install strands-agents strands-agents-tools"
    except Exception as e:
        return None, None, f"Agent init error: {e}"


# ---------------------------------------------------------------------------
# Helpers - send question
# ---------------------------------------------------------------------------
def send_document_question(question, document_bytes, conversation_history):
    agent, _, init_err = build_agent(aws_region, model_id)
    if init_err:
        return f"Agent not available: {init_err}"
    if agent is None:
        return "Agent could not be initialised."

    doc_name = st.session_state.document_name or "document"
    history_text = ""
    if conversation_history:
        history_text = "\n\nPrevious conversation:\n"
        for msg in conversation_history[-6:]:
            history_text += f"{msg['role'].upper()}: {msg['content']}\n"

    doc_b64 = base64.b64encode(document_bytes).decode("utf-8")
    doc_name_lower = doc_name.lower()
    if doc_name_lower.endswith(".pdf"):
        doc_type = "pdf"
    elif doc_name_lower.endswith((".jpg", ".jpeg")):
        doc_type = "jpeg"
    else:
        doc_type = "png"

    prompt = (
        f"I have uploaded a handwritten pharmaceutical document named '{doc_name}' "
        f"(format: {doc_type}, base64 length: {len(doc_b64)} chars).\n"
        f"The full document content in base64 is:\n{doc_b64}\n"
        f"{history_text}\n"
        f"Question: {question}\n\n"
        f"Please carefully examine the handwritten text in this document. "
        f"Pay close attention to handwritten numbers, names, and dates. "
        f"If any field is unclear or illegible, return null for that field."
    )
    try:
        return str(agent(prompt))
    except TimeoutError:
        raise
    except Exception as e:
        return f"Agent error: {e}"


def send_question_bedrock_fallback(question, document_bytes, conversation_history):
    try:
        import boto3
    except ImportError:
        return "boto3 is not installed. Run: pip install boto3"

    try:
        session = boto3.Session(region_name=aws_region)
        creds = session.get_credentials()
        if creds is None:
            return "No AWS credentials found. Set environment variables or run `aws configure`."

        client = session.client("bedrock-runtime")
        raw_name = st.session_state.document_name or "document"
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", raw_name)
        if not safe_name or not safe_name[0].isalpha():
            safe_name = "doc_" + safe_name
        safe_name = safe_name[:200]

        history_context = ""
        for msg in conversation_history[-6:]:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            history_context += f"{role_label}: {msg['content']}\n"

        content_blocks = []
        doc_name_lower = (st.session_state.document_name or "").lower()
        if doc_name_lower.endswith(".pdf"):
            content_blocks.append({
                "document": {
                    "name": safe_name, "format": "pdf",
                    "source": {"bytes": document_bytes},
                }
            })
        elif doc_name_lower.endswith((".png", ".jpg", ".jpeg")):
            fmt = "jpeg" if doc_name_lower.endswith((".jpg", ".jpeg")) else "png"
            content_blocks.append({
                "image": {"format": fmt, "source": {"bytes": document_bytes}}
            })

        full_question = question
        if history_context.strip():
            full_question = f"Previous conversation:\n{history_context}\nCurrent question: {question}"
        content_blocks.append({"text": full_question})

        system_text = (
            "You are an expert Intelligent Document Processing (IDP) agent specialising in "
            "pharmaceutical handwritten documents such as Batch Manufacturing Records (BMR) "
            "and QC Inspection Forms.\n\n"
            "CRITICAL INSTRUCTIONS FOR HANDWRITTEN DOCUMENT EXTRACTION:\n"
            "1. Carefully examine every pixel of the uploaded document image/PDF.\n"
            "2. Pay special attention to handwritten text - read each character individually.\n"
            "3. For numbers: distinguish between similar-looking digits (0 vs O, 1 vs l, 5 vs S).\n"
            "4. For names: spell out exactly what is written, even if it looks like a misspelling.\n"
            "5. For dates/timestamps: normalize to ISO 8601. Separate values from units.\n"
            "6. If a field is crossed out, smudged, or truly illegible, return null.\n"
            "7. Only answer based on the uploaded document content - never fabricate data.\n"
            "8. When asked for extraction, return JSON with confidence scores (0.0-1.0) per field.\n"
            "9. Follow full ALCOA+ (Attributable, Legible, Contemporaneous, Original, Accurate, "
            "Complete, Consistent, Enduring, Available).\n"
            "10. Use this schema:\n"
            '{"batch_record":{"product_name":{"value":"...","confidence":0.95,"source_page":1},'
            '"batch_number":{"value":"...","confidence":0.98,"source_page":1},'
            '"mfg_date":{"value":"ISO8601","confidence":0.92,"source_page":1},'
            '"ingredients":[{"name":{"value":"...","confidence":0.91},'
            '"quantity":{"value":500.0,"unit":"mg","confidence":0.89},"source_page":3}],'
            '"equipment_ids":[{"value":"...","confidence":0.97,"source_page":2}],'
            '"operator":{"value":"...","confidence":0.88,"source_page":1},'
            '"start_timestamp":{"value":"ISO8601","confidence":0.90,"source_page":1},'
            '"end_timestamp":{"value":"ISO8601","confidence":0.90,"source_page":1},'
            '"process_steps":[{"step":1,"description":"...","operator":{"value":"...","confidence":0.88},'
            '"timestamp":{"value":"ISO8601","confidence":0.90},"source_page":4}]},'
            '"composite_confidence":0.91,'
            '"anomalies":[{"field":"...","severity":"low|medium|high|critical","description":"..."}],'
            '"flagged_for_review":false}\n'
            "11. Flag critical fields (batch_number, ingredient qty, equipment_id) if confidence < 0.90.\n"
            "12. Flag anomalies with severity (low/medium/high/critical): missing signatures, "
            "timestamps outside normal shift hours (06:00-22:00), quantity deviations >5%.\n"
            "13. Normalize units to mg/mL/kg/L.\n"
            "14. For QC forms use: product_name, batch_number, tests "
            "(array of test_name, test_parameters, measured_value, unit, "
            "specification_limit, pass_fail), inspector_name, inspection_date."
        )

        def _call():
            return client.converse(
                modelId=model_id,
                system=[{"text": system_text}],
                messages=[{"role": "user", "content": content_blocks}],
                inferenceConfig={"maxTokens": 4096, "temperature": 0.0},
            )

        response = with_retry(_call, context=f"bedrock:{model_id}")

        # Track token usage
        usage = response.get("usage", {})
        st.session_state.total_input_tokens += usage.get("inputTokens", 0)
        st.session_state.total_output_tokens += usage.get("outputTokens", 0)

        parts = []
        for block in response["output"]["message"]["content"]:
            if "text" in block:
                parts.append(block["text"])
        return "\n".join(parts)

    except Exception as e:
        error_str = str(e)
        if "AccessDeniedException" in error_str:
            return f"Access denied for model `{model_id}`. Enable it in Bedrock console."
        if "ExpiredTokenException" in error_str:
            return "AWS credentials expired. Run `aws sso login`."
        return f"Bedrock API error: {e}"


def send_question(question, document_bytes, history):
    agent, _, init_err = build_agent(aws_region, model_id)
    if agent is not None and init_err is None:
        return send_document_question(question, document_bytes, history)
    return send_question_bedrock_fallback(question, document_bytes, history)


# ---------------------------------------------------------------------------
# Helper - render assistant response
# ---------------------------------------------------------------------------
def render_response(content):
    """Render agent response, detecting and formatting JSON blocks."""
    try:
        parsed = json.loads(content)
        st.json(parsed)
        return
    except (json.JSONDecodeError, TypeError):
        pass

    if "```json" in content:
        parts = content.split("```json")
        for idx, part in enumerate(parts):
            if idx == 0:
                if part.strip():
                    st.markdown(part)
            else:
                json_block, *rest = part.split("```", 1)
                try:
                    st.json(json.loads(json_block.strip()))
                except (json.JSONDecodeError, TypeError):
                    st.code(json_block.strip(), language="json")
                if rest and rest[0].strip():
                    st.markdown(rest[0])
    else:
        st.markdown(content)


def extract_json_from_response(content: str) -> dict | None:
    """Try to parse JSON from an agent response string."""
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        pass
    if "```json" in content:
        block = content.split("```json")[1].split("```")[0].strip()
        try:
            return json.loads(block)
        except (json.JSONDecodeError, TypeError):
            pass
    return None


# ---------------------------------------------------------------------------
# Main area - Header
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="pharma-header">'
    '<h1>Intelligent Document Processing Agent</h1>'
    '<p>Pharmaceutical Manufacturing &middot; Handwritten Document Extraction &middot; ALCOA+ Compliant</p>'
    '</div>',
    unsafe_allow_html=True,
)

# Info cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(
        '<div class="glass-card stagger-1">'
        '<div class="card-icon">&#128203;</div>'
        '<div class="card-label">Document Types</div>'
        '<div class="card-value">Batch Records & QC Forms</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        '<div class="glass-card stagger-2">'
        '<div class="card-icon">&#129302;</div>'
        '<div class="card-label">Processing</div>'
        '<div class="card-value">AI-Powered Extraction</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        '<div class="glass-card stagger-3">'
        '<div class="card-icon">&#128200;</div>'
        '<div class="card-label">Output</div>'
        '<div class="card-value">Structured JSON + CSV</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with col4:
    st.markdown(
        '<div class="glass-card stagger-4">'
        '<div class="card-icon">&#9989;</div>'
        '<div class="card-label">Compliance</div>'
        '<div class="card-value">ALCOA+ Data Integrity</div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("")

# ---------------------------------------------------------------------------
# Two-column layout: Document Viewer | Chat
# ---------------------------------------------------------------------------
if st.session_state.get("document_bytes"):
    doc_col, chat_col = st.columns([2, 3])
else:
    doc_col, chat_col = None, None

# ---------------------------------------------------------------------------
# File uploader (always visible)
# ---------------------------------------------------------------------------
if doc_col is None:
    uploaded_file = st.file_uploader(
        "Upload a handwritten pharmaceutical document",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Supported: PDF, PNG, JPG - Batch Manufacturing Records, QC Inspection Forms",
    )
else:
    with doc_col:
        st.markdown('<p class="section-label">Document Preview</p>', unsafe_allow_html=True)

        doc_name_lower = (st.session_state.document_name or "").lower()
        doc_bytes = st.session_state.document_bytes

        if doc_name_lower.endswith(".pdf"):
            b64_pdf = base64.b64encode(doc_bytes).decode("utf-8")
            st.markdown(
                f'<iframe src="data:application/pdf;base64,{b64_pdf}" '
                f'width="100%" height="600" style="border:1px solid var(--border-default); '
                f'border-radius:var(--radius-md);"></iframe>',
                unsafe_allow_html=True,
            )
        else:
            st.image(doc_bytes, use_container_width=True)

        # Re-upload option
        uploaded_file = st.file_uploader(
            "Replace document",
            type=["pdf", "png", "jpg", "jpeg"],
            help="Upload a different document",
            key="replace_uploader",
        )

if uploaded_file is not None:
    new_upload = (
        st.session_state.document_name != uploaded_file.name
        or st.session_state.document_bytes is None
    )
    if new_upload:
        file_bytes = uploaded_file.getvalue()
        st.session_state.document_bytes = file_bytes
        st.session_state.document_name = uploaded_file.name
        st.session_state.document_path = uploaded_file.name
        st.session_state.conversation_history = []
        st.session_state.extracted_data = None
        st.session_state.review_status = None
        st.session_state.validation_report = None
        st.session_state.corrections = {}
        st.session_state.doc_hash = persistence.compute_hash(file_bytes)
        # Page count for PDFs
        if uploaded_file.name.lower().endswith(".pdf"):
            try:
                st.session_state.page_count = get_page_count(file_bytes)
            except Exception:
                st.session_state.page_count = None
        else:
            st.session_state.page_count = 1
        log_audit(f"Upload: {uploaded_file.name}", {
            "hash": st.session_state.doc_hash,
            "size_bytes": len(file_bytes),
            "pages": st.session_state.page_count,
        })
        st.rerun()

# ---------------------------------------------------------------------------
# Chat area (right column when doc is loaded, full width otherwise)
# ---------------------------------------------------------------------------
_chat_target = chat_col if chat_col is not None else st.container()

with _chat_target:
    # Display conversation history
    for msg in st.session_state.conversation_history:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                render_response(msg["content"])
            else:
                st.markdown(msg["content"])

# Chat input (always at page level -- Streamlit requires it outside columns)
if prompt := st.chat_input("Ask about the uploaded document - e.g. 'Extract all fields as JSON'"):
    if st.session_state.document_bytes is None:
        st.error("Please upload a document first.")
    else:
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        log_audit(f"Query: {prompt[:50]}...")

        with st.spinner("Analysing document..."):
            try:
                response = send_question(
                    prompt, st.session_state.document_bytes,
                    st.session_state.conversation_history,
                )
                st.session_state.conversation_history.append(
                    {"role": "assistant", "content": response}
                )
                st.session_state.extraction_count += 1

                # Cache extracted JSON if parseable
                parsed = extract_json_from_response(response)
                if parsed:
                    st.session_state.extracted_data = parsed
                    # Run Python-side validation
                    val_report = validator.validate(parsed)
                    st.session_state.validation_report = val_report
                    # Persist to disk
                    persistence.save_extraction(
                        st.session_state.document_name or "unknown",
                        st.session_state.doc_hash or "",
                        model_id, parsed,
                        {"principles": val_report.principles, "composite": val_report.composite_confidence},
                        {"input": st.session_state.total_input_tokens, "output": st.session_state.total_output_tokens},
                    )
                    persistence.save_validation(
                        st.session_state.document_name or "unknown",
                        st.session_state.doc_hash or "",
                        {"principles": val_report.principles, "flagged": val_report.flagged_for_review},
                    )
                    persistence.save_model_metrics(
                        model_id, "bmr", val_report.composite_confidence,
                        len(val_report.all_confidences),
                        sum(1 for i in val_report.issues if i.severity in ("high", "critical")),
                    )

                log_audit(f"Extraction OK (model={model_id})", {
                    "tokens_in": st.session_state.total_input_tokens,
                    "tokens_out": st.session_state.total_output_tokens,
                })

            except TimeoutError:
                st.error("The agent is taking longer than expected. Please try again.")
            except Exception as exc:
                st.error(f"Error: {exc}")
                log_audit(f"Error: {exc}")

        st.rerun()

# ---------------------------------------------------------------------------
# Post-extraction tools: ALCOA+ Report | Export | Confidence
# ---------------------------------------------------------------------------
if st.session_state.extracted_data and st.session_state.document_bytes:
    st.markdown('<div class="divider-gradient"></div>', unsafe_allow_html=True)

    tool_tabs = st.tabs(["ALCOA+ Compliance", "Monitoring", "Corrections", "Export Data", "Quick Prompts"])

    # Use the validator for all analysis
    val_rpt = st.session_state.validation_report
    if val_rpt is None:
        val_rpt = validator.validate(st.session_state.extracted_data)
        st.session_state.validation_report = val_rpt

    data = st.session_state.extracted_data
    raw_fields = data if not isinstance(data, dict) else data.get("batch_record", data.get("extracted_fields", data))

    # -- ALCOA+ Compliance Report (full 9 principles via validator) --
    with tool_tabs[0]:
        st.markdown(
            f'<div class="alcoa-card"><h4>ALCOA+ Compliance Report '
            f'({val_rpt.pass_count}/{val_rpt.total_principles} principles met)</h4>',
            unsafe_allow_html=True,
        )
        for name, passed in val_rpt.principles.items():
            desc_map = {
                "Attributable": "Every entry has operator identification",
                "Legible": f"All fields confidence >= {config_loader.get_nested('confidence_thresholds', 'standard_fields', default=0.70)}",
                "Contemporaneous": "Timestamps present, valid, and within shift hours",
                "Original": "Source document preserved with page references",
                "Accurate": f"Critical fields confidence >= {config_loader.get_nested('confidence_thresholds', 'critical_fields', default=0.90)}",
                "Complete": "All required fields present (no nulls)",
                "Consistent": "No contradictory data or anomalies detected",
                "Enduring": "Data persisted in immutable audit log on disk",
                "Available": "Data accessible for review, export, and API",
            }
            status = "pass" if passed else "warn"
            label = "PASS" if passed else "FAIL"
            st.markdown(
                f'<div class="alcoa-row">'
                f'<div><div class="alcoa-principle">{name}</div>'
                f'<div class="alcoa-desc">{desc_map.get(name, "")}</div></div>'
                f'<span class="alcoa-status alcoa-{status}">{label}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

        # Anomaly alerts with severity
        if val_rpt.anomalies:
            st.markdown("**Anomalies Detected:**")
            for a in val_rpt.anomalies:
                sev = a.severity.upper()
                if a.severity == "critical":
                    st.error(f"CRITICAL: {a.description} (field: {a.field})")
                elif a.severity == "high":
                    st.error(f"HIGH: {a.description} (field: {a.field})")
                elif a.severity == "medium":
                    st.warning(f"MEDIUM: {a.description} (field: {a.field})")
                else:
                    st.info(f"LOW: {a.description} (field: {a.field})")

        if val_rpt.low_confidence_fields:
            st.markdown("**Low-Confidence Fields:**")
            for field_name, conf in val_rpt.low_confidence_fields:
                st.warning(f"`{field_name}` -- confidence: {conf:.2f}")

        if val_rpt.issues:
            with st.expander(f"All Validation Issues ({len(val_rpt.issues)})"):
                for issue in val_rpt.issues:
                    st.text(f"[{issue.severity.upper()}] {issue.principle}: {issue.field} - {issue.description}")

    # -- Monitoring Dashboard --
    with tool_tabs[1]:
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Composite Confidence", f"{val_rpt.composite_confidence:.1%}" if val_rpt.composite_confidence else "N/A")
        with m2:
            st.metric("Fields Extracted", str(len(val_rpt.all_confidences)))
        with m3:
            st.metric("Flagged for Review", "Yes" if val_rpt.flagged_for_review else "No")
        with m4:
            st.metric("Null Fields", str(len(val_rpt.null_fields)))

        # Token usage
        t1, t2, t3, t4 = st.columns(4)
        with t1:
            st.metric("Input Tokens", f"{st.session_state.total_input_tokens:,}")
        with t2:
            st.metric("Output Tokens", f"{st.session_state.total_output_tokens:,}")
        with t3:
            pages = st.session_state.page_count
            st.metric("Pages", str(pages) if pages else "N/A")
        with t4:
            session_start = datetime.fromisoformat(st.session_state.session_start)
            elapsed_hrs = max((datetime.now(timezone.utc) - session_start).total_seconds() / 3600, 0.001)
            docs_per_hr = st.session_state.extraction_count / elapsed_hrs
            st.metric("Docs/Hour", f"{docs_per_hr:.1f}")

        if val_rpt.all_confidences:
            st.markdown('<p class="section-label">Field Confidence Distribution</p>', unsafe_allow_html=True)
            buckets = {"0.9-1.0": 0, "0.7-0.9": 0, "< 0.7": 0}
            for c in val_rpt.all_confidences:
                if c >= 0.90:
                    buckets["0.9-1.0"] += 1
                elif c >= 0.70:
                    buckets["0.7-0.9"] += 1
                else:
                    buckets["< 0.7"] += 1
            st.bar_chart(buckets)

            if val_rpt.composite_confidence and val_rpt.composite_confidence < 0.70:
                st.error("ALERT: Composite confidence below 0.70. Manual review required.")
            elif val_rpt.composite_confidence and val_rpt.composite_confidence < 0.90:
                st.warning("Some critical fields may need human verification.")
            else:
                st.success("All extracted fields meet confidence thresholds.")

        # Historical model metrics
        hist_metrics = persistence.get_model_metrics()
        if len(hist_metrics) > 1:
            st.markdown('<p class="section-label">Model Accuracy Trend</p>', unsafe_allow_html=True)
            trend = [m["composite_confidence"] for m in hist_metrics if m.get("composite_confidence")]
            st.line_chart(trend)

        # Approve / Reject
        st.markdown('<p class="section-label">Review Decision</p>', unsafe_allow_html=True)
        rcol1, rcol2, rcol3 = st.columns([1, 1, 2])
        with rcol1:
            if st.button("Approve", type="primary", use_container_width=True):
                st.session_state.review_status = "approved"
                log_audit("Review: APPROVED")
                st.rerun()
        with rcol2:
            if st.button("Reject", type="secondary", use_container_width=True):
                st.session_state.review_status = "rejected"
                log_audit("Review: REJECTED")
                st.rerun()
        with rcol3:
            status = st.session_state.review_status
            if status == "approved":
                st.success("Batch record APPROVED")
            elif status == "rejected":
                st.error("Batch record REJECTED")
            else:
                st.info("Pending review")

    # -- Corrections (Human Review) --
    with tool_tabs[2]:
        st.markdown("Edit extracted fields below. Corrections are logged to the audit trail and saved as training data.")
        if isinstance(raw_fields, dict):
            for key, val in raw_fields.items():
                if isinstance(val, dict) and "value" in val:
                    conf = val.get("confidence", 1.0)
                    color = "red" if conf < 0.70 else ("orange" if conf < 0.90 else "green")
                    current = st.session_state.corrections.get(key, val["value"])
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        new_val = st.text_input(
                            f"{key} (conf: {conf:.2f})",
                            value=str(current) if current is not None else "",
                            key=f"corr_{key}",
                        )
                    with col_b:
                        st.markdown(f'<span style="color:{color};font-weight:700;">{conf:.2f}</span>', unsafe_allow_html=True)
                    if new_val != str(val["value"] or ""):
                        st.session_state.corrections[key] = new_val

            if st.button("Save Corrections"):
                for field_key, new_value in st.session_state.corrections.items():
                    original = raw_fields.get(field_key, {}).get("value") if isinstance(raw_fields.get(field_key), dict) else raw_fields.get(field_key)
                    if str(original) != str(new_value):
                        persistence.save_correction(
                            st.session_state.document_name or "unknown",
                            st.session_state.doc_hash or "",
                            field_key, original, new_value,
                        )
                st.success(f"Saved {len(st.session_state.corrections)} correction(s)")
                log_audit("Corrections saved", {"count": len(st.session_state.corrections)})
        else:
            st.info("Extract data with confidence scores first to enable field-level corrections.")

    # -- Export Data --
    with tool_tabs[3]:
        ecol1, ecol2, ecol3 = st.columns(3)
        with ecol1:
            json_str = json.dumps(st.session_state.extracted_data, indent=2)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name=f"{st.session_state.document_name or 'extraction'}.json",
                mime="application/json",
            )
        with ecol2:
            flat = st.session_state.extracted_data
            if isinstance(flat, dict):
                flat = flat.get("batch_record", flat.get("extracted_fields", flat))
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["Field", "Value", "Confidence", "Source Page"])
            if isinstance(flat, dict):
                for k, v in flat.items():
                    if isinstance(v, dict) and "value" in v:
                        writer.writerow([k, v["value"], v.get("confidence", ""), v.get("source_page", "")])
                    elif isinstance(v, (list, dict)):
                        writer.writerow([k, json.dumps(v), "", ""])
                    else:
                        writer.writerow([k, v, "", ""])
            st.download_button(
                label="Download CSV",
                data=buf.getvalue(),
                file_name=f"{st.session_state.document_name or 'extraction'}.csv",
                mime="text/csv",
            )
        with ecol3:
            # Audit trail export (both JSON and CSV)
            all_audit = persistence.get_audit_trail()
            if all_audit:
                st.download_button(
                    label="Audit Trail (JSON)",
                    data=json.dumps(all_audit, indent=2),
                    file_name="audit_trail.json",
                    mime="application/json",
                )

        # Training data export
        training_data = persistence.export_training_jsonl()
        if training_data.strip():
            st.download_button(
                label="Training Data (JSONL)",
                data=training_data,
                file_name="training_corrections.jsonl",
                mime="application/jsonl",
            )

    # -- Quick Prompts --
    with tool_tabs[4]:
        prompts = [
            "Extract all fields from this batch manufacturing record as structured JSON with confidence scores (0.0-1.0) for each field, source_page numbers, composite_confidence, and flag any anomalies with severity levels (low/medium/high/critical)",
            "What is the batch number and product name?",
            "List all ingredients with their weights, units, and lot numbers",
            "Are there any missing or illegible fields? List them with severity",
            "Flag any anomalies: missing signatures, timestamps outside shift hours (06:00-22:00), quantity deviations > 5%",
            "Generate a full ALCOA+ compliance assessment covering all 9 principles",
        ]
        for p in prompts:
            st.code(p, language=None)


# ---------------------------------------------------------------------------
# Empty state - onboarding
# ---------------------------------------------------------------------------
if st.session_state.document_bytes is None and not st.session_state.conversation_history:
    st.markdown('<div class="divider-gradient"></div>', unsafe_allow_html=True)

    st.markdown("### Getting Started")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            '<div class="onboard-card stagger-1">'
            "<h4>Upload & Extract</h4>"
            "<p><strong>Step 1:</strong> Upload a handwritten BMR or QC document above</p>"
            "<p><strong>Step 2:</strong> Ask questions like:</p>"
            "<ul>"
            '<li><em>"Extract all fields as JSON"</em></li>'
            '<li><em>"What is the batch number?"</em></li>'
            '<li><em>"List all ingredients and weights"</em></li>'
            "</ul>"
            "</div>",
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            '<div class="onboard-card stagger-2">'
            "<h4>Validate & Export</h4>"
            "<p><strong>Step 3:</strong> Review the ALCOA+ compliance report</p>"
            "<p><strong>Step 4:</strong> Export to JSON or CSV</p>"
            "<p><strong>Test data</strong> is in<br>"
            "<code>workshop/test-data/bmr/</code></p>"
            "<p>Includes clean, messy, partial, and real scanned documents.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
