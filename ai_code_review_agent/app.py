"""
AI Code Review & Security Analysis Agent -- Streamlit developer portal.

Modules implemented here:
1. Code Submission Module      -- paste or upload Python/Java, syntax-validated
4. Findings Display Module      -- severity-scored findings, code health score
5. Conversational Assistant UI  -- RAG-grounded chat about the findings
6. Report export UI             -- Markdown / JSON / PDF download

Run with:  streamlit run app.py
"""
from __future__ import annotations
import plotly.graph_objects as go
import plotly.express as px

import streamlit as st
from agents import conversational_agent
from agents.orchestrator import run_pipeline
from config import settings
from llm.provider import llm_status
from models.schemas import AnalysisReport, Severity
from rag import ingest
from reports import exporter
from utils.code_validation import detect_language_from_filename, validate_submission
st.set_page_config(
    page_title="Smart Code Inspection Platform",
    page_icon="🛡️",
    layout="wide",
)
SEVERITY_COLOR = {
    Severity.CRITICAL: "#7f1d1d",
    Severity.HIGH: "#b91c1c",
    Severity.MEDIUM: "#d97706",
    Severity.LOW: "#2563eb",
    Severity.INFO: "#6b7280",
}
def _init_state() -> None:
    st.session_state.setdefault("report", None)
    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("last_code", "")
    st.session_state.setdefault("last_language", "python")
    st.session_state.setdefault("validation", None)
_init_state()
# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:0.6rem;">
        <span style="font-size:1.8rem;">🛡️</span>
        <div>
            <div style="font-size:1.5rem;font-weight:700;">Development of Smart Code Inspection Platform with Vulnerability Detection System</div>
            <div style="opacity:0.7;">Multi-agent diagnostic scan for Python &amp; Java</div>
        </div>
   </div>
    """,
    unsafe_allow_html=True,
)
status = llm_status()
kb_stats = ingest.index_stats()
status_line = (
    f"LLM: **{status['provider']}/{status['model']}** ({status['status']}) &nbsp;|&nbsp; "
    f"Embeddings: **{status['embedding_provider']}** &nbsp;|&nbsp; "
    f"KB index: **{kb_stats['documents']} docs, {kb_stats['chunks']} chunks**"
)
st.caption(status_line)
st.divider()
tab_submit, tab_findings, tab_chat = st.tabs(
    ["📝 Submit Code", "📊 Findings & Report", "💬 Ask the Assistant"]
)
# --------------------------------------------------------------------------
# Tab 1: Code Submission Module
# --------------------------------------------------------------------------
with tab_submit:
    left, right = st.columns([3, 2])

    with left:
        mode = st.radio("Source", ["Paste", "Upload"], horizontal=True, label_visibility="collapsed")

        code = ""
        language = st.session_state["last_language"]
        source_name = "pasted_code"

        if mode == "Paste":
            #language = st.selectbox("Language", settings.supported_languages, index=0)
            code = st.text_area(
                "Source input",
                height=420,
                placeholder=f"Paste your {language} code here...",
                key="paste_area",
            )
            if code and code.strip():
                if "public class" in code or "import java" in code:
                    language = "java"
                    st.success("✅ Detected: **JAVA**")
                else:
                     language = "python"
                     st.success("✅ Detected: **PYTHON**")
            else:
                 language = "python"
            source_name = f"pasted_code.{'py' if language == 'python' else 'java'}"
        else:
            uploaded = st.file_uploader("Upload a .py or .java file", type=["py", "java"])
            if uploaded is not None:
                code = uploaded.read().decode("utf-8", errors="replace")
                detected = detect_language_from_filename(uploaded.name)
                language = detected or "python"
                source_name = uploaded.name

                if language == "java":
                     st.success("✅ Detected: **JAVA**")
                else:
                     st.success("✅ Detected: **PYTHON**")
        
                st.code(code[:2000] + ("..." if len(code) > 2000 else ""), language=language)
        col_a, col_b = st.columns(2)
        validate_clicked = col_a.button("✅ Submit for validation", use_container_width=True)
        run_clicked = col_b.button(
            "🚀 Run Code Analysis + Security Scan", type="primary", use_container_width=True
        )
   # with right:
    #    st.markdown("#### Pipeline")
     #   st.markdown(
      #      """
       #     ```
        #    Submitted code
         #         |
           #       v
            #Syntax validation
             #     |
              #    v
            #+-----------------+-----------------+
            #| Code Analysis   | Security Vuln.  |   (parallel)
            #| Agent           | Agent (RAG)     |
            #+-----------------+-----------------+
              #    |
             #     v
            #Remediation Agent
              #    |
             #     v
            #PR Summary Agent
             #     |
            #      v
           # Findings & Report
          #  ```
         #   """
        #)
        if validate_clicked or run_clicked:
            if not code.strip():
                st.warning("No code submitted yet.")
            else:
                result = validate_submission(code, language)
                st.session_state["validation"] = result
                st.session_state["last_code"] = code
                st.session_state["last_language"] = language

        validation = st.session_state["validation"]
        if validation is not None:
            if validation.is_valid:
                st.success(f"Syntax valid ✓  ({validation.char_count} chars, {language})")
            else:
                st.error(f"Syntax error: {validation.error}")

        if run_clicked and code.strip():
            validation = st.session_state["validation"]
            if validation and validation.is_valid:
                with st.status("Running multi-agent pipeline...", expanded=True) as status_box:
                    st.write("🔎 Code Analysis Agent + Security Vulnerability Agent (parallel)...")
                    try:
                        report: AnalysisReport = run_pipeline(
                            submission_id="",
                            language=language,
                            file_label=source_name,
                            code=code,
                        )
                        st.write("🛠️ Remediation Agent generating fixes...")
                        st.write("📝 PR Summary Agent compiling review...")
                        st.session_state["report"] = report
                        st.session_state["chat_history"] = []
                        status_box.update(label="Pipeline complete ✅", state="complete")
                    except Exception as exc:
                        status_box.update(label="Pipeline failed", state="error")
                        st.exception(exc)
                st.success("Done — see the **Findings & Report** tab.")
            else:
                st.warning("Fix the syntax error before running the pipeline.")

# --------------------------------------------------------------------------
# Tab 2: Findings Display & Report Export
# --------------------------------------------------------------------------
with tab_findings:
    report: AnalysisReport | None = st.session_state["report"]
    if report is None:
        st.info("Submit code and run the pipeline to see findings here.")
    else:
        # ===== VISUALIZATIONS =====
        st.subheader("📊 Analysis Dashboard")
        col1, col2, col3 = st.columns(3)
        
        # Graph 1: Severity Distribution (Pie Chart)
        with col1:
            st.subheader("📊 Severity Distribution")
            severity_data = {
                "Critical": report.severity_breakdown.critical,
                "High": report.severity_breakdown.high,
                "Medium": report.severity_breakdown.medium,
                "Low": report.severity_breakdown.low,
                "Info": report.severity_breakdown.info,
            }
            severity_data = {k: v for k, v in severity_data.items() if v > 0}
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=list(severity_data.keys()),
                values=list(severity_data.values()),
                marker=dict(colors=["#d62728", "#ff7f0e", "#ffbb33", "#90EE90", "#808080"]),
                hole=0
            )])
            fig_pie.update_layout(height=300, showlegend=True, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Graph 2: Code Health Score Gauge
        with col2:
            st.subheader("💚 Code Health Score")
            score = report.code_health_score
            
            if score >= 80:
                gauge_color = "green"
            elif score >= 50:
                gauge_color = "yellow"
            else:
                gauge_color = "red"
            
            fig_gauge = go.Figure(data=[go.Indicator(
                mode="gauge+number+delta",
                value=score,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Score / 100"},
                delta={"reference": 60},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": gauge_color},
                    "steps": [
                        {"range": [0, 30], "color": "#ffcccc"},
                        {"range": [30, 60], "color": "#ffffcc"},
                        {"range": [60, 100], "color": "#ccffcc"}
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 90
                    }
                }
            )])
            fig_gauge.update_layout(height=300, margin=dict(l=0, r=0, t=50, b=0))
            st.plotly_chart(fig_gauge, use_container_width=True)
        
        # Graph 3: Findings by Category (Bar Chart)
        with col3:
            st.subheader("🔍 Findings by Category")
            
            categories = {
                "Security": 0,
                "Code Quality": 0,
                "Logic": 0,
                "Style": 0
            }
            
            for f in report.findings:
                title_lower = f.title.lower()
                if any(keyword in title_lower for keyword in ["injection", "hardcoded", "bypass", "vulnerability", "secret"]):
                    categories["Security"] += 1
                elif any(keyword in title_lower for keyword in ["unused", "duplication", "smell", "complexity"]):
                    categories["Code Quality"] += 1
                elif any(keyword in title_lower for keyword in ["logic", "return", "validation", "parameter"]):
                    categories["Logic"] += 1
                else:
                    categories["Style"] += 1
            
            fig_bar = go.Figure(data=[go.Bar(
                x=list(categories.keys()),
                y=list(categories.values()),
                marker=dict(color=["#d62728", "#1f77b4", "#ff7f0e", "#2ca02c"]),
                text=list(categories.values()),
                textposition="auto",
            )])
            fig_bar.update_layout(
                height=300,
                xaxis_title="Category",
                yaxis_title="Count",
                showlegend=False,
                margin=dict(l=0, r=0, t=0, b=0)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        st.divider()
        
        # Continue with existing metrics below
        score_col, crit_col, high_col, med_col, low_col = st.columns(5)
        score_col.metric("Code Health Score", f"{report.code_health_score}/100")
        crit_col.metric("Critical", report.severity_breakdown.critical)
        high_col.metric("High", report.severity_breakdown.high)
        med_col.metric("Medium", report.severity_breakdown.medium)
        low_col.metric("Low / Info", report.severity_breakdown.low + report.severity_breakdown.info)

        st.progress(report.code_health_score / 100)

        st.markdown("### PR-Style Review Summary")
        st.markdown(report.pr_summary or "_No summary available._")

        st.markdown("### Findings")
        severities_present = {f.severity for f in report.findings}
        filter_choice = st.multiselect(
            "Filter by severity",
            options=[s.value for s in Severity],
            default=[s.value for s in Severity if s in severities_present],
        )

        for f in report.sorted_findings():
            if f.severity.value not in filter_choice:
                continue
            color = SEVERITY_COLOR[f.severity]
            with st.expander(f"🔸 [{f.severity.value}] {f.title}"):
                st.markdown(
                    f"<span style='color:{color};font-weight:700;'>{f.severity.value}</span> "
                    f"&nbsp;|&nbsp; source: `{f.source}` &nbsp;|&nbsp; confidence: {f.confidence:.0%}",
                    unsafe_allow_html=True,
                )
                st.write(f.description)
                if f.owasp_category:
                    st.caption(f"OWASP: {f.owasp_category}")
                if f.cwe_id:
                    st.caption(f"CWE: {f.cwe_id}")
                if f.code_snippet:
                    st.code(f.code_snippet, language=report.language)
                if f.remediation_summary:
                    st.markdown(f"**Remediation:** {f.remediation_summary}")
                if f.remediation_code:
                    st.markdown("Suggested fix:")
                    st.code(f.remediation_code, language=report.language)

        st.markdown("### Export Report")
        exp_col1, exp_col2, exp_col3 = st.columns(3)
        md_bytes = exporter.to_markdown(report).encode("utf-8")
        json_bytes = exporter.to_json(report).encode("utf-8")
        exp_col1.download_button(
            "⬇️ Markdown", md_bytes, file_name=f"review_{report.submission_id}.md", mime="text/markdown"
        )
        exp_col2.download_button(
            "⬇️ JSON", json_bytes, file_name=f"review_{report.submission_id}.json", mime="application/json"
        )
        if exp_col3.button("⬇️ Generate PDF"):
            pdf_bytes = exporter.to_pdf_bytes(report)
            st.download_button(
                "Download PDF",
                pdf_bytes,
                file_name=f"review_{report.submission_id}.pdf",
                mime="application/pdf",
            )

# --------------------------------------------------------------------------
# Tab 3: Conversational Code Assistant
# --------------------------------------------------------------------------
with tab_chat:
    st.markdown("Ask follow-up questions about flagged issues or secure coding guidance.")
    report = st.session_state["report"]

    for role, content in st.session_state["chat_history"]:
        with st.chat_message("user" if role == "human" else "assistant"):
            st.markdown(content)

    question = st.chat_input("e.g. Why is the SQL query on line 5 risky, and how do I fix it?")
    if question:
        st.session_state["chat_history"].append(("human", question))
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer = conversational_agent.ask(
                        question, report, st.session_state["chat_history"][:-1]
                    )
                except Exception as exc:
                    answer = f"⚠️ Assistant unavailable: {exc}"
            st.markdown(answer)
        st.session_state["chat_history"].append(("ai", answer))

# --------------------------------------------------------------------------
# Tab 4: Knowledge Base (OWASP / secure-coding docs -> RAG index)
# --------------------------------------------------------------------------
#with tab_kb:
 #   st.markdown(
  #      "Upload OWASP Top 10 / ASVS / Cheat Sheets / internal secure-coding "
   #     "standards (PDF, Markdown, or text). They're chunked, embedded, and "
    #    "indexed into the vector store that grounds the Security Agent and "
     #   "the assistant."
    #)
    #uploaded_docs = st.file_uploader(
     #  "Add documents", type=["pdf", "md", "txt"], accept_multiple_files=True
    #3)
    #if uploaded_docs:
     #   for doc in uploaded_docs:
      #      dest = settings.owasp_docs_dir / doc.name
       #     dest.write_bytes(doc.getbuffer())
       # st.success(f"Saved {len(uploaded_docs)} file(s) to {settings.owasp_docs_dir}")

    #existing = sorted(p.name for p in settings.owasp_docs_dir.glob("*") if p.is_file())
    #st.markdown(f"**{len(existing)} document(s) on disk:** " + (", ".join(existing) if existing else "none yet"))

    #if st.button("🔄 (Re)build knowledge base index", type="primary"):
     #   with st.spinner("Chunking, embedding, and indexing..."):
      #      try:
       #         result = ingest.build_or_refresh_index()
        #        st.success(
         #           f"Indexed {result.files_processed} file(s) into {result.chunks_indexed} chunks."
           #     )
          #      if result.skipped:
           #         st.caption(f"Skipped (unsupported/failed): {', '.join(result.skipped)}")
            #except Exception as exc:
             #   st.error(f"Indexing failed: {exc}")

   # stats = ingest.index_stats()
    #Sst.metric("Indexed chunks", stats["chunks"])
