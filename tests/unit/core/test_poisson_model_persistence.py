"""Tests for STORY-02-003 PoissonModel local persistence."""

from __future__ import annotations

from dataclasses import dataclass, replace
import inspect
import json
import math
from pathlib import Path

import pytest

from src.edgehunter.core import poisson_model as poisson_module
from src.edgehunter.core.poisson_model import (
    MODEL_SCHEMA_VERSION,
    MODEL_VERSION,
    PoissonModel,
)


@dataclass(frozen=True)
class SyntheticMatch:
    match_id: str
    home_team: str
    away_team: str
    league: str
    home_goals: int
    away_goals: int
    result: str
    valid_for_analysis: bool = True
    status: str = "finished"


def _build_training_matches() -> list[SyntheticMatch]:
    return [
        SyntheticMatch("m1", "Strong FC", "Weak FC", "Brasileirao", 3, 0, "home_win"),
        SyntheticMatch("m2", "Strong FC", "Mid FC", "Brasileirao", 2, 0, "home_win"),
        SyntheticMatch("m3", "Mid FC", "Weak FC", "Brasileirao", 2, 1, "home_win"),
        SyntheticMatch("m4", "Weak FC", "Strong FC", "Brasileirao", 0, 2, "away_win"),
        SyntheticMatch("m5", "Mid FC", "Strong FC", "Brasileirao", 0, 1, "away_win"),
        SyntheticMatch("m6", "Weak FC", "Mid FC", "Brasileirao", 0, 1, "away_win"),
    ]


def _train_model() -> PoissonModel:
    model = PoissonModel(max_goals=8)
    model.fit(_build_training_matches())
    assert model.last_training_result is not None
    model.last_training_result = replace(model.last_training_result, warning=None)
    if model.last_fit_summary is not None:
        model.last_fit_summary["warning"] = None
    return model


def _save_model(tmp_path: Path) -> tuple[PoissonModel, Path]:
    model = _train_model()
    path = tmp_path / "poisson_model.json"
    model.save(path)
    return model, path


def _load_payload(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_payload(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_trained_model_saves_local_json_file(tmp_path: Path) -> None:
    model = _train_model()
    path = tmp_path / "model.json"

    model.save(path)

    assert path.exists()
    payload = _load_payload(path)
    assert payload["schema_version"] == MODEL_SCHEMA_VERSION
    assert payload["model_version"] == MODEL_VERSION
    assert isinstance(payload["created_at"], str)
    assert isinstance(payload["saved_at"], str)


def test_saved_file_is_valid_json_with_required_state(tmp_path: Path) -> None:
    _model, path = _save_model(tmp_path)

    payload = _load_payload(path)

    assert set(payload) >= {
        "schema_version",
        "model_version",
        "created_at",
        "saved_at",
        "league_avg_home_goals",
        "league_avg_away_goals",
        "home_advantage",
        "max_goals",
        "neutral_strength",
        "trained",
        "trained_league",
        "team_strengths",
        "last_training_result",
    }


def test_load_reconstructs_poisson_model(tmp_path: Path) -> None:
    model, path = _save_model(tmp_path)

    loaded = PoissonModel.load(path)

    assert isinstance(loaded, PoissonModel)
    assert loaded.trained is True
    assert loaded.trained_league == model.trained_league
    assert loaded.max_goals == model.max_goals


def test_predict_match_is_equivalent_before_and_after_load(tmp_path: Path) -> None:
    model, path = _save_model(tmp_path)
    before = model.predict_match(home_team="Strong FC", away_team="Weak FC")

    loaded = PoissonModel.load(path)
    after = loaded.predict_match(home_team="Strong FC", away_team="Weak FC")

    assert after["used_fallback"] == before["used_fallback"]
    for field_name in (
        "home_win",
        "draw",
        "away_win",
        "expected_home_goals",
        "expected_away_goals",
    ):
        assert after[field_name] == pytest.approx(before[field_name], abs=1e-12)


def test_sanity_check_works_after_load(tmp_path: Path) -> None:
    _model, path = _save_model(tmp_path)

    loaded = PoissonModel.load(path)
    result = loaded.sanity_check()

    assert result.passed is True
    assert result.metrics["canary_probability_sum"] == pytest.approx(1.0, abs=1e-6)


def test_last_training_result_is_preserved(tmp_path: Path) -> None:
    model, path = _save_model(tmp_path)

    loaded = PoissonModel.load(path)

    assert loaded.last_training_result is not None
    assert model.last_training_result is not None
    assert loaded.last_training_result.to_dict() == model.last_training_result.to_dict()


def test_home_advantage_and_league_averages_are_preserved(tmp_path: Path) -> None:
    model, path = _save_model(tmp_path)

    loaded = PoissonModel.load(path)

    assert loaded.home_advantage == pytest.approx(model.home_advantage)
    assert loaded.league_avg_home_goals == pytest.approx(model.league_avg_home_goals)
    assert loaded.league_avg_away_goals == pytest.approx(model.league_avg_away_goals)


def test_team_strengths_are_preserved(tmp_path: Path) -> None:
    model, path = _save_model(tmp_path)

    loaded = PoissonModel.load(path)

    for team in ("Strong FC", "Mid FC", "Weak FC"):
        original = model.get_team_strength(team)
        restored = loaded.get_team_strength(team)
        assert restored.attack == pytest.approx(original.attack)
        assert restored.defense == pytest.approx(original.defense)


def test_load_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        PoissonModel.load(tmp_path / "missing.json")


def test_load_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid PoissonModel JSON"):
        PoissonModel.load(path)


def test_load_rejects_missing_required_fields(tmp_path: Path) -> None:
    _model, path = _save_model(tmp_path)
    payload = _load_payload(path)
    del payload["team_strengths"]
    _write_payload(path, payload)

    with pytest.raises(ValueError, match="missing required field: team_strengths"):
        PoissonModel.load(path)


def test_load_rejects_incompatible_schema_version(tmp_path: Path) -> None:
    _model, path = _save_model(tmp_path)
    payload = _load_payload(path)
    payload["schema_version"] = MODEL_SCHEMA_VERSION + 1
    _write_payload(path, payload)

    with pytest.raises(ValueError, match="unsupported PoissonModel schema_version"):
        PoissonModel.load(path)


def test_load_rejects_incompatible_model_version(tmp_path: Path) -> None:
    _model, path = _save_model(tmp_path)
    payload = _load_payload(path)
    payload["model_version"] = "future-model"
    _write_payload(path, payload)

    with pytest.raises(ValueError, match="unsupported PoissonModel model_version"):
        PoissonModel.load(path)


def test_load_rejects_nan_or_infinite_values(tmp_path: Path) -> None:
    _model, path = _save_model(tmp_path)
    payload = _load_payload(path)
    payload["league_avg_home_goals"] = float("nan")
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid JSON numeric constant|non-finite"):
        PoissonModel.load(path)


def test_load_rejects_non_finite_nested_values(tmp_path: Path) -> None:
    _model, path = _save_model(tmp_path)
    text = path.read_text(encoding="utf-8")
    text = text.replace('"attack":', '"attack": 1e999, "attack_original":', 1)
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="non-finite"):
        PoissonModel.load(path)


def test_save_rejects_untrained_model(tmp_path: Path) -> None:
    model = PoissonModel()

    with pytest.raises(ValueError, match="trained model is required before save"):
        model.save(tmp_path / "untrained.json")


def test_persistence_module_does_not_access_database_network_or_external_services() -> None:
    source = inspect.getsource(poisson_module)

    assert "sqlite3" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "httpx" not in source
    assert "socket" not in source
    assert "telegram" not in source.lower()
    assert "scraper" not in source.lower()
    assert "OddsHistorian" not in source
