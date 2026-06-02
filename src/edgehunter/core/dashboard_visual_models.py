from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Forbidden terms to strictly enforce the rules
FORBIDDEN_TERMS = {
    "aposta", "apostar", "entrada", "sinal de aposta", "recomendado",
    "recomendação operacional", "lucro", "gain", "stake", "kelly",
    "bankroll", "bet_amount", "wager", "execute", "execution",
    "place_bet", "telegram", "scheduler", "autoevolution"
}

def _validate_safe_string(text: str) -> None:
    if not isinstance(text, str):
        return
    lower_text = text.lower()
    for term in FORBIDDEN_TERMS:
        if term in lower_text:
            raise ValueError(f"Operational language is strictly forbidden: found '{term}'")

class VisualSeverity(str, Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    DANGER = "DANGER"

@dataclass(frozen=True)
class DashboardVisualMetric:
    key: str
    label: str
    value: Any
    formatted_value: str
    severity: VisualSeverity
    description: str
    is_simulated: bool = field(default=True, init=False)
    paper_trading: bool = field(default=True, init=False)
    learning_mode: bool = field(default=True, init=False)
    actionable: bool = field(default=False)
    bet_placed: bool = field(default=False)
    alerted: bool = field(default=False)
    not_operational_advice: bool = field(default=True, init=False)

    def __post_init__(self):
        if self.actionable:
            raise ValueError("actionable=True is strictly forbidden.")
        if self.bet_placed:
            raise ValueError("bet_placed=True is strictly forbidden.")
        if self.alerted:
            raise ValueError("alerted=True is strictly forbidden.")
        
        # Financial fields checks (just looking at keys/labels is one way, plus the text)
        for val in [self.key, self.label, self.formatted_value, self.description]:
            _validate_safe_string(str(val))

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "value": self.value,
            "formatted_value": self.formatted_value,
            "severity": self.severity.value,
            "description": self.description,
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "learning_mode": self.learning_mode,
            "actionable": self.actionable,
            "bet_placed": self.bet_placed,
            "alerted": self.alerted,
            "not_operational_advice": self.not_operational_advice
        }

@dataclass(frozen=True)
class DashboardVisualCard:
    title: str
    content: str
    severity: VisualSeverity = VisualSeverity.INFO

    def __post_init__(self):
        _validate_safe_string(self.title)
        _validate_safe_string(self.content)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "content": self.content,
            "severity": self.severity.value
        }

@dataclass(frozen=True)
class DashboardVisualSection:
    title: str
    metrics: list[DashboardVisualMetric] = field(default_factory=list)
    cards: list[DashboardVisualCard] = field(default_factory=list)

    def __post_init__(self):
        _validate_safe_string(self.title)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "metrics": [m.to_dict() for m in self.metrics],
            "cards": [c.to_dict() for c in self.cards]
        }

@dataclass(frozen=True)
class DashboardVisualPage:
    title: str
    generated_at: str
    sections: list[DashboardVisualSection]
    summary: str
    is_simulated: bool = field(default=True, init=False)
    paper_trading: bool = field(default=True, init=False)
    learning_mode: bool = field(default=True, init=False)
    actionable: bool = field(default=False)
    bet_placed: bool = field(default=False)
    alerted: bool = field(default=False)
    not_operational_advice: bool = field(default=True, init=False)

    def __post_init__(self):
        if self.actionable:
            raise ValueError("actionable=True is strictly forbidden.")
        if self.bet_placed:
            raise ValueError("bet_placed=True is strictly forbidden.")
        if self.alerted:
            raise ValueError("alerted=True is strictly forbidden.")
        
        _validate_safe_string(self.title)
        _validate_safe_string(self.summary)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "generated_at": self.generated_at,
            "sections": [s.to_dict() for s in self.sections],
            "summary": self.summary,
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "learning_mode": self.learning_mode,
            "actionable": self.actionable,
            "bet_placed": self.bet_placed,
            "alerted": self.alerted,
            "not_operational_advice": self.not_operational_advice
        }
