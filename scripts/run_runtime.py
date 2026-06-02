"""
Ponto de entrada do runtime controlado EdgeHunter.

Uso:
    python scripts/run_runtime.py

Variáveis de ambiente obrigatórias (todas desabilitadas por padrão):
    EDGEHUNTER_RUNTIME_ENABLED=false
    EDGEHUNTER_RUNTIME_DRY_RUN=true
    EDGEHUNTER_RUNTIME_MAX_CYCLES=   (vazio = indefinido)
    EDGEHUNTER_RUNTIME_INTERVAL_SECONDS=300

    GEMINI_ENABLED=false
    SCRAPER_ENABLED=false
    TELEGRAM_ENABLED=false

Guardrails:
    - Sem execução financeira.
    - Sem stake, Kelly, bankroll.
    - Sem AutoEvolution.
    - Sem Telegram operacional.
    - Dry-run por padrão.
"""
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("edgehunter.run_runtime")


def _load_env_file(path: str = ".env") -> None:
    """Carrega variáveis do .env sem dependências externas."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def main() -> int:
    _load_env_file()

    from src.edgehunter.runtime.orchestrator import run_runtime, _load_runtime_config

    config = _load_runtime_config()

    if not config["enabled"]:
        logger.info("Runtime desabilitado (EDGEHUNTER_RUNTIME_ENABLED=false). Encerrando.")
        return 0

    dry = "DRY_RUN" if config["dry_run"] else "LIVE"
    max_c = str(config["max_cycles"]) if config["max_cycles"] else "∞"
    logger.info(f"Iniciando runtime | mode={dry} | interval={config['interval_seconds']}s | max_cycles={max_c}")

    summary = run_runtime()

    logger.info(f"Runtime encerrado | reason={summary['shutdown_reason']} | cycles={summary['cycles_executed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
