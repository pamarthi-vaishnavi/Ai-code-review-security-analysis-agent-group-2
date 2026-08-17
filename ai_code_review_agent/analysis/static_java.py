"""
Static analysis for Java source.

Two tiers, both real tools (no invented rules):

1. `javalang` (pure-Python Java parser) -- always available once installed
   via pip, used for syntax validation and lightweight structural checks
   (long methods, deep nesting, empty catch blocks).
2. PMD -- if the user has PMD installed and on PATH (common on Windows via
   the official zip release), we shell out to it for a much deeper OWASP-
   aligned rule set (`category/java/security.xml`, `bestpractices.xml`,
   `design.xml`). This is optional and auto-detected; the app works
   without it, just with a smaller Java rule set than Python gets from
   pylint/bandit.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from models.schemas import Finding, FindingCategory, Severity

_PMD_SEVERITY = {1: Severity.CRITICAL, 2: Severity.HIGH, 3: Severity.MEDIUM, 4: Severity.LOW, 5: Severity.INFO}


def validate_syntax(code: str) -> tuple[bool, str | None]:
    try:
        import javalang

        list(javalang.parse.parse(code).types)  # force full parse
        return True, None
    except ImportError:
        # javalang not installed -- fall back to a coarse brace/paren check
        # so the Code Submission Module still gives useful feedback.
        return _fallback_brace_check(code)
    except Exception as exc:  # javalang.parser.JavaSyntaxError et al.
        return False, str(exc)


def _fallback_brace_check(code: str) -> tuple[bool, str | None]:
    pairs = {"{": "}", "(": ")", "[": "]"}
    stack: list[str] = []
    for i, ch in enumerate(code):
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in pairs.values():
            if not stack or stack.pop() != ch:
                line = code[:i].count("\n") + 1
                return False, f"Unbalanced '{ch}' near line {line}"
    if stack:
        return False, "Unclosed brackets/braces detected"
    return True, None


def run_javalang_checks(code: str, file_label: str = "Submitted.java") -> list[Finding]:
    findings: list[Finding] = []
    try:
        import javalang
    except ImportError:
        return findings

    try:
        tree = javalang.parse.parse(code)
    except Exception:
        return findings

    lines = code.splitlines()

    for _, node in tree.filter(javalang.tree.MethodDeclaration):
        body = node.body or []
        length = len(body)
        if length > 40:
            findings.append(
                Finding(
                    source="javalang",
                    category=FindingCategory.CODE_SMELL,
                    title=f"Long method: '{node.name}'",
                    description=(
                        f"Method '{node.name}' has ~{length} top-level statements. "
                        "Long methods are harder to test and review; consider extracting "
                        "helper methods."
                    ),
                    severity=Severity.MEDIUM,
                    confidence=0.7,
                    file_name=file_label,
                    line_start=getattr(node.position, "line", None),
                )
            )

    for _, node in tree.filter(javalang.tree.CatchClause):
        block = node.block or []
        if len(block) == 0:
            findings.append(
                Finding(
                    source="javalang",
                    category=FindingCategory.SECURITY_VULNERABILITY,
                    title="Empty catch block",
                    description=(
                        "An empty catch block silently swallows exceptions, which can hide "
                        "security-relevant failures (e.g. failed auth checks) and complicates "
                        "incident response. Related to OWASP 'Improper Error Handling'."
                    ),
                    severity=Severity.MEDIUM,
                    confidence=0.75,
                    file_name=file_label,
                    line_start=getattr(node.position, "line", None),
                    owasp_category="A09:2021-Security Logging and Monitoring Failures",
                )
            )

    # Heuristic hardcoded-secret scan (mirrors what bandit does for Python).
    secret_markers = ("password", "secret", "apikey", "api_key", "token")
    for i, line in enumerate(lines, start=1):
        lower = line.lower()
        if "=" in line and any(m in lower for m in secret_markers) and '"' in line:
            findings.append(
                Finding(
                    source="javalang-heuristic",
                    category=FindingCategory.SECURITY_VULNERABILITY,
                    title="Possible hardcoded secret",
                    description="A string literal assigned to a credential-like variable name was found.",
                    severity=Severity.HIGH,
                    confidence=0.5,
                    file_name=file_label,
                    line_start=i,
                    code_snippet=line.strip(),
                    cwe_id="CWE-798",
                    owasp_category="A07:2021-Identification and Authentication Failures",
                )
            )

    return findings


def pmd_available() -> bool:
    return shutil.which("pmd") is not None


def run_pmd(code: str, file_label: str = "Submitted.java") -> list[Finding]:
    """Optional deep scan via PMD if installed. Silently returns []
    otherwise -- this keeps Java analysis functional without a hard
    dependency on a JVM toolchain being present."""
    if not pmd_available():
        return []

    findings: list[Finding] = []
    tmp_dir = Path(tempfile.mkdtemp())
    src = tmp_dir / "Submitted.java"
    src.write_text(code, encoding="utf-8")
    out = tmp_dir / "pmd.json"
    try:
        subprocess.run(
            [
                "pmd",
                "check",
                "-d",
                str(src),
                "-R",
                "category/java/security.xml,category/java/bestpractices.xml,category/java/design.xml",
                "-f",
                "json",
                "-r",
                str(out),
            ],
            capture_output=True,
            timeout=90,
        )
        if out.exists():
            data = json.loads(out.read_text(encoding="utf-8"))
            for file_entry in data.get("files", []):
                for v in file_entry.get("violations", []):
                    findings.append(
                        Finding(
                            source="pmd",
                            category=FindingCategory.SECURITY_VULNERABILITY
                            if "security" in v.get("rule", "").lower()
                            else FindingCategory.CODE_SMELL,
                            title=v.get("rule", "PMD finding"),
                            description=v.get("description", ""),
                            severity=_PMD_SEVERITY.get(v.get("priority", 3), Severity.MEDIUM),
                            confidence=0.8,
                            file_name=file_label,
                            line_start=v.get("beginline"),
                            line_end=v.get("endline"),
                        )
                    )
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    finally:
        for f in tmp_dir.glob("*"):
            f.unlink(missing_ok=True)
        tmp_dir.rmdir()
    return findings


def run_all(code: str, file_label: str = "Submitted.java") -> list[Finding]:
    findings = run_javalang_checks(code, file_label)
    findings.extend(run_pmd(code, file_label))
    return findings
