"""
Milestone 1 requirement: "Build Secure Coding Knowledge Base -- index OWASP
guidelines, secure coding standards, and best practice documents into RAG
pipeline via chunking, embedding, and vector store indexing."

Drop any number of PDFs / Markdown / text files (OWASP Top 10, ASVS,
Cheat Sheets, internal secure-coding standards, ...) into
`data/owasp_docs/` and call `build_or_refresh_index()`. Nothing about the
document set is hardcoded -- whatever is in that folder gets indexed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from llm.provider import get_embeddings

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


@dataclass
class IngestResult:
    files_processed: int
    chunks_indexed: int
    skipped: list[str]


def _load_document(path: Path) -> list[Document]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader

        return PyPDFLoader(str(path)).load()
    if suffix in (".md", ".txt"):
        from langchain_community.document_loaders import TextLoader

        return TextLoader(str(path), encoding="utf-8").load()
    raise ValueError(f"Unsupported document type: {suffix}")


def load_all_documents(docs_dir: Path | None = None) -> tuple[list[Document], list[str]]:
    docs_dir = docs_dir or settings.owasp_docs_dir
    documents: list[Document] = []
    skipped: list[str] = []

    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            skipped.append(path.name)
            continue
        try:
            loaded = _load_document(path)
            for doc in loaded:
                doc.metadata["source_file"] = path.name
            documents.extend(loaded)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to load %s: %s", path, exc)
            skipped.append(path.name)

    return documents, skipped


def chunk_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)


def build_or_refresh_index(docs_dir: Path | None = None) -> IngestResult:
    """(Re)build the persisted Chroma collection from every document in
    `data/owasp_docs/`. Safe to call repeatedly -- it fully replaces the
    collection so stale/removed documents don't linger."""
    from langchain_chroma import Chroma

    documents, skipped = load_all_documents(docs_dir)
    chunks = chunk_documents(documents) if documents else []

    embeddings = get_embeddings()

    # Reset the collection so re-indexing reflects deletions/edits too.
    store = Chroma(
        collection_name=settings.collection_name,
        embedding_function=embeddings,
        persist_directory=str(settings.vector_store_dir),
    )
    try:
        existing_ids = store.get()["ids"]
        if existing_ids:
            store.delete(ids=existing_ids)
    except Exception:  # pragma: no cover - empty/new collection
        pass

    if chunks:
        store.add_documents(chunks)

    return IngestResult(
        files_processed=len({d.metadata.get("source_file") for d in documents}),
        chunks_indexed=len(chunks),
        skipped=skipped,
    )


def index_stats() -> dict[str, int]:
    from langchain_chroma import Chroma

    embeddings = get_embeddings()
    store = Chroma(
        collection_name=settings.collection_name,
        embedding_function=embeddings,
        persist_directory=str(settings.vector_store_dir),
    )
    try:
        data = store.get()
        ids = data.get("ids", [])
        sources = {m.get("source_file") for m in data.get("metadatas", []) if m}
        return {"chunks": len(ids), "documents": len(sources)}
    except Exception:
        return {"chunks": 0, "documents": 0}
