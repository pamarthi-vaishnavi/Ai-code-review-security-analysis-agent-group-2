"""
Milestone 2, item 2: "Build Security Vulnerability Agent -- scans submitted
code for OWASP-standard vulnerabilities, classifies by type and severity,
and provides location-specific flagging."

The LLM pass is grounded (RAG) in whatever OWASP/secure-coding documents
the user has indexed via the Knowledge Base tab -- retrieved passages are
injected into the prompt so findings cite real guidance instead of the
model's unaided memory.
"""
from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from analysis import static_java, static_python
from llm.provider import get_chat_model
from models.schemas import Finding, FindingsList
from rag.knowledge_base import format_context_block, retrieve_context

SYSTEM_PROMPT = """You are an application security engineer scanning {language} \
code for OWASP-standard vulnerabilities: Injection (SQLi, command injection), \
Broken Access Control, Cryptographic Failures, Insecure Design, Security \
Misconfiguration, Vulnerable Components, Identification/Authentication \
Failures, Software/Data Integrity Failures, Logging/Monitoring Failures, and \
Server-Side Request Forgery, as well as XSS and CSRF in web-facing code.

Ground every finding in the secure-coding knowledge base excerpts below when \
they are relevant -- reference the matching OWASP category. If the knowledge \
base has no relevant excerpts, rely on well-established OWASP guidance and \
say so.

KNOWLEDGE BASE EXCERPTS:
{context}

A deterministic security scanner already flagged the following -- do not \
duplicate them verbatim, but you MAY note if they are more/less severe in \
context, and you should look for what a pattern-based scanner would miss \
(e.g. broken access control logic, business-logic flaws, SSRF, insecure \
deserialization use):
{static_summary}

Only report vulnerabilities that are actually present in the code below. \
For each finding, set `owasp_category` (e.g. "A03:2021-Injection") and \
`cwe_id` when applicable, and give the exact line range if determinable."""

USER_PROMPT = "```{language}\n{code}\n```"


def _static_summary(findings: list[Finding]) -> str:
    if not findings:
        return "(none)"
    return "\n".join(f"- {f.title} (line {f.line_start}): {f.description[:120]}" for f in findings[:25])


def run_static_security_scan(code: str, language: str, file_label: str) -> list[Finding]:
    if language == "python":
        return static_python.run_bandit(code, file_label)
    if language == "java":
        # javalang heuristic findings already skew security; PMD (if present)
        # adds the rest via run_all in the orchestrator's static pass, but we
        # keep the LLM's static_summary focused on security-flavoured hits.
        return [
            f
            for f in static_java.run_javalang_checks(code, file_label)
            if f.category.value == "SECURITY_VULNERABILITY"
        ]
    return []


def run_llm_scan(
    code: str, language: str, static_findings: list[Finding]
) -> list[Finding]:
    query = f"OWASP secure coding guidance relevant to this {language} code and common vulnerability classes"
    context_chunks = retrieve_context(query, k=6)

    llm = get_chat_model().with_structured_output(FindingsList)
    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("user", USER_PROMPT)]
    )
    chain = prompt | llm
    result: FindingsList = chain.invoke(
        {
            "language": language,
            "code": code,
            "context": format_context_block(context_chunks),
            "static_summary": _static_summary(static_findings),
        }
    )
    for f in result.findings:
        f.source = "security-agent (llm+rag)"
    return result.findings


def analyze(code: str, language: str, file_label: str) -> list[Finding]:
    static_findings = run_static_security_scan(code, language, file_label)
    try:
        llm_findings = run_llm_scan(code, language, static_findings)
    except Exception as exc:
        llm_findings = []
        static_findings.append(_agent_error_finding(str(exc), file_label))
    return static_findings + llm_findings


def _agent_error_finding(message: str, file_label: str) -> Finding:
    from models.schemas import FindingCategory, Severity

    return Finding(
        source="security-agent",
        category=FindingCategory.BEST_PRACTICE,
        title="LLM security scan unavailable",
        description=(
            f"The Security Vulnerability Agent's LLM+RAG pass could not run ({message}). "
            "Showing static-scanner (bandit/javalang) results only."
        ),
        severity=Severity.INFO,
        confidence=1.0,
        file_name=file_label,
    )
