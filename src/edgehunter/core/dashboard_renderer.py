import html
import datetime
from src.edgehunter.core.dashboard_visual_models import (
    DashboardVisualPage, DashboardVisualSection, DashboardVisualMetric, DashboardVisualCard, VisualSeverity
)

def _safe(text: str | None) -> str:
    if text is None:
        return ""
    return html.escape(str(text))

def render_dashboard_visual_page(
    summary: dict,
    calibration_summary: dict | None = None,
    evolution_report: dict | None = None,
    schema_status: dict | None = None
) -> DashboardVisualPage:
    sections = []
    
    # Summary Section
    metrics = []
    if "total_matches" in summary:
        metrics.append(DashboardVisualMetric(
            key="total_matches", label="Total Matches", value=summary["total_matches"],
            formatted_value=str(summary["total_matches"]), severity=VisualSeverity.INFO,
            description="Total matches processed in simulated mode"
        ))
    
    # Green/Red Metrics
    if "simulated_outcomes" in summary:
        so = summary["simulated_outcomes"]
        metrics.append(DashboardVisualMetric(
            key="green_sim", label="GREEN_SIM", value=so.get("GREEN_SIM", 0),
            formatted_value=str(so.get("GREEN_SIM", 0)), severity=VisualSeverity.SUCCESS,
            description="Simulated green outcomes"
        ))
        metrics.append(DashboardVisualMetric(
            key="red_sim", label="RED_SIM", value=so.get("RED_SIM", 0),
            formatted_value=str(so.get("RED_SIM", 0)), severity=VisualSeverity.DANGER,
            description="Simulated red outcomes"
        ))
        
    sections.append(DashboardVisualSection(title="Summary Metrics", metrics=metrics))
    
    cards = []
    # Outcomes
    if "simulated_outcomes" in summary:
        cards.append(DashboardVisualCard(
            title="Outcomes",
            content=str(summary["simulated_outcomes"]),
            severity=VisualSeverity.INFO
        ))
        
    # Calibration
    if calibration_summary:
        cards.append(DashboardVisualCard(
            title="Calibration",
            content=str(calibration_summary),
            severity=VisualSeverity.INFO
        ))
        
    # Threshold Suggestion
    if "threshold_suggestion" in summary:
        cards.append(DashboardVisualCard(
            title="Threshold Suggestion",
            content=str(summary["threshold_suggestion"]),
            severity=VisualSeverity.INFO
        ))
        
    # Schema Health
    if schema_status:
        cards.append(DashboardVisualCard(
            title="Schema Health",
            content=str(schema_status),
            severity=VisualSeverity.INFO
        ))
        
    # Evolution Report
    if evolution_report:
        cards.append(DashboardVisualCard(
            title="Evolution Report",
            content=str(evolution_report),
            severity=VisualSeverity.INFO
        ))
        
    if cards:
        sections.append(DashboardVisualSection(title="Detailed Reports", cards=cards))

    return DashboardVisualPage(
        title="Simulated Dashboard",
        generated_at=datetime.datetime.now().isoformat(),
        sections=sections,
        summary="Simulated analytics summary overview."
    )

def render_dashboard_html(page: DashboardVisualPage) -> str:
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        f"<title>{_safe(page.title)}</title>",
        "<style>",
        "body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }",
        ".banner { background-color: #2c3e50; color: #ecf0f1; padding: 10px; margin-bottom: 20px; text-align: center; font-weight: bold; }",
        ".section { background-color: #fff; border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; }",
        ".metric { display: inline-block; padding: 10px; margin: 5px; border: 1px solid #ccc; border-radius: 4px; background-color: #fafafa; }",
        ".metric.SUCCESS { border-color: #2ecc71; color: #27ae60; }",
        ".metric.DANGER { border-color: #e74c3c; color: #c0392b; }",
        ".card { padding: 10px; margin-bottom: 10px; border: 1px solid #eee; background-color: #fcfcfc; }",
        "</style>",
        "</head>",
        "<body>",
        "<div class='banner'>",
        "Simulated analytics dashboard | Read-only | No automatic threshold changes",
        "</div>",
        f"<h1>{_safe(page.title)}</h1>",
        f"<p><strong>Generated at:</strong> {_safe(page.generated_at)}</p>",
        f"<p>{_safe(page.summary)}</p>",
        f"<p><em>Simulated: {page.is_simulated} | Paper Trading: {page.paper_trading} | Learning Mode: {page.learning_mode}</em></p>"
    ]
    
    for section in page.sections:
        html_parts.append("<div class='section'>")
        html_parts.append(f"<h2>{_safe(section.title)}</h2>")
        
        if section.metrics:
            for metric in section.metrics:
                m_class = _safe(metric.severity.value)
                html_parts.append(f"<div class='metric {m_class}'>")
                html_parts.append(f"<strong>{_safe(metric.label)}:</strong> {_safe(metric.formatted_value)}")
                html_parts.append(f"<br><small>{_safe(metric.description)}</small>")
                html_parts.append("</div>")
                
        if section.cards:
            for card in section.cards:
                html_parts.append("<div class='card'>")
                html_parts.append(f"<h3>{_safe(card.title)}</h3>")
                html_parts.append(f"<pre>{_safe(card.content)}</pre>")
                html_parts.append("</div>")
                
        html_parts.append("</div>")
        
    html_parts.append("</body>")
    html_parts.append("</html>")
    
    return "\n".join(html_parts)
