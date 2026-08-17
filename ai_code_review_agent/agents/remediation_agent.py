"""
Milestone 3, item 1: "Build Remediation Agent -- generates specific fix
recommendations with corrected code examples and best practice explanations
for each flagged finding."
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from llm.provider import get_chat_model
from models.schemas import Finding, RemediationPatch
from rag.knowledge_base import format_context_block, retrieve_context


class _RemediationLLMOutput(BaseModel):
    """What we ask the LLM to produce -- deliberately excludes
    `finding_id`, which we set ourselves, so the model never has to
    invent/guess an id (and structured-output schemas shouldn't require
    fields the model has no way to know)."""

    explanation: str
    corrected_code: str
    best_practice_notes: str | None = None


SYSTEM_PROMPT = """You are a secure-coding mentor. A code review tool flagged \
the finding below in {language} code. Write a precise, actionable fix.

Ground your explanation in this secure-coding guidance when relevant:
{context}

Finding: {title}
Severity: {severity}
Description: {description}
Offending code:
```{language}
{snippet}
```

Respond with:
- `explanation`: 2-4 sentences on WHY this is a problem and HOW the fix addresses it
- `corrected_code`: a minimal corrected code snippet (same language) that fixes the issue
- `best_practice_notes`: one short general best-practice tip related to this finding class"""


def _remediate_one(finding: Finding, language: str) -> RemediationPatch | None:
    if not finding.description:
        return None
    context_chunks = retrieve_context(f"{finding.title} {finding.owasp_category or ''}", k=3)
    llm = get_chat_model().with_structured_output(_RemediationLLMOutput)
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT)])
    chain = prompt | llm
    try:
        raw: _RemediationLLMOutput = chain.invoke(
            {
                "language": language,
                "context": format_context_block(context_chunks),
                "title": finding.title,
                "severity": finding.severity.value,
                "description": finding.description,
                "snippet": finding.code_snippet or "(snippet unavailable, use description + line number)",
            }
        )
        return RemediationPatch(
            finding_id=finding.id,
            explanation=raw.explanation,
            corrected_code=raw.corrected_code,
            best_practice_notes=raw.best_practice_notes,
        )
    except Exception:
        return None


def remediate(
    findings: list[Finding],
    language: str,
    max_workers: int = 4,
    max_remediations: int = 20,
) -> list[Finding]:
    """Fill in `remediation_summary` / `remediation_code` on each finding that
    doesn't already have one. Runs remediation calls concurrently since each
    finding is an independent LLM call.

    Only CRITICAL/HIGH/MEDIUM findings are remediated by the LLM by default
    (capped at `max_remediations`) to keep latency/cost bounded; LOW/INFO
    findings get a lightweight static note instead since they're rarely
    security-critical.
    """
    from models.schemas import Severity

    priority = [
        f
        for f in findings
        if f.remediation_summary is None
        and f.severity in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM)
    ][:max_remediations]
    priority_ids = {f.id for f in priority}

    for f in findings:
        if f.remediation_summary is None and f.id not in priority_ids:
            f.remediation_summary = (
                "Low-priority finding -- address as part of routine cleanup. "
                "See description above for guidance."
            )

    targets = priority
    if not targets:
        return findings

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_remediate_one, f, language): f for f in targets}
        for future in as_completed(futures):
            finding = futures[future]
            patch = future.result()
            if patch:
                finding.remediation_summary = patch.explanation
                finding.remediation_code = patch.corrected_code
                if patch.best_practice_notes:
                    finding.references.append(patch.best_practice_notes)

    return findings
