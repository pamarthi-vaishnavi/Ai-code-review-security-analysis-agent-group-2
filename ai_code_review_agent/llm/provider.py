"""
Provider-agnostic factories for chat models and embedding models.

Nothing here hardcodes a specific vendor. `init_chat_model` (langchain>=0.2)
accepts a "provider:model" string, so switching LLM_PROVIDER/MODEL_NAME in
.env is enough to move between OpenAI, Anthropic, Google Gemini, Groq,
Ollama, etc. Embeddings default to a local HuggingFace sentence-transformer
so the RAG pipeline works even with zero API keys configured.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from config import settings


class LLMConfigurationError(RuntimeError):
    """Raised when the selected provider is missing required credentials."""


def _require_key(value: str | None, env_var: str, provider: str) -> str:
    if not value:
        raise LLMConfigurationError(
            f"LLM_PROVIDER is '{provider}' but {env_var} is not set. "
            f"Add it to your .env file (see .env.example)."
        )
    return value


@lru_cache(maxsize=4)
def get_chat_model(temperature: float | None = None) -> BaseChatModel:
    """Return a chat model for whichever provider is configured in .env."""
    from langchain.chat_models import init_chat_model

    provider = settings.llm_provider.lower()
    temp = settings.llm_temperature if temperature is None else temperature

    if provider == "openai":
        _require_key(settings.openai_api_key, "OPENAI_API_KEY", provider)
    elif provider == "anthropic":
        _require_key(settings.anthropic_api_key, "ANTHROPIC_API_KEY", provider)
    elif provider in ("google_genai", "google-genai", "google"):
        _require_key(settings.google_api_key, "GOOGLE_API_KEY", provider)
    # ollama / other local providers need no API key

    return init_chat_model(
        settings.llm_model_id(),
        temperature=temp,
    )


@lru_cache(maxsize=2)
def get_embeddings() -> Embeddings:
    """Return an embeddings model for the RAG knowledge base."""
    if settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        _require_key(settings.openai_api_key, "OPENAI_API_KEY", "openai")
        return OpenAIEmbeddings(model=settings.embedding_model)

    # Default: fully local, no API key required.
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=settings.embedding_model)


def llm_status() -> dict[str, str]:
    """Human-readable status used by the sidebar so users know what's active."""
    provider = settings.llm_provider
    configured = True
    reason = "ready"
    try:
        if provider == "openai" and not settings.openai_api_key:
            configured, reason = False, "OPENAI_API_KEY missing"
        elif provider == "anthropic" and not settings.anthropic_api_key:
            configured, reason = False, "ANTHROPIC_API_KEY missing"
        elif provider in ("google_genai", "google") and not settings.google_api_key:
            configured, reason = False, "GOOGLE_API_KEY missing"
    except Exception as exc:  # pragma: no cover - defensive
        configured, reason = False, str(exc)

    return {
        "provider": provider,
        "model": settings.model_name,
        "embedding_provider": settings.embedding_provider,
        "status": "ready" if configured else "not configured",
        "detail": reason,
    }
