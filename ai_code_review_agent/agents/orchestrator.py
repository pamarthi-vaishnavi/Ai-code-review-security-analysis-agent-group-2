"""
Milestone 2, item 3 & Milestone 3 orchestration: "Implement multi-agent
orchestration -- Code Analysis and Security Vulnerability agents run in
parallel, outputs merged into a unified findings list", followed by the
Milestone 3 Remediation and PR Summary stages.

Built on LangGraph so the pipeline is a real, inspectable state graph
(fan-out -> fan-in -> sequential stages) rather than a hand-rolled
sequence of function calls.
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from agents import code_analysis_agent, pr_summary_agent, remediation_agent, security_agent
from analysis.severity import build_report
from models.schemas import AnalysisReport, Finding


class PipelineState(TypedDict):
    submission_id: str
    language: str
    file_label: str
    code: str
    # Both analysis nodes append to the same reducer-backed list, which is
    # how LangGraph merges concurrent branch outputs safely.
    findings: Annotated[list[Finding], operator.add]
    report: AnalysisReport | None


def _code_analysis_node(state: PipelineState) -> dict:
    findings = code_analysis_agent.analyze(state["code"], state["language"], state["file_label"])
    return {"findings": findings}


def _security_node(state: PipelineState) -> dict:
    findings = security_agent.analyze(state["code"], state["language"], state["file_label"])
    return {"findings": findings}


def _remediation_node(state: PipelineState) -> dict:
    remediated = remediation_agent.remediate(state["findings"], state["language"])
    return {"findings": remediated}


def _finalize_node(state: PipelineState) -> dict:
    report = build_report(
        submission_id=state["submission_id"],
        language=state["language"],
        source_name=state["file_label"],
        findings=state["findings"],
    )
    summary = pr_summary_agent.summarize(
        report.findings, state["language"], report.code_health_score, report.severity_breakdown
    )
    report.pr_summary = summary
    return {"report": report}


def build_pipeline():
    graph = StateGraph(PipelineState)

    graph.add_node("code_analysis", _code_analysis_node)
    graph.add_node("security_scan", _security_node)
    graph.add_node("remediation", _remediation_node)
    graph.add_node("finalize", _finalize_node)

    # Fan-out: both analysis agents run in parallel off START.
    graph.add_edge(START, "code_analysis")
    graph.add_edge(START, "security_scan")

    # Fan-in: remediation only starts once BOTH branches complete.
    graph.add_edge("code_analysis", "remediation")
    graph.add_edge("security_scan", "remediation")

    graph.add_edge("remediation", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


def run_pipeline(submission_id: str, language: str, file_label: str, code: str) -> AnalysisReport:
    pipeline = get_pipeline()
    result = pipeline.invoke(
        {
            "submission_id": submission_id,
            "language": language,
            "file_label": file_label,
            "code": code,
            "findings": [],
            "report": None,
        }
    )
    return result["report"]
