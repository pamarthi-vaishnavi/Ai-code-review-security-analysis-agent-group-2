"""
Central configuration for the AI Code Review & Security Analysis Agent.

Every value that could differ between environments (API keys, model names,
storage paths, thresholds) is read from environment variables / a local
`.env` file via pydantic-settings. Nothing here is hardcoded to a single
vendor -- swap LLM_PROVIDER / MODEL_NAME / EMBEDDING_PROVIDER and the whole
pipeline follows.
"""
from __future__ import annotations
from dotenv import load_dotenv

load_dotenv()
import os
import streamlit as st
from functools import lru_cache

# Cache expensive resources
@st.cache_resource
def load_llm_model():
    from llm.provider import get_chat_model
    return get_chat_model()

@st.cache_resource
def load_vector_db():
    from rag.knowledge_base import knowledge_base
    return knowledge_base

@st.cache_resource
def load_settings():
    return Settings()
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- LLM provider -----------------------------------------------
    # Any provider supported by langchain's init_chat_model:
    # "openai", "anthropic", "google_genai", "ollama", "groq", ...
    llm_provider: str = Field(default="google_genai", alias="LLM_PROVIDER")
    model_name: str = Field(default="gpt-4o-mini", alias="MODEL_NAME")
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")

    # ---- Embeddings / RAG --------------------------------------------
    # "huggingface" runs fully offline/local (sentence-transformers) so the
    # knowledge base works even without an API key. "openai" uses
    # text-embedding-3-small when a key is available.
    embedding_provider: Literal["huggingface", "openai"] = Field(
        default="huggingface", alias="EMBEDDING_PROVIDER"
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )
    rag_chunk_size: int = Field(default=1000, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=150, alias="RAG_CHUNK_OVERLAP")
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")

    # ---- Storage -------------------------------------------------------
    owasp_docs_dir: Path = Field(default=BASE_DIR / "data" / "owasp_docs")
    vector_store_dir: Path = Field(default=BASE_DIR / "vector_store")
    reports_dir: Path = Field(default=BASE_DIR / "data" / "generated_reports")
    collection_name: str = Field(default="secure_coding_kb", alias="COLLECTION_NAME")

    # ---- Analysis behaviour ---------------------------------------------
    max_code_chars: int = Field(default=60_000, alias="MAX_CODE_CHARS")
    supported_languages: tuple[str, ...] = ("python", "java")

    def llm_model_id(self) -> str:
        """Provider-prefixed model id for langchain's init_chat_model()."""
        return f"{self.llm_provider}:{self.model_name}"


settings = Settings()
settings.owasp_docs_dir.mkdir(parents=True, exist_ok=True)
settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
settings.reports_dir.mkdir(parents=True, exist_ok=True)

if settings.openai_api_key:
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
if settings.anthropic_api_key:
    os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
if settings.google_api_key:
    os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key)
    os.environ.setdefault("GEMINI_API_KEY", settings.google_api_key)
