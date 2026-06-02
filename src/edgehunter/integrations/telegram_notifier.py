"""
Telegram técnico controlado.

Habilitado apenas via TELEGRAM_ENABLED=true no .env.
Apenas notificações técnicas. Sem comandos operacionais.
"""
import os
from typing import Optional

_FORBIDDEN_MESSAGE_TERMS = [
    "aposta", "apostar", "entrada", "sinal de aposta",
    "recomendação operacional", "lucro", "gain", "stake",
    "kelly", "bankroll", "wager", "bet_amount",
    "execute", "execution", "place_bet", "autoevolution",
    "ordem automática", "comando de ação",
]

_SAFE_RESULT_TEMPLATE = {
    "sent": False,
    "is_simulated": True,
    "actionable": False,
    "not_operational_advice": True,
    "error": None,
    "message_text": None,
}


def _load_telegram_config(env: Optional[dict] = None) -> dict:
    e = env or {}
    return {
        "enabled": (e.get("TELEGRAM_ENABLED") or os.environ.get("TELEGRAM_ENABLED", "false")).lower() == "true",
        "bot_token": e.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "chat_id": e.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID", ""),
        "timeout": int(e.get("TELEGRAM_TIMEOUT_SECONDS") or os.environ.get("TELEGRAM_TIMEOUT_SECONDS", "5")),
    }


def _contains_forbidden_message(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in _FORBIDDEN_MESSAGE_TERMS)


def build_telegram_message(event_type: str, data: dict) -> str:
    """
    Constrói mensagem técnica para Telegram.
    Bloqueia linguagem proibida.
    """
    allowed_events = {
        "runtime_status": "📊 Runtime Status",
        "signal_summary": "📈 Resumo Técnico",
        "daily_report": "📋 Relatório Diário",
        "error_alert": "⚠️ Alerta Técnico",
        "fallback_warning": "🔄 Aviso de Fallback",
        "scraper_status": "🔍 Status Scraper",
        "gemini_status": "🤖 Status Gemini",
    }

    header = allowed_events.get(event_type, f"📌 {event_type}")
    lines = [header]

    for key, val in data.items():
        # Bloquear campos com valor proibido
        val_str = str(val)
        if _contains_forbidden_message(val_str):
            val_str = "[BLOCKED]"
        lines.append(f"  {key}: {val_str}")

    return "\n".join(lines)


def send_telegram_message(
    token: str,
    chat_id: str,
    text: str,
    config: dict,
    _mock_send: Optional[callable] = None,
) -> dict:
    """
    Envia mensagem técnica ao Telegram.
    Em testes, passar _mock_send para evitar rede real.
    Bloqueia mensagem com linguagem proibida.
    """
    result = dict(_SAFE_RESULT_TEMPLATE)
    result["message_text"] = text

    if _contains_forbidden_message(text):
        result["error"] = "forbidden_content_in_message"
        return result

    if _mock_send is not None:
        return _mock_send(token, chat_id, text, config)

    # Envio real — só em produção com flag explícita
    import urllib.request
    import json as _json

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = _json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()

    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=config["timeout"]) as resp:
            data = _json.loads(resp.read().decode())
            if data.get("ok"):
                result["sent"] = True
            else:
                result["error"] = f"api_error:{data.get('description', 'unknown')}"
    except TimeoutError:
        result["error"] = "timeout"
    except Exception as e:
        result["error"] = f"error:{type(e).__name__}"

    return result


def notify_runtime_status(status_data: dict, env: Optional[dict] = None, _mock_send: Optional[callable] = None) -> dict:
    """Notifica status do runtime."""
    config = _load_telegram_config(env)
    if not config["enabled"]:
        return {**_SAFE_RESULT_TEMPLATE, "error": "telegram_disabled"}
    if not config["bot_token"]:
        return {**_SAFE_RESULT_TEMPLATE, "error": "missing_bot_token"}
    if not config["chat_id"]:
        return {**_SAFE_RESULT_TEMPLATE, "error": "missing_chat_id"}

    text = build_telegram_message("runtime_status", status_data)
    return send_telegram_message(config["bot_token"], config["chat_id"], text, config, _mock_send=_mock_send)


def notify_signal_summary(summary_data: dict, env: Optional[dict] = None, _mock_send: Optional[callable] = None) -> dict:
    """Notifica resumo técnico de sinais (GREEN_SIM/RED_SIM como labels técnicos)."""
    config = _load_telegram_config(env)
    if not config["enabled"]:
        return {**_SAFE_RESULT_TEMPLATE, "error": "telegram_disabled"}
    if not config["bot_token"]:
        return {**_SAFE_RESULT_TEMPLATE, "error": "missing_bot_token"}
    if not config["chat_id"]:
        return {**_SAFE_RESULT_TEMPLATE, "error": "missing_chat_id"}

    text = build_telegram_message("signal_summary", summary_data)
    return send_telegram_message(config["bot_token"], config["chat_id"], text, config, _mock_send=_mock_send)
