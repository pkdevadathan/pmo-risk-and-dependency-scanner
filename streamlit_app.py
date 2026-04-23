"""PMO Risk & Dependency Scanner — Streamlit demo for interviews."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from pipeline import analyze_documents
from taxonomy import RISK_CATEGORIES

st.set_page_config(page_title="PMO Risk & Dependency Scanner", layout="wide")

st.title("PMO Risk & Dependency Scanner")
st.caption(
    "Upload project docs or use samples. Output uses a fixed taxonomy — PMs review, not blindly trust."
)

with st.sidebar:
    st.subheader("How to run")
    st.markdown(
        "1. `cd pmo-risk-intelligence`\n\n"
        "2. `python3 -m venv .venv && source .venv/bin/activate`\n\n"
        "3. `pip install -r requirements.txt`\n\n"
        "4. `streamlit run streamlit_app.py`\n\n"
        "**Vercel:** connect this repo — the web UI uses FastAPI (`src/server.py`).\n\n"
        "**Optional:** `export OPENAI_API_KEY=...` for live LLM mode.\n\n"
        "**If pip hits SSL errors:**\n"
        "`pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt`\n\n"
        "**CLI only (no Streamlit):** `pip install -r requirements-minimal.txt` then `python cli.py`"
    )
    st.divider()
    st.subheader("Taxonomy (fixed)")
    for c in RISK_CATEGORIES:
        st.text(f"• {c}")

col_a, col_b = st.columns([1, 1])

with col_a:
    st.subheader("Inputs")
    model = st.selectbox("OpenAI model (live mode only)", ["gpt-4o-mini", "gpt-4o"], index=0)
    use_samples = st.toggle("Load built-in sample bundle", value=True)
    uploads = st.file_uploader(
        "Upload text documents (.txt) — optional, adds to bundle",
        type=["txt"],
        accept_multiple_files=True,
    )
    extra = st.text_area("Paste status notes, email thread, or charter excerpt", height=160)

bundle_parts: list[str] = []

if use_samples:
    try:
        base = Path(__file__).resolve().parent / "sample_docs"
        for name in sorted(p.name for p in base.glob("*.txt")):
            bundle_parts.append(f"### FILE: {name}\n" + (base / name).read_text(encoding="utf-8"))
    except OSError as e:
        st.warning(f"Could not load samples: {e}")

if uploads:
    for f in uploads:
        bundle_parts.append(f"### FILE: {f.name}\n" + f.getvalue().decode("utf-8", errors="replace"))

if extra.strip():
    bundle_parts.append("### PASTED TEXT\n" + extra.strip())

bundle = "\n\n".join(bundle_parts).strip()

with col_b:
    st.subheader("Analyze")
    go = st.button("Run scan", type="primary", disabled=not bundle)
    if not bundle:
        st.info("Add sample bundle, uploads, or pasted text to enable the scan.")

if go and bundle:
    with st.spinner("Analyzing document bundle…"):
        result, mode = analyze_documents(bundle, model=model)

    badge = "Live LLM" if mode == "live_llm" else "Offline demo (no API key)"
    st.success(f"Mode: **{badge}**")

    st.subheader("Executive summary")
    st.write(result.executive_summary)

    rcol, dcol = st.columns(2)
    with rcol:
        st.subheader(f"Risks ({len(result.risks)})")
        for i, r in enumerate(result.risks, start=1):
            with st.expander(f"{i}. {r.title} — {r.impact} impact", expanded=i <= 3):
                st.markdown(f"**Category:** {r.category}")
                st.markdown(f"**Likelihood:** {r.likelihood}")
                st.write(r.description)
                if r.source_snippet:
                    st.caption("Evidence")
                    st.code(r.source_snippet, language=None)
                if r.suggested_owner_role:
                    st.markdown(f"**Suggested owner (role):** {r.suggested_owner_role}")
                if r.mitigation_hint:
                    st.markdown(f"**Mitigation hint:** {r.mitigation_hint}")

    with dcol:
        st.subheader(f"Dependencies ({len(result.dependencies)})")
        if not result.dependencies:
            st.caption("No explicit dependency chains extracted — see open questions.")
        for i, d in enumerate(result.dependencies, start=1):
            with st.expander(f"{i}. {d.predecessor} → {d.successor}", expanded=i <= 2):
                st.write(d.description)
                if d.if_slipped_impact:
                    st.markdown(f"**If predecessor slips:** {d.if_slipped_impact}")

    st.subheader("Open questions for PM")
    for q in result.open_questions_for_pm:
        st.markdown(f"- {q}")
    if not result.open_questions_for_pm:
        st.caption("None flagged.")

    st.download_button(
        "Download JSON",
        data=json.dumps(result.model_dump(), indent=2),
        file_name="pmo_risk_scan.json",
        mime="application/json",
    )
