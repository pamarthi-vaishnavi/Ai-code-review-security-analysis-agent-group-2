"""
Turns a flat list of Findings into a severity breakdown and a single
0-100 "code health score" used throughout the UI and the exported report.

The scoring model is a transparent weighted-deduction formula (documented
in README.md) rather than a black box, so reviewers can see exactly why a
score landed where it did.
"""
from __future__ import annotations
from models.schemas import AnalysisReport, Finding, SeverityBreakdown

def compute_code_health_score(findings: list[Finding]) -> float:
    if not findings:
        return 100.0
    penalty = sum(f.severity.weight * f.confidence for f in findings)
    score = 100.0 - penalty
    return round(max(0.0, min(100.0, score)), 1)

def deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    """Collapse near-duplicate findings (same file/line/title from
    different tools) so the report isn't noisy."""
    seen: set[tuple] = set()
    unique: list[Finding] = []
    for f in findings:
        key = (f.file_name, f.line_start, f.title.lower().strip())
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)
    return unique

def build_report(
    submission_id: str,
    language: str,
    source_name: str,
    findings: list[Finding],
    pr_summary: str = "",
) -> AnalysisReport:
    deduped = deduplicate_findings(findings)
    return AnalysisReport(
        submission_id=submission_id,
        language=language,
        source_name=source_name,
        findings=deduped,
        severity_breakdown=SeverityBreakdown.from_findings(deduped),
        code_health_score=compute_code_health_score(deduped),
        pr_summary=pr_summary,
    )
