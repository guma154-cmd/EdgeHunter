import pytest
from src.edgehunter.core.dashboard_renderer import render_dashboard_visual_page, render_dashboard_html

def test_render_dashboard_visual_page_from_summary():
    summary = {
        "total_matches": 10,
        "simulated_outcomes": {"GREEN_SIM": 5, "RED_SIM": 3},
        "threshold_suggestion": {"new_threshold": 0.05}
    }
    page = render_dashboard_visual_page(summary=summary)
    assert page.title == "Simulated Dashboard"
    assert len(page.sections) == 2
    
    # Check metrics
    metrics_section = page.sections[0]
    assert len(metrics_section.metrics) == 3
    assert metrics_section.metrics[0].key == "total_matches"
    assert metrics_section.metrics[1].key == "green_sim"
    
def test_render_html_contains_banner_and_flags():
    summary = {"total_matches": 10}
    page = render_dashboard_visual_page(summary=summary)
    html_out = render_dashboard_html(page)
    
    assert "Simulated analytics dashboard" in html_out
    assert "Read-only" in html_out
    assert "No automatic threshold changes" in html_out
    assert "Simulated: True" in html_out
    assert "Learning Mode: True" in html_out

def test_html_escapes_dangerous_text():
    summary = {"total_matches": "<script>alert(1)</script>"}
    page = render_dashboard_visual_page(summary=summary)
    html_out = render_dashboard_html(page)
    
    assert "<script>" not in html_out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_out

def test_html_no_external_cdn_or_scripts():
    summary = {"total_matches": 10}
    page = render_dashboard_visual_page(summary=summary)
    html_out = render_dashboard_html(page)
    
    assert "<script" not in html_out.lower()
    assert "http://" not in html_out.lower()
    assert "https://" not in html_out.lower()
    assert "cdn" not in html_out.lower()

def test_json_visual_is_deterministic():
    summary = {"total_matches": 10}
    page1 = render_dashboard_visual_page(summary=summary)
    page2 = render_dashboard_visual_page(summary=summary)
    
    # Ignoring generated_at which changes
    dict1 = page1.to_dict()
    dict2 = page2.to_dict()
    dict1.pop("generated_at")
    dict2.pop("generated_at")
    
    assert dict1 == dict2

def test_unsafe_payload_fails():
    summary = {"total_matches": "aposta"}
    with pytest.raises(ValueError, match="Operational language is strictly forbidden"):
        render_dashboard_visual_page(summary=summary)

def test_no_network_no_gemini_no_db_no_api_no_execution():
    # As these are pure functions manipulating dicts, string and HTML escaping,
    # no I/O is performed.
    summary = {"total_matches": 1}
    page = render_dashboard_visual_page(summary=summary)
    html = render_dashboard_html(page)
    assert page.is_simulated is True
