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

    def get_v(key, default):
        val = e.get(key) if key in e else os.environ.get(key)
        return val if val else default

    return {
        "enabled": str(get_v("TELEGRAM_ENABLED", "false")).lower() == "true",
        "bot_token": get_v("TELEGRAM_BOT_TOKEN", ""),
        "chat_id": get_v("TELEGRAM_CHAT_ID", ""),
        "timeout": int(get_v("TELEGRAM_TIMEOUT_SECONDS", "5")),
    }


def _contains_forbidden_message(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in _FORBIDDEN_MESSAGE_TERMS)


def build_telegram_message(event_type: str, data: dict) -> str:
    """
    Constrói mensagem técnica para Telegram.
    Bloqueia linguagem proibida.
    """
    # Sanitiza valores primeiro
    safe_data = {}
    for key, val in data.items():
        val_str = str(val)
        if _contains_forbidden_message(val_str):
            safe_data[key] = "[BLOCKED]"
        else:
            safe_data[key] = val_str

    if event_type == "runtime_status":
        scraper_status_map = {
            "EMPTY": "Nenhuma oportunidade encontrada neste ciclo.",
            "SKIPPED": "Não executado.",
        }
        scraper_status = scraper_status_map.get(safe_data.get('scraper', ''), safe_data.get('scraper', 'N/A'))

        ai_agent_status_map = {
            "OK": " OK.",
            "SKIPPED": "Não executado.",
        }
        ai_agent_status = ai_agent_status_map.get(safe_data.get('gemini', ''), safe_data.get('gemini', 'N/A'))

        resultado_map = {
            "UNRESOLVED": "Sem ação necessária.",
        }
        resultado = resultado_map.get(safe_data.get('label', ''), safe_data.get('label', 'N/A'))

        header_title = "Relatório"
        if data.get("is_heartbeat"):
            header_title = "Batimento Cardíaco (6h)"

        lines = [
            f"EdgeHunter v2.1.4 | {header_title}",
            "",
            "🏃 Status: Ativo",
            f"📡 Radar: {scraper_status}",
            f"🧠 Agente IA: {ai_agent_status}",
            f"✅ Resultado: {resultado}"
        ]
        return "\n".join(lines)

    if event_type == "signal_pending":
        lines = ["🟡 PENDENTE", ""]
        lines.append(f"Jogo: {safe_data.get('home', 'N/A')} x {safe_data.get('away', 'N/A')}")
        lines.append("Mercado: Resultado Final")
        lines.append(f"Hipótese: {safe_data.get('selection', 'N/A')}")
        lines.append(f"Assertividade: {safe_data.get('calibrated_assertiveness', 'N/A')}%")
        lines.append(f"Odd: {safe_data.get('offered_odds', 'N/A')}")
        lines.append(f"Fonte: {safe_data.get('source', 'N/A')}")
        lines.append(f"ID: {safe_data.get('signal_id', 'N/A')}")
        lines.append("")
        lines.append("Status: aguardando resultado final / paper trading")
        return "\n".join(lines)

    if event_type == "signal_resolved":
        label = safe_data.get("label", "")
        if label == "GREEN":
            title = "🟢 GREEN"
            status_line = "Status: hipótese confirmada / paper trading"
        elif label == "RED":
            title = "🔴 RED"
            status_line = "Status: hipótese não confirmada / paper trading"
        else:
            return ""

        lines = [title, ""]
        lines.append(f"Jogo: {safe_data.get('home', 'N/A')} x {safe_data.get('away', 'N/A')}")
        lines.append("Mercado: Resultado Final")
        lines.append(f"Hipótese: {safe_data.get('selection', 'N/A')}")
        lines.append(f"Resultado final: {safe_data.get('home_score', 'N/A')} x {safe_data.get('away_score', 'N/A')}")
        lines.append(f"Odd: {safe_data.get('offered_odds', 'N/A')}")
        lines.append(f"Assertividade inicial: {safe_data.get('calibrated_assertiveness', 'N/A')}%")
        lines.append(f"ID: {safe_data.get('signal_id', 'N/A')}")
        lines.append("")
        lines.append(status_line)
        return "\n".join(lines)

    allowed_events = {

        "signal_summary": "📈 Resumo Técnico",
        "daily_report": "📋 Relatório Diário",
        "error_alert": "⚠️ Alerta Técnico",
        "fallback_warning": "🔄 Aviso de Fallback",
        "scraper_status": "🔍 Status Scraper",
        "gemini_status": "🤖 Status Gemini",
    }

    header = allowed_events.get(event_type, f"📌 {event_type}")
    lines = [header]

    for key, val_str in safe_data.items():
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
    body = _json.dumps({"chat_id": chat_id, "text": text}).encode()

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


def notify_signal_pending(signal_data: dict, env: Optional[dict] = None, _mock_send: Optional[callable] = None) -> dict:
    """Notifica a captura de um sinal pendente no Telegram."""
    config = _load_telegram_config(env)
    if not config["enabled"]:
        return {**_SAFE_RESULT_TEMPLATE, "error": "telegram_disabled"}
    if not config["bot_token"]:
        return {**_SAFE_RESULT_TEMPLATE, "error": "missing_bot_token"}
    if not config["chat_id"]:
        return {**_SAFE_RESULT_TEMPLATE, "error": "missing_chat_id"}

    text = build_telegram_message("signal_pending", signal_data)
    return send_telegram_message(config["bot_token"], config["chat_id"], text, config, _mock_send=_mock_send)


def notify_signal_resolved(resolved_data: dict, env: Optional[dict] = None, _mock_send: Optional[callable] = None) -> dict:
    """Notifica a resolução final de um sinal (GREEN ou RED) no Telegram."""
    config = _load_telegram_config(env)
    if not config["enabled"]:
        return {**_SAFE_RESULT_TEMPLATE, "error": "telegram_disabled"}
    if not config["bot_token"]:
        return {**_SAFE_RESULT_TEMPLATE, "error": "missing_bot_token"}
    if not config["chat_id"]:
        return {**_SAFE_RESULT_TEMPLATE, "error": "missing_chat_id"}

    text = build_telegram_message("signal_resolved", resolved_data)
    if not text:
        return {**_SAFE_RESULT_TEMPLATE, "error": "empty_resolved_message"}
        
    return send_telegram_message(config["bot_token"], config["chat_id"], text, config, _mock_send=_mock_send)
