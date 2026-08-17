"""
Milestone 3, item 2: "Build PR Summary Agent -- compiles all agent outputs
into a structured pull request style review summary with executive
overview, severity breakdown, and prioritized fix list."
"""
from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from llm.provider import get_chat_model
from models.schemas import Finding, SeverityBreakdown

SYSTEM_PROMPT = """You are writing a pull-request style code review summary \
for a {language} submission, in Markdown. You are given the full list of \
findings from a Code Analysis Agent and a Security Vulnerability Agent, \
already deduplicated and severity-scored. The overall code health score is \
{health_score}/100.

Severity breakdown: {breakdown}

Findings (JSON-ish list, one per line):
{findings_block}

Write the summary with these sections, in this order:
## Executive Overview
2-4 sentences: what does this code do, and what's the overall risk/quality \
posture? Be direct, not generic.

## Severity Breakdown
A short bullet list restating the counts above with one line of context.

## Prioritized Fix List
A numbered list, most severe first, of the top issues to fix -- each item \
one line, referencing the finding title and file/line.

## Notes
Anything else worth flagging (patterns across findings, systemic issues).

Keep the whole summary concise and skimmable -- this is read by a busy \
developer deciding whether to merge. Do not invent findings not in the list."""


def _findings_block(findings: list[Finding]) -> str:
    if not findings:
        return "(No findings -- code looks clean.)"
    lines = []
    for f in findings:
        loc = f"{f.file_name or 'code'}:{f.line_start or '?'}"
        lines.append(f"- [{f.severity.value}] {f.title} ({loc}) -- {f.description[:150]}")
    return "\n".join(lines)


def summarize(
    findings: list[Finding],
    language: str,
    health_score: float,
    breakdown: SeverityBreakdown,
) -> str:
    try:
        llm = get_chat_model()
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "Generate the PR review summary now."),
            ])
        chain = prompt | llm | StrOutputParser()
        return chain.invoke(
            {
                "language": language,
                "health_score": health_score,
                "breakdown": breakdown.model_dump(),
                "findings_block": _findings_block(findings),
            }
        )
    except Exception as exc:
        return _fallback_summary(findings, health_score, breakdown, str(exc))


def _fallback_summary(
    findings: list[Finding], health_score: float, breakdown: SeverityBreakdown, error: str
) -> str:
    """Deterministic summary used if the LLM call fails, so the pipeline
    still produces a usable report."""
    lines = [
        "## Executive Overview",
        f"_LLM summary unavailable ({error}). Showing an auto-generated overview._",
        f"Code health score: **{health_score}/100** across {len(findings)} findings.",
        "",
        "## Severity Breakdown",
        f"- Critical: {breakdown.critical}",
        f"- High: {breakdown.high}",
        f"- Medium: {breakdown.medium}",
        f"- Low: {breakdown.low}",
        f"- Info: {breakdown.info}",
        "",
        "## Prioritized Fix List",
    ]
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    for i, f in enumerate(sorted(findings, key=lambda x: order[x.severity.value])[:15], 1):
        lines.append(f"{i}. [{f.severity.value}] {f.title} ({f.file_name}:{f.line_start})")
    return "\n".join(lines)
