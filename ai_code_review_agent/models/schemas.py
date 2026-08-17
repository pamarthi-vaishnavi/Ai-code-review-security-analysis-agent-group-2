"""
Typed data contracts shared by every agent, the static analyzers, the
report exporter and the Streamlit UI. Keeping one shared schema means no
agent has to guess the shape of another agent's output.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    @property
    def weight(self) -> int:
        return {
            Severity.CRITICAL: 40,
            Severity.HIGH: 20,
            Severity.MEDIUM: 10,
            Severity.LOW: 4,
            Severity.INFO: 1,
        }[self]


class FindingCategory(str, Enum):
    CODE_SMELL = "CODE_SMELL"
    DESIGN_ANTI_PATTERN = "DESIGN_ANTI_PATTERN"
    COMPLEXITY = "COMPLEXITY"
    SECURITY_VULNERABILITY = "SECURITY_VULNERABILITY"
    BEST_PRACTICE = "BEST_PRACTICE"


class Finding(BaseModel):
    """A single issue raised by any agent or static tool."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    source: str = Field(description="Which agent/tool produced this finding")
    category: FindingCategory
    title: str
    description: str
    severity: Severity
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    file_name: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str | None = None
    cwe_id: str | None = Field(default=None, description="e.g. CWE-89")
    owasp_category: str | None = Field(
        default=None, description="e.g. A03:2021-Injection"
    )
    remediation_summary: str | None = None
    remediation_code: str | None = None
    references: list[str] = Field(default_factory=list)


class FindingsList(BaseModel):
    """Structured-output envelope used when asking an LLM for findings."""

    findings: list[Finding]


class RemediationPatch(BaseModel):
    finding_id: str
    explanation: str
    corrected_code: str
    best_practice_notes: str | None = None


class CodeSubmission(BaseModel):
    submission_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    language: Literal["python", "java"]
    source_name: str = "pasted_code"
    code: str
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SeverityBreakdown(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0

    @classmethod
    def from_findings(cls, findings: list[Finding]) -> "SeverityBreakdown":
        counts = {s: 0 for s in Severity}
        for f in findings:
            counts[f.severity] += 1
        return cls(
            critical=counts[Severity.CRITICAL],
            high=counts[Severity.HIGH],
            medium=counts[Severity.MEDIUM],
            low=counts[Severity.LOW],
            info=counts[Severity.INFO],
        )


class AnalysisReport(BaseModel):
    """Final merged output of the whole multi-agent pipeline."""

    submission_id: str
    language: str
    source_name: str
    findings: list[Finding] = Field(default_factory=list)
    severity_breakdown: SeverityBreakdown = Field(default_factory=SeverityBreakdown)
    code_health_score: float = 100.0
    pr_summary: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def sorted_findings(self) -> list[Finding]:
        order = {s: i for i, s in enumerate(Severity)}
        return sorted(self.findings, key=lambda f: order[f.severity])
