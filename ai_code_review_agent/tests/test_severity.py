from analysis.severity import build_report, compute_code_health_score, deduplicate_findings
from models.schemas import Finding, FindingCategory, Severity


def _finding(severity: Severity, title: str = "issue", line: int = 1, confidence: float = 1.0) -> Finding:
    return Finding(
        source="test",
        category=FindingCategory.CODE_SMELL,
        title=title,
        description="test finding",
        severity=severity,
        confidence=confidence,
        file_name="sample.py",
        line_start=line,
    )


def test_score_is_100_with_no_findings():
    assert compute_code_health_score([]) == 100.0


def test_score_decreases_with_findings():
    findings = [_finding(Severity.HIGH), _finding(Severity.MEDIUM)]
    score = compute_code_health_score(findings)
    assert score < 100.0


def test_score_never_goes_below_zero():
    findings = [_finding(Severity.CRITICAL, title=f"issue-{i}", line=i) for i in range(20)]
    score = compute_code_health_score(findings)
    assert score == 0.0


def test_deduplicate_findings_collapses_same_line_and_title():
    findings = [
        _finding(Severity.HIGH, title="SQL Injection", line=5),
        _finding(Severity.HIGH, title="sql injection", line=5),  # same key, different case
        _finding(Severity.HIGH, title="SQL Injection", line=9),
    ]
    deduped = deduplicate_findings(findings)
    assert len(deduped) == 2


def test_build_report_computes_breakdown():
    findings = [_finding(Severity.CRITICAL), _finding(Severity.LOW, title="b", line=2)]
    report = build_report("sub123", "python", "sample.py", findings)
    assert report.severity_breakdown.critical == 1
    assert report.severity_breakdown.low == 1
    assert report.code_health_score < 100.0
