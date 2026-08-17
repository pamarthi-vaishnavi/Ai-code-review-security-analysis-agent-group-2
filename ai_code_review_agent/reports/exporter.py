"""
Module 6: "Code Review Report Generation and Export Module" -- turns an
AnalysisReport into Markdown, JSON, and PDF artifacts a developer can
attach to a pull request or ticket.
"""
from __future__ import annotations

from io import BytesIO

from models.schemas import AnalysisReport, Finding


def to_markdown(report: AnalysisReport) -> str:
    lines = [
        f"# Code Review Report -- {report.source_name}",
        "",
        f"- **Submission ID:** `{report.submission_id}`",
        f"- **Language:** {report.language}",
        f"- **Generated:** {report.generated_at.isoformat()}",
        f"- **Code Health Score:** {report.code_health_score}/100",
        "",
        report.pr_summary or "_No PR summary generated._",
        "",
        "## All Findings",
        "",
        "| Severity | Title | Location | Source |",
        "|---|---|---|---|",
    ]
    for f in report.sorted_findings():
        loc = f"{f.file_name or '-'}:{f.line_start or '-'}"
        lines.append(f"| {f.severity.value} | {f.title} | {loc} | {f.source} |")

    lines.append("")
    lines.append("## Findings Detail")
    for f in report.sorted_findings():
        lines.extend(_finding_markdown(f))

    return "\n".join(lines)


def _finding_markdown(f: Finding) -> list[str]:
    loc = f"{f.file_name or '-'}:{f.line_start or '-'}"
    block = [
        f"### [{f.severity.value}] {f.title}",
        f"*{loc}  |  source: {f.source}  |  confidence: {f.confidence:.0%}*",
        "",
        f.description,
        "",
    ]
    if f.owasp_category:
        block.append(f"**OWASP:** {f.owasp_category}")
    if f.cwe_id:
        block.append(f"**CWE:** {f.cwe_id}")
    if f.code_snippet:
        block.extend(["", "```", f.code_snippet, "```"])
    if f.remediation_summary:
        block.extend(["", f"**Remediation:** {f.remediation_summary}"])
    if f.remediation_code:
        block.extend(["", "Suggested fix:", "```", f.remediation_code, "```"])
    block.append("")
    return block


def to_json(report: AnalysisReport) -> str:
    return report.model_dump_json(indent=2)


def to_pdf_bytes(report: AnalysisReport) -> bytes:
    """Render the report as a formatted PDF using reportlab (pure-Python,
    installs cleanly on Windows -- no external binary dependency)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], spaceAfter=6)
    mono = ParagraphStyle("mono", parent=styles["Code"], fontSize=8, leading=10)

    severity_colors = {
        "CRITICAL": colors.HexColor("#7f1d1d"),
        "HIGH": colors.HexColor("#b91c1c"),
        "MEDIUM": colors.HexColor("#d97706"),
        "LOW": colors.HexColor("#2563eb"),
        "INFO": colors.HexColor("#6b7280"),
    }

    story = [
        Paragraph(f"Code Review Report -- {report.source_name}", styles["Title"]),
        Paragraph(
            f"Submission {report.submission_id} | {report.language} | "
            f"Generated {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Normal"],
        ),
        Paragraph(f"Code Health Score: <b>{report.code_health_score}/100</b>", styles["Heading2"]),
        Spacer(1, 8),
    ]

    for paragraph in (report.pr_summary or "No PR summary generated.").split("\n"):
        if paragraph.strip():
            story.append(Paragraph(paragraph.replace("#", "").strip(), body))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Findings", styles["Heading2"]))

    table_data = [["Severity", "Title", "Location", "Source"]]
    for f in report.sorted_findings():
        table_data.append(
            [f.severity.value, f.title[:60], f"{f.file_name or '-'}:{f.line_start or '-'}", f.source]
        )
    table = Table(table_data, colWidths=[0.9 * inch, 3.0 * inch, 1.3 * inch, 1.6 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    for row_idx, f in enumerate(report.sorted_findings(), start=1):
        table.setStyle(
            TableStyle([("TEXTCOLOR", (0, row_idx), (0, row_idx), severity_colors.get(f.severity.value, colors.black))])
        )
    story.append(table)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Findings Detail", styles["Heading2"]))
    for f in report.sorted_findings():
        story.append(Paragraph(f"[{f.severity.value}] {f.title}", styles["Heading3"]))
        story.append(Paragraph(f"{f.file_name or '-'}:{f.line_start or '-'} | source: {f.source}", styles["Italic"]))
        story.append(Paragraph(f.description, body))
        if f.remediation_summary:
            story.append(Paragraph(f"<b>Remediation:</b> {f.remediation_summary}", body))
        if f.remediation_code:
            story.append(Paragraph(f.remediation_code.replace("\n", "<br/>"), mono))
        story.append(Spacer(1, 8))

    doc.build(story)
    return buffer.getvalue()
