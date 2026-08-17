# AI Code Review & Security Analysis Agent

A multi-agent platform that reviews pasted or uploaded Python/Java code for
quality issues and OWASP-standard security vulnerabilities, generates
remediation with corrected code, produces a PR-style review summary, and
answers follow-up questions through a RAG-grounded conversational assistant.

100% Python. No hardcoded rules or vendor lock-in: static analysis uses
real libraries (pylint, bandit, radon, javalang), the LLM layer is
provider-agnostic (OpenAI / Anthropic / Google / Ollama via one config
value), and the knowledge base is whatever OWASP/secure-coding documents
you index.

---

## 1. Architecture

```
                          Streamlit UI (app.py)
                                  |
                     Code Submission Module
                (paste or upload .py / .java, syntax-validated)
                                  |
                     LangGraph Orchestrator (agents/orchestrator.py)
                                  |
              +-------------------+-------------------+
              |                                        |
      Code Analysis Agent                    Security Vulnerability Agent
   (pylint + radon + LLM review)         (bandit/javalang + RAG-grounded LLM)
              |                                        |
              +-------------------+-------------------+
                                  |
                          Remediation Agent
                (LLM fix + corrected code per finding, RAG-grounded)
                                  |
                          PR Summary Agent
              (executive overview, severity breakdown, fix list)
                                  |
                    Findings Display + Report Export
                     (Markdown / JSON / PDF, Streamlit)
                                  |
                    Conversational Code Assistant
               (RAG over OWASP docs + this session's findings)
```

The Secure Coding Knowledge Base (`rag/`) is a separate pipeline: PDFs/MD/TXT
you drop in `data/owasp_docs/` are chunked, embedded, and stored in a
persisted Chroma collection (`vector_store/`). The Security Agent, the
Remediation Agent, and the Conversational Assistant all retrieve from it.

## 2. Milestone -> code mapping

| Milestone | Deliverable | Where |
|---|---|---|
| M1.1-2 | Architecture, agent responsibilities, data models | this README, `models/schemas.py` |
| M1.3 | Code Submission Module, paste/upload, syntax validation | `utils/code_validation.py`, `app.py` (Submit tab) |
| M1.4 | Secure Coding Knowledge Base + RAG indexing | `rag/ingest.py`, `rag/knowledge_base.py` |
| M2.1 | Code Analysis Agent (smells, complexity, design) | `agents/code_analysis_agent.py`, `analysis/static_python.py`, `analysis/static_java.py` |
| M2.2 | Security Vulnerability Agent (OWASP scan) | `agents/security_agent.py` |
| M2.3 | Parallel multi-agent orchestration | `agents/orchestrator.py` (LangGraph) |
| M2.4 | Validation against sample vulnerable code | `data/sample_code/`, `tests/` |
| M3.1 | Remediation Agent | `agents/remediation_agent.py` |
| M3.2 | PR Summary Agent | `agents/pr_summary_agent.py` |
| M3.3 | Findings Display + code health score | `analysis/severity.py`, `app.py` (Findings tab) |
| M3.4 | Conversational Code Assistant | `agents/conversational_agent.py`, `app.py` (Ask tab) |
| Module 6 | Report export (MD/JSON/PDF) | `reports/exporter.py` |

## 3. Windows setup

Requirements: **Python 3.11 or 3.12** (from [python.org](https://python.org),
check "Add python.exe to PATH" during install), internet access for the
first `pip install`.

```bat
:: 1) In the project folder, double-click or run:
setup_windows.bat

:: 2) Edit .env (created from .env.example) and set:
::    LLM_PROVIDER=openai
::    MODEL_NAME=gpt-4o-mini
::    OPENAI_API_KEY=sk-...
:: (or swap to anthropic / google_genai / ollama -- see .env.example)

:: 3) Launch the app:
run_windows.bat
```

The app opens at `http://localhost:8501`.

### Manual setup (if you prefer not to use the .bat files)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
:: edit .env
streamlit run app.py
```

### Running fully offline / without an API key

- Embeddings default to a local HuggingFace model (`EMBEDDING_PROVIDER=huggingface`),
  so the Knowledge Base tab and vector search work with zero API keys.
- The LLM-powered agents (Code Analysis's design review, Security Agent's
  semantic scan, Remediation, PR Summary, Assistant) require a configured
  LLM provider. Without one, the pipeline still runs and shows **static
  analysis results only** (pylint/bandit/radon/javalang) -- each agent
  degrades gracefully and reports why the LLM pass was skipped instead of
  crashing the pipeline.
- To run 100% locally including the LLM, set `LLM_PROVIDER=ollama` and
  `MODEL_NAME` to a model you've pulled with [Ollama](https://ollama.com)
  (e.g. `ollama pull llama3.1` then `MODEL_NAME=llama3.1`).

## 4. Using the app

1. **Knowledge Base tab** -- upload OWASP Top 10 / ASVS / Cheat Sheet PDFs
   (download them yourself from owasp.org; not redistributed here for
   copyright reasons) and click **Rebuild index**. This is optional but
   makes the Security Agent's findings grounded and cite real guidance.
2. **Submit Code tab** -- paste code or upload a `.py`/`.java` file, click
   **Submit for validation** to syntax-check it, then **Run Code Analysis +
   Security Scan** to trigger the full pipeline.
3. **Findings & Report tab** -- see the code health score, severity
   breakdown, per-finding detail with remediation, and export as
   Markdown/JSON/PDF.
4. **Ask the Assistant tab** -- ask follow-up questions; answers are
   grounded in this session's findings and the indexed knowledge base.

Two intentionally-vulnerable sample files are included at
`data/sample_code/vulnerable_sample.py` and `VulnerableSample.java` --
paste their contents in to see the pipeline in action end-to-end
(SQL injection, hardcoded secrets, command injection, insecure
deserialization, broken access control, empty catch blocks, high
complexity, mutable default arguments, etc. are all planted there).

## 5. Testing

```bat
.venv\Scripts\activate
pytest
```

Tests cover syntax validation, severity scoring, deduplication, and the
static-analysis wrappers (pylint/bandit/radon/javalang) -- these run
without any LLM/API key. The LLM-dependent agents are exercised through
the app itself since they require a live model.

## 6. Extending

- **Add an LLM provider:** anything supported by LangChain's
  `init_chat_model` works -- set `LLM_PROVIDER`/`MODEL_NAME` in `.env`.
  No code changes needed.
- **Add a deeper Java scanner:** install [PMD](https://pmd.github.io/) and
  put `pmd` on PATH -- `analysis/static_java.py` auto-detects and uses it.
- **Add more knowledge base documents:** drop PDFs/MD/TXT into
  `data/owasp_docs/` and click **Rebuild index** in the Knowledge Base tab.
- **Tune the code health score formula:** it's a transparent weighted
  deduction in `analysis/severity.py` (`compute_code_health_score`) --
  documented and easy to adjust rather than a black box.

## 7. Project layout

```
ai_code_review_agent/
├── app.py                     Streamlit UI (all 4 tabs)
├── config.py                  Settings (env-driven)
├── requirements.txt
├── .env.example
├── setup_windows.bat
├── run_windows.bat
├── agents/
│   ├── orchestrator.py        LangGraph multi-agent pipeline
│   ├── code_analysis_agent.py
│   ├── security_agent.py
│   ├── remediation_agent.py
│   ├── pr_summary_agent.py
│   └── conversational_agent.py
├── analysis/
│   ├── static_python.py       pylint / bandit / radon integration
│   ├── static_java.py         javalang / optional PMD integration
│   └── severity.py            scoring + dedup
├── rag/
│   ├── ingest.py               PDF/MD/TXT -> Chroma index
│   └── knowledge_base.py       retriever + context formatting
├── llm/provider.py             provider-agnostic LLM + embeddings factory
├── models/schemas.py           shared Pydantic models
├── reports/exporter.py         Markdown / JSON / PDF export
├── utils/code_validation.py    Code Submission Module validation
├── data/
│   ├── owasp_docs/             put your OWASP PDFs here
│   └── sample_code/            planted-vulnerability demo files
├── vector_store/               persisted Chroma DB (generated)
└── tests/                      pytest suite
```
