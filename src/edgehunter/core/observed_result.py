from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ObservedResultStatus(str, Enum):
    POSITIVE_OBSERVED = "POSITIVE_OBSERVED"
    NEGATIVE_OBSERVED = "NEGATIVE_OBSERVED"
    UNRESOLVED = "UNRESOLVED"
    INVALIDATED = "INVALIDATED"


class ObservedResultSource(str, Enum):
    LOCAL_CSV = "LOCAL_CSV"
    LOCAL_JSON = "LOCAL_JSON"
    INTERNAL_DATASET = "INTERNAL_DATASET"
    MANUAL_TEST_FIXTURE = "MANUAL_TEST_FIXTURE"


def _check_operational_language(text: str) -> None:
    if not text:
        return
    forbidden = [
        "aposta", "apostar", "entrada", "sinal de aposta", "recomendado",
        "recomendação operacional", "recomendacao operacional", "lucro", "gain",
        "stake", "kelly", "bankroll", "bet_amount", "wager", "execute", "execution",
        "place_bet", "telegram", "scheduler", "autoevolution"
    ]
    lower_text = text.lower()
    for word in forbidden:
        if word in lower_text:
            raise ValueError(f"Operational language blocked: {word}")


@dataclass(frozen=True)
class ObservedResult:
    result_id: str
    signal_id: str
    classification_id: str
    opportunity_id: str
    match_id: str
    result_status: ObservedResultStatus
    observed_at: datetime
    source: ObservedResultSource
    source_ref: str
    notes: str
    is_simulated: bool = field(default=True, init=False)
    paper_trading: bool = field(default=True, init=False)
    learning_mode: bool = field(default=True, init=False)
    actionable: bool = field(default=False, init=False)
    bet_placed: bool = field(default=False, init=False)
    alerted: bool = field(default=False, init=False)
    not_operational_advice: bool = field(default=True, init=False)

    def __post_init__(self):
        # Mandatory string fields check
        for attr in ["result_id", "signal_id", "classification_id", "opportunity_id", "match_id"]:
            val = getattr(self, attr)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"{attr} cannot be empty.")
                
        # Status and Source Enum checks
        if not isinstance(self.result_status, ObservedResultStatus):
            raise ValueError("Invalid result_status.")
        if not isinstance(self.source, ObservedResultSource):
            raise ValueError("Invalid source.")
            
        # Timezone check
        if not isinstance(self.observed_at, datetime):
            raise ValueError("observed_at must be a datetime.")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware.")
            
        # Optional string fields type check
        if not isinstance(self.source_ref, str):
            raise ValueError("source_ref must be a string.")
        if not isinstance(self.notes, str):
            raise ValueError("notes must be a string.")
            
        # Operational language check
        _check_operational_language(self.source_ref)
        _check_operational_language(self.notes)

    def to_dict(self) -> dict:
        return {
            "result_id": self.result_id,
            "signal_id": self.signal_id,
            "classification_id": self.classification_id,
            "opportunity_id": self.opportunity_id,
            "match_id": self.match_id,
            "result_status": self.result_status.value,
            "observed_at": self.observed_at.isoformat(),
            "source": self.source.value,
            "source_ref": self.source_ref,
            "notes": self.notes,
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "learning_mode": self.learning_mode,
            "actionable": self.actionable,
            "bet_placed": self.bet_placed,
            "alerted": self.alerted,
            "not_operational_advice": self.not_operational_advice
        }
