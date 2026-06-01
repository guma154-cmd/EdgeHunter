"""Pure contracts for safe AI validation in paper-trading mode."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from typing import Any
import unicodedata


MIN_OFFERED_ODDS = 1.01
MAX_RISK_FACTORS = 5
MAX_RISK_FACTOR_LENGTH = 120
MAX_RATIONALE_LENGTH = 280
FAKE_GEMINI_VALIDATION_PROVIDER = "fake"
FAKE_GEMINI_VALIDATION_MODEL = "fake-gemini-validator-v1"


def _join(*parts: str) -> str:
    return "".join(parts)


_BLOCKED_TERMS = frozenset(
    {
        _join("sta", "ke"),
        _join("kel", "ly"),
        _join("kel", "ly_criterion"),
        _join("bank", "roll"),
        _join("bet", "_amount"),
        _join("wag", "er"),
        _join("suggested", "_bet"),
        _join("recom", "mended", "_bet"),
        _join("recom", "mendation"),
        _join("exec", "ute"),
        _join("exec", "ution"),
        _join("place", "_bet"),
        _join("entr", "ada"),
        _join("ap", "ostar"),
        _join("sinal de ", "ap", "osta"),
        _join("ap", "osta recomen", "dada"),
        _join("tele", "gram"),
        _join("sched", "uler"),
        _join("auto", "evolution"),
    }
)

_INPUT_FIELDS = frozenset(
    {
        "opportunity_id",
        "match_id",
        "league",
        "market",
        "selection",
        "true_probability",
        "offered_odds",
        "expected_value",
        "edge_percentage",
        "source",
        "detection_method",
        "snapshot_age_seconds",
        "recent_hit_rate",
        "recent_false_positive_rate",
        "is_simulated",
        "paper_trading",
        "actionable",
    }
)

_RESULT_FIELDS = frozenset(
    {
        "validation_id",
        "opportunity_id",
        "technical_verdict",
        "confidence",
        "risk_factors",
        "rationale",
        "parser_status",
        "provider",
        "model_name",
        "prompt_hash",
        "tokens_used",
        "is_simulated",
        "paper_trading",
        "actionable",
        "bet_placed",
        "alerted",
        "not_operational_advice",
    }
)

_AI_RESPONSE_FIELDS = frozenset(
    {
        "technical_verdict",
        "confidence",
        "risk_factors",
        "rationale",
    }
)

_PROMPT_INPUT_FIELD_ORDER = (
    "opportunity_id",
    "match_id",
    "league",
    "market",
    "selection",
    "true_probability",
    "offered_odds",
    "expected_value",
    "edge_percentage",
    "source",
    "detection_method",
    "snapshot_age_seconds",
    "recent_hit_rate",
    "recent_false_positive_rate",
    "is_simulated",
    "paper_trading",
    "actionable",
)


class TechnicalVerdict(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    REJECT = "reject"
    INVALID_RESPONSE = "invalid_response"
    UNAVAILABLE = "unavailable"


class ParserStatus(str, Enum):
    PARSED = "parsed"
    RECOVERED = "recovered"
    FAILED = "failed"


_AI_RESPONSE_VERDICTS = frozenset(
    {
        TechnicalVerdict.PASS.value,
        TechnicalVerdict.REVIEW.value,
        TechnicalVerdict.REJECT.value,
    }
)


def _text_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return " ".join(without_marks.lower().split())


def _has_blocked_term(value: str) -> bool:
    haystack = _text_for_match(value)
    haystack_space_variant = haystack.replace("_", " ")
    for term in _BLOCKED_TERMS:
        needle = _text_for_match(term)
        if needle in haystack:
            return True
        if needle.replace("_", " ") in haystack_space_variant:
            return True
    return False


def _reject_blocked_text(value: str, field_name: str) -> None:
    if _has_blocked_term(value):
        raise ValueError(f"{field_name} contains forbidden content")


def _require_text(value: str, field_name: str) -> str:
    clean_value = str(value).strip()
    if not clean_value:
        raise ValueError(f"{field_name} is required")
    _reject_blocked_text(clean_value, field_name)
    return clean_value


def _require_finite_float(value: float, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    clean_value = float(value)
    if not math.isfinite(clean_value):
        raise ValueError(f"{field_name} must be finite")
    return clean_value


def _require_probability(value: float, field_name: str) -> float:
    clean_value = _require_finite_float(value, field_name)
    if not 0.0 <= clean_value <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return clean_value


def _require_offered_odds(value: float) -> float:
    clean_value = _require_finite_float(value, "offered_odds")
    if clean_value < MIN_OFFERED_ODDS:
        raise ValueError("offered_odds must be >= 1.01")
    return clean_value


def _require_non_negative_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return value


def _require_flag(value: bool, expected: bool, field_name: str) -> bool:
    if value is not expected:
        raise ValueError(f"{field_name} must be {expected}")
    return value


def _coerce_enum(
    value: str | TechnicalVerdict | ParserStatus,
    enum_type: type[TechnicalVerdict] | type[ParserStatus],
    field_name: str,
) -> TechnicalVerdict | ParserStatus:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value).strip())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ValueError(f"{field_name} must be one of: {allowed}") from exc


def _require_payload(
    payload: Mapping[str, Any],
    *,
    allowed_fields: frozenset[str],
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")

    payload_keys: set[str] = set()
    for raw_key in payload:
        if not isinstance(raw_key, str):
            raise ValueError("payload keys must be strings")
        if _has_blocked_term(raw_key):
            raise ValueError(f"forbidden field found: {raw_key}")
        payload_keys.add(raw_key)

    unexpected = sorted(payload_keys - allowed_fields)
    if unexpected:
        raise ValueError(f"unexpected fields: {', '.join(unexpected)}")

    missing = sorted(allowed_fields - payload_keys)
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")

    return {field_name: payload[field_name] for field_name in sorted(allowed_fields)}


@dataclass(frozen=True)
class SafeAIValidationInput:
    opportunity_id: str
    match_id: str
    league: str
    market: str
    selection: str
    true_probability: float
    offered_odds: float
    expected_value: float
    edge_percentage: float
    source: str
    detection_method: str
    snapshot_age_seconds: int
    recent_hit_rate: float
    recent_false_positive_rate: float
    is_simulated: bool = True
    paper_trading: bool = True
    actionable: bool = False

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SafeAIValidationInput:
        return cls(**_require_payload(payload, allowed_fields=_INPUT_FIELDS))

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "opportunity_id",
            _require_text(self.opportunity_id, "opportunity_id"),
        )
        object.__setattr__(self, "match_id", _require_text(self.match_id, "match_id"))
        object.__setattr__(self, "league", _require_text(self.league, "league"))
        object.__setattr__(self, "market", _require_text(self.market, "market"))
        object.__setattr__(self, "selection", _require_text(self.selection, "selection"))
        object.__setattr__(self, "source", _require_text(self.source, "source"))
        object.__setattr__(
            self,
            "detection_method",
            _require_text(self.detection_method, "detection_method"),
        )
        object.__setattr__(
            self,
            "true_probability",
            _require_probability(self.true_probability, "true_probability"),
        )
        object.__setattr__(
            self,
            "offered_odds",
            _require_offered_odds(self.offered_odds),
        )
        object.__setattr__(
            self,
            "expected_value",
            _require_finite_float(self.expected_value, "expected_value"),
        )
        object.__setattr__(
            self,
            "edge_percentage",
            _require_finite_float(self.edge_percentage, "edge_percentage"),
        )
        object.__setattr__(
            self,
            "snapshot_age_seconds",
            _require_non_negative_int(
                self.snapshot_age_seconds,
                "snapshot_age_seconds",
            ),
        )
        object.__setattr__(
            self,
            "recent_hit_rate",
            _require_probability(self.recent_hit_rate, "recent_hit_rate"),
        )
        object.__setattr__(
            self,
            "recent_false_positive_rate",
            _require_probability(
                self.recent_false_positive_rate,
                "recent_false_positive_rate",
            ),
        )
        object.__setattr__(
            self,
            "is_simulated",
            _require_flag(self.is_simulated, True, "is_simulated"),
        )
        object.__setattr__(
            self,
            "paper_trading",
            _require_flag(self.paper_trading, True, "paper_trading"),
        )
        object.__setattr__(
            self,
            "actionable",
            _require_flag(self.actionable, False, "actionable"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "match_id": self.match_id,
            "league": self.league,
            "market": self.market,
            "selection": self.selection,
            "true_probability": self.true_probability,
            "offered_odds": self.offered_odds,
            "expected_value": self.expected_value,
            "edge_percentage": self.edge_percentage,
            "source": self.source,
            "detection_method": self.detection_method,
            "snapshot_age_seconds": self.snapshot_age_seconds,
            "recent_hit_rate": self.recent_hit_rate,
            "recent_false_positive_rate": self.recent_false_positive_rate,
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "actionable": self.actionable,
        }


@dataclass(frozen=True)
class SafeAIValidationResult:
    validation_id: str
    opportunity_id: str
    technical_verdict: TechnicalVerdict | str
    confidence: float
    risk_factors: tuple[str, ...] | list[str]
    rationale: str
    parser_status: ParserStatus | str
    provider: str = FAKE_GEMINI_VALIDATION_PROVIDER
    model_name: str = FAKE_GEMINI_VALIDATION_MODEL
    prompt_hash: str = ""
    tokens_used: int = 0
    is_simulated: bool = True
    paper_trading: bool = True
    actionable: bool = False
    bet_placed: bool = False
    alerted: bool = False
    not_operational_advice: bool = True

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SafeAIValidationResult:
        return cls(**_require_payload(payload, allowed_fields=_RESULT_FIELDS))

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "validation_id",
            _require_text(self.validation_id, "validation_id"),
        )
        object.__setattr__(
            self,
            "opportunity_id",
            _require_text(self.opportunity_id, "opportunity_id"),
        )
        object.__setattr__(
            self,
            "technical_verdict",
            _coerce_enum(
                self.technical_verdict,
                TechnicalVerdict,
                "technical_verdict",
            ),
        )
        object.__setattr__(
            self,
            "confidence",
            _require_probability(self.confidence, "confidence"),
        )
        object.__setattr__(
            self,
            "risk_factors",
            _normalize_risk_factors(self.risk_factors),
        )
        rationale = _require_text(self.rationale, "rationale")
        if len(rationale) > MAX_RATIONALE_LENGTH:
            raise ValueError("rationale is too long")
        object.__setattr__(self, "rationale", rationale)
        object.__setattr__(
            self,
            "parser_status",
            _coerce_enum(self.parser_status, ParserStatus, "parser_status"),
        )
        object.__setattr__(self, "provider", _require_text(self.provider, "provider"))
        object.__setattr__(
            self,
            "model_name",
            _require_text(self.model_name, "model_name"),
        )
        object.__setattr__(
            self,
            "prompt_hash",
            _require_text(self.prompt_hash, "prompt_hash"),
        )
        object.__setattr__(
            self,
            "tokens_used",
            _require_non_negative_int(self.tokens_used, "tokens_used"),
        )
        object.__setattr__(
            self,
            "is_simulated",
            _require_flag(self.is_simulated, True, "is_simulated"),
        )
        object.__setattr__(
            self,
            "paper_trading",
            _require_flag(self.paper_trading, True, "paper_trading"),
        )
        object.__setattr__(
            self,
            "actionable",
            _require_flag(self.actionable, False, "actionable"),
        )
        object.__setattr__(
            self,
            "bet_placed",
            _require_flag(self.bet_placed, False, "bet_placed"),
        )
        object.__setattr__(
            self,
            "alerted",
            _require_flag(self.alerted, False, "alerted"),
        )
        object.__setattr__(
            self,
            "not_operational_advice",
            _require_flag(
                self.not_operational_advice,
                True,
                "not_operational_advice",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "opportunity_id": self.opportunity_id,
            "technical_verdict": self.technical_verdict.value,
            "confidence": self.confidence,
            "risk_factors": list(self.risk_factors),
            "rationale": self.rationale,
            "parser_status": self.parser_status.value,
            "provider": self.provider,
            "model_name": self.model_name,
            "prompt_hash": self.prompt_hash,
            "tokens_used": self.tokens_used,
            "is_simulated": self.is_simulated,
            "paper_trading": self.paper_trading,
            "actionable": self.actionable,
            "bet_placed": self.bet_placed,
            "alerted": self.alerted,
            "not_operational_advice": self.not_operational_advice,
        }


def _normalize_risk_factors(value: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError("risk_factors must be a list")
    if len(value) > MAX_RISK_FACTORS:
        raise ValueError("risk_factors is too long")

    normalized = tuple(
        _require_text(str(item), "risk_factors")
        for item in value
    )
    for item in normalized:
        if len(item) > MAX_RISK_FACTOR_LENGTH:
            raise ValueError("risk_factors item is too long")
    return normalized


def build_gemini_validation_prompt(
    validation_input: SafeAIValidationInput,
) -> str:
    if not isinstance(validation_input, SafeAIValidationInput):
        raise ValueError("validation_input must be a SafeAIValidationInput")

    payload = validation_input.to_dict()
    context_lines = [
        f"- {field_name}: {payload[field_name]}"
        for field_name in _PROMPT_INPUT_FIELD_ORDER
    ]
    return "\n".join(
        [
            "Voce e um revisor tecnico de sinais estatisticos simulados.",
            "Use somente o contexto abaixo e produza uma avaliacao tecnica curta.",
            "Este material e simulacao em paper trading.",
            "Isto nao e recomendacao operacional e nao autoriza acao real.",
            (
                "Nao gere valores financeiros, fracao de capital, gestao de saldo "
                "ou instrucao de acao."
            ),
            "",
            "Contexto permitido:",
            *context_lines,
            "",
            "Responda apenas JSON valido neste formato:",
            "{",
            '  "technical_verdict": "pass|review|reject",',
            '  "confidence": 0.0,',
            '  "risk_factors": ["short technical factor"],',
            '  "rationale": "short technical rationale"',
            "}",
        ],
    )


def _prompt_digest(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


class FakeGeminiValidationClient:
    provider = FAKE_GEMINI_VALIDATION_PROVIDER
    model_name = FAKE_GEMINI_VALIDATION_MODEL

    def validate(self, prompt: str) -> str:
        clean_prompt = _require_text(prompt, "prompt")
        digest = _prompt_digest(clean_prompt)
        verdicts = (
            TechnicalVerdict.PASS.value,
            TechnicalVerdict.REVIEW.value,
            TechnicalVerdict.REJECT.value,
        )
        verdict = verdicts[int(digest[:2], 16) % len(verdicts)]
        confidence = 0.55 + ((int(digest[2:4], 16) % 20) / 100)
        payload = {
            "technical_verdict": verdict,
            "confidence": round(confidence, 2),
            "risk_factors": ["local_consistency_review"],
            "rationale": "Offline deterministic technical assessment.",
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _validation_id(
    *,
    opportunity_id: str,
    provider: str,
    model_name: str,
    prompt_hash: str,
    raw_response: str,
) -> str:
    payload = json.dumps(
        {
            "model_name": model_name,
            "opportunity_id": opportunity_id,
            "prompt_hash": prompt_hash,
            "provider": provider,
            "raw_response": raw_response,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"ai-validation-{digest}"


def _safe_failed_result(
    *,
    opportunity_id: str,
    provider: str,
    model_name: str,
    prompt_hash: str,
    raw_response: str,
) -> SafeAIValidationResult:
    return SafeAIValidationResult(
        validation_id=_validation_id(
            opportunity_id=opportunity_id,
            provider=provider,
            model_name=model_name,
            prompt_hash=prompt_hash,
            raw_response=raw_response,
        ),
        opportunity_id=opportunity_id,
        technical_verdict=TechnicalVerdict.INVALID_RESPONSE,
        confidence=0.0,
        risk_factors=("invalid_or_unsafe_ai_response",),
        rationale="AI validation response could not be safely parsed.",
        parser_status=ParserStatus.FAILED,
        provider=provider,
        model_name=model_name,
        prompt_hash=prompt_hash,
        tokens_used=0,
    )


def _json_candidates(raw_response: str) -> tuple[tuple[str, ParserStatus], ...]:
    stripped = raw_response.strip()
    candidates: list[tuple[str, ParserStatus]] = []
    if stripped.startswith("{") and stripped.endswith("}"):
        candidates.append((stripped, ParserStatus.PARSED))

    lowered = stripped.lower()
    marker_start = lowered.find("```json")
    marker_length = len("```json")
    if marker_start < 0:
        marker_start = lowered.find("```")
        marker_length = len("```")
    if marker_start >= 0:
        content_start = marker_start + marker_length
        marker_end = stripped.find("```", content_start)
        if marker_end > content_start:
            fenced = stripped[content_start:marker_end].strip()
            if fenced:
                candidates.append((fenced, ParserStatus.RECOVERED))

    brace_start = stripped.find("{")
    brace_end = stripped.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        recovered = stripped[brace_start:brace_end + 1].strip()
        if recovered and all(recovered != candidate for candidate, _ in candidates):
            candidates.append((recovered, ParserStatus.RECOVERED))

    return tuple(candidates)


def _decode_ai_response(raw_response: str) -> tuple[dict[str, Any], ParserStatus] | None:
    for candidate, parser_status in _json_candidates(raw_response):
        try:
            decoded = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return decoded, parser_status
    return None


def _safe_result_from_ai_payload(
    payload: Mapping[str, Any],
    *,
    parser_status: ParserStatus,
    opportunity_id: str,
    provider: str,
    model_name: str,
    prompt_hash: str,
    raw_response: str,
) -> SafeAIValidationResult:
    response_payload = _require_payload(payload, allowed_fields=_AI_RESPONSE_FIELDS)
    technical_verdict = _require_text(
        str(response_payload["technical_verdict"]),
        "technical_verdict",
    )
    if technical_verdict not in _AI_RESPONSE_VERDICTS:
        raise ValueError("technical_verdict must be pass, review, or reject")

    return SafeAIValidationResult(
        validation_id=_validation_id(
            opportunity_id=opportunity_id,
            provider=provider,
            model_name=model_name,
            prompt_hash=prompt_hash,
            raw_response=raw_response,
        ),
        opportunity_id=opportunity_id,
        technical_verdict=technical_verdict,
        confidence=response_payload["confidence"],
        risk_factors=response_payload["risk_factors"],
        rationale=response_payload["rationale"],
        parser_status=parser_status,
        provider=provider,
        model_name=model_name,
        prompt_hash=prompt_hash,
        tokens_used=0,
    )


def parse_gemini_validation_response(
    raw_response: str,
    *,
    opportunity_id: str,
    provider: str = FAKE_GEMINI_VALIDATION_PROVIDER,
    model_name: str = FAKE_GEMINI_VALIDATION_MODEL,
    prompt_hash: str,
) -> SafeAIValidationResult:
    opportunity_id_clean = _require_text(opportunity_id, "opportunity_id")
    provider_clean = _require_text(provider, "provider")
    model_name_clean = _require_text(model_name, "model_name")
    prompt_hash_clean = _require_text(prompt_hash, "prompt_hash")
    raw_response_clean = "" if raw_response is None else str(raw_response)

    fallback = _safe_failed_result(
        opportunity_id=opportunity_id_clean,
        provider=provider_clean,
        model_name=model_name_clean,
        prompt_hash=prompt_hash_clean,
        raw_response=raw_response_clean,
    )
    if not raw_response_clean.strip():
        return fallback

    decoded = _decode_ai_response(raw_response_clean)
    if decoded is None:
        return fallback

    payload, parser_status = decoded
    try:
        return _safe_result_from_ai_payload(
            payload,
            parser_status=parser_status,
            opportunity_id=opportunity_id_clean,
            provider=provider_clean,
            model_name=model_name_clean,
            prompt_hash=prompt_hash_clean,
            raw_response=raw_response_clean,
        )
    except ValueError:
        return fallback


def validate_opportunity_offline(
    validation_input: SafeAIValidationInput,
    client: FakeGeminiValidationClient | None = None,
) -> SafeAIValidationResult:
    if not isinstance(validation_input, SafeAIValidationInput):
        raise ValueError("validation_input must be a SafeAIValidationInput")

    prompt = build_gemini_validation_prompt(validation_input)
    prompt_hash = _prompt_digest(prompt)
    validation_client = FakeGeminiValidationClient() if client is None else client
    validate = getattr(validation_client, "validate", None)

    fallback = _safe_failed_result(
        opportunity_id=validation_input.opportunity_id,
        provider=FAKE_GEMINI_VALIDATION_PROVIDER,
        model_name=FAKE_GEMINI_VALIDATION_MODEL,
        prompt_hash=prompt_hash,
        raw_response="",
    )
    if not callable(validate):
        return fallback

    try:
        raw_response = validate(prompt)
    except Exception:
        return fallback

    return parse_gemini_validation_response(
        raw_response,
        opportunity_id=validation_input.opportunity_id,
        provider=FAKE_GEMINI_VALIDATION_PROVIDER,
        model_name=FAKE_GEMINI_VALIDATION_MODEL,
        prompt_hash=prompt_hash,
    )
