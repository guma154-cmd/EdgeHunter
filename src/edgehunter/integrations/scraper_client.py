"""
Scraping controlado.

Habilitado apenas via SCRAPER_ENABLED=true no .env.
Por padrão retorna snapshot vazio sem chamadas de rede.
Sem bypass, captcha, login ou JavaScript remoto.
"""
import os
import time
from typing import Optional

_SAFE_SNAPSHOT_TEMPLATE = {
    "status": "EMPTY",
    "source_url": None,
    "raw_content": None,
    "items": [],
    "is_simulated": True,
    "actionable": False,
    "not_operational_advice": True,
    "dry_run": False,
    "error": None,
}


def _load_scraper_config(env: Optional[dict] = None) -> dict:
    e = env or {}
    return {
        "enabled": (e.get("SCRAPER_ENABLED") or os.environ.get("SCRAPER_ENABLED", "false")).lower() == "true",
        "source_url": e.get("SCRAPER_SOURCE_URL") or os.environ.get("SCRAPER_SOURCE_URL", ""),
        "timeout": int(e.get("SCRAPER_TIMEOUT_SECONDS") or os.environ.get("SCRAPER_TIMEOUT_SECONDS", "10")),
        "rate_limit": float(e.get("SCRAPER_RATE_LIMIT_SECONDS") or os.environ.get("SCRAPER_RATE_LIMIT_SECONDS", "5")),
        "user_agent": e.get("SCRAPER_USER_AGENT") or os.environ.get("SCRAPER_USER_AGENT", "EdgeHunterLocalResearch/1.0"),
        "dry_run": (e.get("EDGEHUNTER_RUNTIME_DRY_RUN") or os.environ.get("EDGEHUNTER_RUNTIME_DRY_RUN", "true")).lower() == "true",
    }


def _empty_snapshot(config: dict, reason: str = "disabled") -> dict:
    snap = dict(_SAFE_SNAPSHOT_TEMPLATE)
    snap["error"] = reason
    snap["dry_run"] = config.get("dry_run", True)
    return snap


def fetch_source_snapshot(url: str, config: dict, _mock_response: Optional[str] = None) -> dict:
    """
    Busca snapshot da fonte configurada.
    Em testes, passar _mock_response para evitar rede real.
    Sem bypass, captcha, login ou JavaScript remoto.
    """
    snap = dict(_SAFE_SNAPSHOT_TEMPLATE)
    snap["source_url"] = url
    snap["dry_run"] = config.get("dry_run", True)

    if not url:
        snap["error"] = "missing_url"
        return snap

    if snap["dry_run"]:
        snap["status"] = "DRY_RUN"
        snap["raw_content"] = None
        return snap

    if _mock_response is not None:
        snap["raw_content"] = _mock_response
        snap["status"] = "OK"
        return snap

    # Chamada real — só ocorre em produção com flag explícita
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": config["user_agent"]})
        with urllib.request.urlopen(req, timeout=config["timeout"]) as resp:
            snap["raw_content"] = resp.read().decode("utf-8", errors="replace")
            snap["status"] = "OK"
    except TimeoutError:
        snap["error"] = "timeout"
    except Exception as e:
        snap["error"] = f"error:{type(e).__name__}"

    return snap


def parse_source_snapshot(raw: dict) -> dict:
    """
    Parser determinístico do snapshot.
    Retorna lista de items técnicos sem dados financeiros acionáveis.
    """
    result = {
        "status": raw.get("status", "EMPTY"),
        "items": [],
        "is_simulated": True,
        "actionable": False,
        "not_operational_advice": True,
    }

    content = raw.get("raw_content") or ""
    if not content:
        return result

    # Parser simples: divide por linhas, ignora vazias
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    result["items"] = lines[:100]  # limite seguro de 100 items
    result["status"] = "PARSED"
    return result


def run_scraper_once(env: Optional[dict] = None, _mock_response: Optional[str] = None) -> dict:
    """
    Ponto de entrada principal do scraper.
    Se SCRAPER_ENABLED=false → retorna snapshot vazio.
    Se URL ausente → retorna snapshot vazio.
    Aplica rate limit após fetch.
    """
    config = _load_scraper_config(env)

    if not config["enabled"]:
        return _empty_snapshot(config, reason="scraper_disabled")

    if not config["source_url"]:
        return _empty_snapshot(config, reason="missing_source_url")

    snap = fetch_source_snapshot(config["source_url"], config, _mock_response=_mock_response)

    if not config["dry_run"] and _mock_response is None:
        time.sleep(config["rate_limit"])

    parsed = parse_source_snapshot(snap)
    parsed["source_url"] = config["source_url"]
    return parsed
