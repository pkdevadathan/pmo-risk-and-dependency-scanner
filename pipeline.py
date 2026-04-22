import json
import os
import re
from typing import Any

from schema import AnalysisResult, DependencyItem, RiskItem
from taxonomy import LIKELIHOOD_LEVELS, RISK_CATEGORIES, SEVERITY_LEVELS


SYSTEM_PROMPT = """You are a senior program manager assistant for a PMO. Your job is to read project
documentation and surface risks and cross-team dependencies that humans might miss under time pressure.

Rules:
- Only infer from the text provided. If something is speculative, say so in the description.
- Use the exact risk category strings from the taxonomy list provided in the user message.
- Prefer fewer, higher-quality items over a long generic list.
- For dependencies, name concrete work streams, systems, or milestones when the text supports it.
- suggested_owner_role should be a role (e.g. "Regulatory Affairs Lead"), not a invented person name.
- Return valid JSON matching the schema exactly. No markdown fences."""


def _mock_analysis(text: str) -> AnalysisResult:
    """Deterministic offline demo when no API key is configured."""
    lower = text.lower()
    risks: list[RiskItem] = []
    deps: list[DependencyItem] = []

    if "ind" in lower or "nda" in lower or "regulatory" in lower or "fda" in lower:
        risks.append(
            RiskItem(
                title="Regulatory submission path not fully locked",
                category="Regulatory / compliance",
                description=(
                    "Documents reference IND/NDA or regulatory milestones but timing or "
                    "pre-requisite studies may be implicit—confirm submission readiness criteria."
                ),
                likelihood="Medium",
                impact="Critical",
                suggested_owner_role="Regulatory Affairs Lead",
                mitigation_hint="Run a submission readiness checklist workshop with QA and CMC.",
                source_snippet=_snippet(text, ["ind", "nda", "regulatory", "fda"]),
            )
        )
    if "vendor" in lower or "cro" in lower or "third party" in lower:
        risks.append(
            RiskItem(
                title="Third-party delivery concentration",
                category="Vendor / third party",
                description="Key deliverables appear tied to external vendors; confirm backup plans and SLA visibility.",
                likelihood="High",
                impact="High",
                suggested_owner_role="Procurement / Vendor Manager",
                mitigation_hint="Add joint governance cadence and milestone-based exit criteria.",
                source_snippet=_snippet(text, ["vendor", "cro", "third party"]),
            )
        )
    if re.search(r"\b(q[1-4]|h[12])\b", lower) or "milestone" in lower:
        risks.append(
            RiskItem(
                title="Schedule compression around named milestones",
                category="Schedule / timeline",
                description="Named quarters or milestones without buffer may hide integration and review time.",
                likelihood="Medium",
                impact="High",
                suggested_owner_role="Program Manager",
                mitigation_hint="Overlay critical path and add explicit review gates in the plan.",
                source_snippet=_snippet(text, ["milestone", "q1", "q2", "q3", "q4", "h1", "h2"]),
            )
        )
    if "depends" in lower or "blocked" in lower or "prerequisite" in lower:
        deps.append(
            DependencyItem(
                predecessor="Upstream work package (from text)",
                successor="Downstream milestone or handoff",
                description="Text signals a sequencing constraint; validate exact owners and dates with teams.",
                if_slipped_impact="Downstream testing, reporting, or submission dates may slip in parallel.",
            )
        )

    if not risks:
        risks.append(
            RiskItem(
                title="Limited explicit risk register in source bundle",
                category="Stakeholder / communication",
                description="Bundle reads as narrative/status without a consolidated risk log—blind spots are more likely.",
                likelihood="Medium",
                impact="Medium",
                suggested_owner_role="PMO Lead",
                mitigation_hint="Introduce a lightweight risk review in weekly program forums.",
                source_snippet=text[:240].replace("\n", " ") + ("…" if len(text) > 240 else ""),
            )
        )

    questions = []
    if "tbd" in lower or "tbc" in lower:
        questions.append("Several items marked TBD/TBC—who owns resolution and by when?")
    if not deps:
        questions.append("Are there undocumented cross-team handoffs (data, samples, releases) not captured here?")

    summary = (
        "Offline demo mode (no LLM API key): pattern-based scan of the document bundle. "
        "With an API key, the same UI runs a full LLM pass using your taxonomy. "
        f"Surfaced {len(risks)} risk(s) and {len(deps)} dependency cluster(s)."
    )
    return AnalysisResult(
        executive_summary=summary,
        risks=risks,
        dependencies=deps,
        open_questions_for_pm=questions,
    )


def _snippet(text: str, keywords: list[str]) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        low = line.lower()
        if any(k in low for k in keywords):
            return line.strip()[:400]
    return text[:400].replace("\n", " ") + ("…" if len(text) > 400 else "")


def _openai_client():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(api_key=key)


def analyze_documents(bundle_text: str, model: str = "gpt-4o-mini") -> tuple[AnalysisResult, str]:
    """
    Returns (result, mode_label).
    mode_label is 'live_llm' or 'offline_demo'.
    """
    client = _openai_client()
    if client is None:
        return _mock_analysis(bundle_text), "offline_demo"

    taxonomy_block = json.dumps(
        {
            "risk_categories": RISK_CATEGORIES,
            "severity_levels": SEVERITY_LEVELS,
            "likelihood_levels": LIKELIHOOD_LEVELS,
        },
        indent=2,
    )

    schema_hint = AnalysisResult.model_json_schema()
    user_msg = f"""Taxonomy and enums:
{taxonomy_block}

Target JSON schema (produce JSON that validates against this structure):
{json.dumps(schema_hint, indent=2)}

--- DOCUMENT BUNDLE START ---
{bundle_text[:120_000]}
--- DOCUMENT BUNDLE END ---
"""

    completion = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    raw = completion.choices[0].message.content or "{}"
    data: dict[str, Any] = json.loads(raw)
    result = AnalysisResult.model_validate(data)
    return result, "live_llm"
