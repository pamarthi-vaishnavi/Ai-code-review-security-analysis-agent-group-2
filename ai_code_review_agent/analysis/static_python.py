"""
Deterministic, library-backed static analysis for Python source.

- `pylint`  -> code smells, style/design issues, unused code, complexity
- `bandit`  -> OWASP-relevant security issues (SQLi patterns, hardcoded
               secrets, insecure deserialization, weak crypto, eval/exec, ...)
- `radon`   -> cyclomatic complexity + maintainability index

These are real, industry-standard tools -- results are merged into the same
`Finding` schema the LLM agents use, so static findings and LLM findings
render identically in the UI and report.
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from models.schemas import Finding, FindingCategory, Severity

_PYLINT_SEVERITY = {
    "error": Severity.HIGH,
    "warning": Severity.MEDIUM,
    "convention": Severity.LOW,
    "refactor": Severity.MEDIUM,
    "fatal": Severity.CRITICAL,
    "info": Severity.INFO,
}

_BANDIT_SEVERITY = {
    "HIGH": Severity.CRITICAL,
    "MEDIUM": Severity.HIGH,
    "LOW": Severity.MEDIUM,
}


def validate_syntax(code: str) -> tuple[bool, str | None]:
    """Fast syntax gate used by the Code Submission Module before any
    agent is invoked."""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as exc:
        return False, f"Line {exc.lineno}: {exc.msg}"


def _write_temp_file(code: str, suffix: str = ".py") -> Path:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    tmp.write(code)
    tmp.close()
    return Path(tmp.name)


def run_pylint(code: str, file_label: str = "submitted_code.py") -> list[Finding]:
    """Run pylint's JSON reporter and translate messages into Findings."""
    path = _write_temp_file(code)
    findings: list[Finding] = []
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pylint",
                str(path),
                "--output-format=json",
                "--disable=C0114,C0116,C0115",  # skip missing-docstring noise
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        raw = proc.stdout.strip()
        if not raw:
            return []
        messages = json.loads(raw)
        for msg in messages:
            category = (
                FindingCategory.COMPLEXITY
                if msg.get("type") == "refactor"
                else FindingCategory.CODE_SMELL
            )
            findings.append(
                Finding(
                    source="pylint",
                    category=category,
                    title=f"{msg.get('symbol', msg.get('message-id'))}",
                    description=msg.get("message", ""),
                    severity=_PYLINT_SEVERITY.get(msg.get("type"), Severity.LOW),
                    confidence=0.9,
                    file_name=file_label,
                    line_start=msg.get("line"),
                    line_end=msg.get("line"),
                    references=["https://pylint.readthedocs.io/en/stable/user_guide/messages/"],
                )
            )
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    finally:
        path.unlink(missing_ok=True)
    return findings


def run_bandit(code: str, file_label: str = "submitted_code.py") -> list[Finding]:
    """Run bandit (OWASP-oriented Python security linter)."""
    path = _write_temp_file(code)
    findings: list[Finding] = []
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "bandit", "-f", "json", "-q", str(path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if not proc.stdout.strip():
            return []
        data = json.loads(proc.stdout)
        for res in data.get("results", []):
            findings.append(
                Finding(
                    source="bandit",
                    category=FindingCategory.SECURITY_VULNERABILITY,
                    title=res.get("test_name", res.get("test_id", "Security issue")),
                    description=res.get("issue_text", ""),
                    severity=_BANDIT_SEVERITY.get(
                        res.get("issue_severity", "MEDIUM"), Severity.MEDIUM
                    ),
                    confidence={"HIGH": 0.9, "MEDIUM": 0.65, "LOW": 0.4}.get(
                        res.get("issue_confidence", "MEDIUM"), 0.6
                    ),
                    file_name=file_label,
                    line_start=res.get("line_number"),
                    line_end=res.get("line_number"),
                    code_snippet=res.get("code"),
                    cwe_id=f"CWE-{res['issue_cwe']['id']}"
                    if isinstance(res.get("issue_cwe"), dict) and res["issue_cwe"].get("id")
                    else None,
                    references=[res.get("more_info", "")] if res.get("more_info") else [],
                )
            )
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    finally:
        path.unlink(missing_ok=True)
    return findings


def run_radon_complexity(code: str, file_label: str = "submitted_code.py") -> list[Finding]:
    """Flag functions whose cyclomatic complexity exceeds a healthy
    threshold (radon's own grading scale, not an invented one)."""
    findings: list[Finding] = []
    try:
        from radon.complexity import cc_visit
        from radon.visitors import ComplexityVisitor  # noqa: F401 (import validates availability)

        blocks = cc_visit(code)
        for block in blocks:
            if block.complexity >= 11:  # radon rank D/E/F starts at 11+
                rank = "high" if block.complexity < 21 else "very high"
                findings.append(
                    Finding(
                        source="radon",
                        category=FindingCategory.COMPLEXITY,
                        title=f"High cyclomatic complexity in '{block.name}'",
                        description=(
                            f"Cyclomatic complexity is {block.complexity} ({rank}). "
                            "Consider decomposing this function into smaller units."
                        ),
                        severity=Severity.MEDIUM if block.complexity < 21 else Severity.HIGH,
                        confidence=0.85,
                        file_name=file_label,
                        line_start=block.lineno,
                        line_end=getattr(block, "endline", block.lineno),
                    )
                )
    except ImportError:
        pass
    return findings


def run_all(code: str, file_label: str = "submitted_code.py") -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(run_pylint(code, file_label))
    findings.extend(run_bandit(code, file_label))
    findings.extend(run_radon_complexity(code, file_label))
    return findings
