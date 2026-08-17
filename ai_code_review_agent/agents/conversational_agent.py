"""
Milestone 3, item 4 / Module 5: "Build Conversational Code Assistant --
RAG-powered interface for follow-up queries on flagged issues, vulnerability
explanations, and secure coding guidance grounded in knowledge base."

Grounds every answer in two places: the secure-coding vector store (OWASP
docs the user indexed) and the current analysis report (findings from this
session), so answers are specific to what was actually found.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from llm.provider import get_chat_model
from models.schemas import AnalysisReport
from rag.knowledge_base import format_context_block, retrieve_context

SYSTEM_PROMPT = """You are a secure-coding assistant embedded in a code \
review tool. Answer the developer's question using:

1. The CURRENT REVIEW FINDINGS below (specific to their submitted code)
2. The KNOWLEDGE BASE EXCERPTS below (indexed OWASP / secure-coding docs)

If the question isn't covered by either, answer from general secure-coding \
best practice and say the knowledge base didn't have a direct match. Be \
concise, technical, and give code examples when useful. Never invent a \
finding that isn't in the list below.

CURRENT REVIEW FINDINGS:
{findings_summary}

KNOWLEDGE BASE EXCERPTS:
{kb_context}"""


def _findings_summary(report: AnalysisReport | None) -> str:
    if not report or not report.findings:
        return "(No code has been analyzed in this session yet.)"
    lines = [f"Code health score: {report.code_health_score}/100"]
    for f in report.sorted_findings():
        lines.append(
            f"- [{f.severity.value}] {f.title} ({f.file_name}:{f.line_start}) "
            f"-- {f.description[:200]}"
        )
    return "\n".join(lines)


def ask(
    question: str,
    report: AnalysisReport | None,
    chat_history: list[tuple[str, str]] | None = None,
) -> str:
    kb_chunks = retrieve_context(question, k=5)

    history_messages = []
    for role, content in chat_history or []:
        history_messages.append(HumanMessage(content=content) if role == "human" else AIMessage(content=content))

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("history"),
            ("human", "{question}"),
        ]
    )
    llm = get_chat_model()
    chain = prompt | llm | StrOutputParser()

    return chain.invoke(
        {
            "findings_summary": _findings_summary(report),
            "kb_context": format_context_block(kb_chunks),
            "question": question,
            "history": history_messages,
        }
    )
