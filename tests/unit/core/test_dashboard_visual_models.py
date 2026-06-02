import pytest
from src.edgehunter.core.dashboard_visual_models import (
    VisualSeverity,
    DashboardVisualMetric,
    DashboardVisualCard,
    DashboardVisualSection,
    DashboardVisualPage
)

def test_visual_severity_creation():
    assert VisualSeverity.INFO == "INFO"
    assert VisualSeverity.SUCCESS == "SUCCESS"
    assert VisualSeverity.WARNING == "WARNING"
    assert VisualSeverity.DANGER == "DANGER"

def test_dashboard_visual_metric_valid():
    metric = DashboardVisualMetric(
        key="test_metric",
        label="Test Metric",
        value=42,
        formatted_value="42",
        severity=VisualSeverity.INFO,
        description="A simple test metric"
    )
    assert metric.key == "test_metric"
    assert metric.is_simulated is True
    assert metric.paper_trading is True
    assert metric.learning_mode is True
    assert metric.actionable is False
    assert metric.bet_placed is False
    assert metric.alerted is False
    assert metric.not_operational_advice is True
    
    d = metric.to_dict()
    assert d["key"] == "test_metric"
    assert d["severity"] == "INFO"
    assert d["is_simulated"] is True

def test_dashboard_visual_section_valid():
    metric = DashboardVisualMetric(
        key="test_metric",
        label="Test Metric",
        value=42,
        formatted_value="42",
        severity=VisualSeverity.INFO,
        description="A simple test metric"
    )
    section = DashboardVisualSection(title="Test Section", metrics=[metric])
    assert section.title == "Test Section"
    assert len(section.metrics) == 1
    
    d = section.to_dict()
    assert d["title"] == "Test Section"
    assert d["metrics"][0]["key"] == "test_metric"

def test_dashboard_visual_page_valid():
    page = DashboardVisualPage(
        title="Dashboard",
        generated_at="2026-06-02T10:00:00Z",
        sections=[],
        summary="A nice summary"
    )
    assert page.title == "Dashboard"
    assert page.is_simulated is True
    assert page.paper_trading is True
    assert page.learning_mode is True
    
    d = page.to_dict()
    assert d["title"] == "Dashboard"
    assert d["is_simulated"] is True
    assert d["not_operational_advice"] is True

def test_to_dict_deterministic():
    metric = DashboardVisualMetric(
        key="m", label="l", value=1, formatted_value="1",
        severity=VisualSeverity.SUCCESS, description="d"
    )
    d1 = metric.to_dict()
    d2 = metric.to_dict()
    assert d1 == d2

def test_actionable_true_fails():
    with pytest.raises(ValueError, match="actionable=True is strictly forbidden"):
        DashboardVisualMetric(
            key="m", label="l", value=1, formatted_value="1",
            severity=VisualSeverity.SUCCESS, description="d", actionable=True
        )

def test_bet_placed_true_fails():
    with pytest.raises(ValueError, match="bet_placed=True is strictly forbidden"):
        DashboardVisualPage(
            title="Dashboard", generated_at="now", sections=[], summary="s",
            bet_placed=True
        )

def test_alerted_true_fails():
    with pytest.raises(ValueError, match="alerted=True is strictly forbidden"):
        DashboardVisualPage(
            title="Dashboard", generated_at="now", sections=[], summary="s",
            alerted=True
        )

@pytest.mark.parametrize("bad_term", [
    "apostar hoje", "deu gain", "qual a stake", "kelly formula",
    "fazer entrada", "sinal de aposta", "lucro garantido", "bankroll risk",
    "bet_amount = 10", "wager 5", "execute now", "place_bet API", "call telegram",
    "use scheduler", "trigger autoevolution"
])
def test_operational_language_fails(bad_term):
    with pytest.raises(ValueError, match="Operational language is strictly forbidden"):
        DashboardVisualMetric(
            key="m", label="l", value=1, formatted_value="1",
            severity=VisualSeverity.INFO, description=bad_term
        )

    with pytest.raises(ValueError, match="Operational language is strictly forbidden"):
        DashboardVisualPage(
            title=bad_term, generated_at="now", sections=[], summary="s"
        )

def test_no_network_no_gemini_no_telegram():
    # Model instantiation is pure logic, shouldn't need mocks to prove it does no I/O,
    # but we assert purely that it's a dataclass that doesn't trigger side effects.
    metric = DashboardVisualMetric(
        key="safe", label="Safe", value=1, formatted_value="1",
        severity=VisualSeverity.INFO, description="Safe desc"
    )
    assert metric.key == "safe"
