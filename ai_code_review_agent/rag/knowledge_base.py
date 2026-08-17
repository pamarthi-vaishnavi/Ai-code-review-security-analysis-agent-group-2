"""
Read-side of the RAG pipeline: turns the persisted Chroma collection into a
retriever, and exposes a small helper for grounding LLM prompts in the
indexed OWASP / secure-coding guidance.
"""
from __future__ import annotations

from config import settings
from llm.provider import get_embeddings


def get_vectorstore():
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=settings.collection_name,
        embedding_function=get_embeddings(),
        persist_directory=str(settings.vector_store_dir),
    )


def get_retriever(k: int | None = None):
    store = get_vectorstore()
    return store.as_retriever(search_kwargs={"k": k or settings.rag_top_k})


def retrieve_context(query: str, k: int | None = None) -> list[dict]:
    """Return grounding chunks as plain dicts (text + source) for prompts."""
    try:
        retriever = get_retriever(k)
        docs = retriever.invoke(query)
    except Exception:
        # Knowledge base not built yet, or embeddings unavailable offline.
        return []

    return [
        {
            "text": doc.page_content,
            "source": doc.metadata.get("source_file", "unknown"),
            "page": doc.metadata.get("page"),
        }
        for doc in docs
    ]


def format_context_block(chunks: list[dict]) -> str:
    if not chunks:
        return "(No secure-coding knowledge base indexed yet.)"
    parts = []
    for i, c in enumerate(chunks, start=1):
        page = f", p.{c['page']}" if c.get("page") is not None else ""
        parts.append(f"[{i}] Source: {c['source']}{page}\n{c['text']}")
    return "\n\n".join(parts)
