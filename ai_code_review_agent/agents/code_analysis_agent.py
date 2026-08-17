"""
Milestone 2, item 1: "Build Code Analysis Agent -- detects code smells,
complexity issues, design anti-patterns, and poor coding practices with
severity scoring per finding."

Design: deterministic static tools (pylint/radon for Python, javalang/PMD
for Java) find the mechanical issues; the LLM is reserved for the things
static tools are bad at -- naming, design-pattern misuse, separation of
concerns, readability, API design -- grounded in the actual submitted code
so nothing is hardcoded or templated.
"""
from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from analysis import static_java, static_python
from llm.provider import get_chat_model
from models.schemas import Finding, FindingsList

SYSTEM_PROMPT = """You are a senior software engineer performing a thorough \
code review focused on code QUALITY -- not security (a separate agent \
handles security). Review the submitted {language} code for:

- Code smells (long functions, duplicated logic, magic numbers, poor naming)
- Design anti-patterns (God objects, tight coupling, violated SRP)
- Poor error handling and missing input validation
- Maintainability and readability issues
- Missing tests/documentation where it materially hurts maintainability

A separate static-analysis pass already flagged the following mechanical \
issues -- do NOT repeat them, focus on issues a linter cannot catch:
{static_summary}

For every issue you find, output a structured finding with an accurate \
severity (CRITICAL/HIGH/MEDIUM/LOW/INFO), the exact line range if you can \
determine it, and a one-sentence description. Only report real issues \
present in the code below -- do not invent findings."""

USER_PROMPT = "```{language}\n{code}\n```"


def _static_summary(findings: list[Finding]) -> str:
    if not findings:
        return "(none)"
    return "\n".join(f"- {f.title} (line {f.line_start})" for f in findings[:25])


def run_static_analysis(code: str, language: str, file_label: str) -> list[Finding]:
    if language == "python":
        # Only the quality-relevant subset here; bandit runs in the security agent.
        return static_python.run_pylint(code, file_label) + static_python.run_radon_complexity(
            code, file_label
        )
    if language == "java":
        return static_java.run_javalang_checks(code, file_label)
    return []


def run_llm_review(code: str, language: str, static_findings: list[Finding]) -> list[Finding]:
    llm = get_chat_model().with_structured_output(FindingsList)
    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("user", USER_PROMPT)]
    )
    chain = prompt | llm
    result: FindingsList = chain.invoke(
        {
            "language": language,
            "code": code,
            "static_summary": _static_summary(static_findings),
        }
    )
    for f in result.findings:
        f.source = "code-analysis-agent (llm)"
    return result.findings


def analyze(code: str, language: str, file_label: str) -> list[Finding]:
    """Full Code Analysis Agent run: static tools + LLM, merged."""
    static_findings = run_static_analysis(code, language, file_label)
    try:
        llm_findings = run_llm_review(code, language, static_findings)
    except Exception as exc:  # LLM not configured / network unavailable
        llm_findings = []
        static_findings.append(
            _agent_error_finding(str(exc), file_label)
        )
    return static_findings + llm_findings


def _agent_error_finding(message: str, file_label: str) -> Finding:
    from models.schemas import FindingCategory, Severity

    return Finding(
        source="code-analysis-agent",
        category=FindingCategory.BEST_PRACTICE,
        title="LLM review unavailable",
        description=(
            "The Code Analysis Agent's LLM pass could not run "
            f"({message}). Showing static-analysis results only. "
            "Configure LLM_PROVIDER/API keys in .env to enable full review."
        ),
        severity=Severity.INFO,
        confidence=1.0,
        file_name=file_label,
    )
