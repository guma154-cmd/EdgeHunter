"""
Gemini client controlado.

Habilitado apenas via GEMINI_ENABLED=true no .env.
Por padrão usa cliente offline/fake sem chamadas de rede.
"""
import os
from typing import Optional

# Linguagem proibida que jamais deve constar em resposta retornada
_FORBIDDEN_TERMS = [
    "aposta", "apostar", "entrada", "sinal de aposta",
    "recomendação operacional", "lucro", "gain", "stake",
    "kelly", "bankroll", "wager", "bet_amount", "execute",
    "execution", "place_bet", "autoevolution",
]

_SAFE_RESULT_TEMPLATE = {
    "valid": False,
    "raw_response": None,
    "parsed": None,
    "provider": "gemini",
    "model": None,
    "tokens_used": None,
    "is_simulated": True,
    "actionable": False,
    "not_operational_advice": True,
    "fallback_reason": None,
}


def _load_gemini_config(env: Optional[dict] = None) -> dict:
    e = env or {}
    return {
        "enabled": (e.get("GEMINI_ENABLED") or os.environ.get("GEMINI_ENABLED", "false")).lower() == "true",
        "api_key": e.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", ""),
        "model": e.get("GEMINI_MODEL") or os.environ.get("GEMINI_MODEL", "gemini-1.5-flash"),
        "timeout": int(e.get("GEMINI_TIMEOUT_SECONDS") or os.environ.get("GEMINI_TIMEOUT_SECONDS", "5")),
        "max_tokens": int(e.get("GEMINI_MAX_TOKENS") or os.environ.get("GEMINI_MAX_TOKENS", "1024")),
    }


def _contains_forbidden(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in _FORBIDDEN_TERMS)


def _fake_gemini_validate(prompt: str, config: dict) -> dict:
    """Fallback offline — não faz chamada de rede."""
    result = dict(_SAFE_RESULT_TEMPLATE)
    result["model"] = config["model"]
    result["fallback_reason"] = "gemini_disabled"
    result["parsed"] = {"label": "UNRESOLVED", "confidence": 0.0}
    result["valid"] = True  # estrutura válida, dado offline
    return result


def _real_gemini_validate(prompt: str, config: dict) -> dict:
    """
    Chama Gemini real. Requer GEMINI_ENABLED=true e GEMINI_API_KEY configurado.
    Nunca retorna payload acionável.
    """
    import urllib.request
    import json as _json

    result = dict(_SAFE_RESULT_TEMPLATE)
    result["model"] = config["model"]

    url = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}".format(
        model=config["model"], key=config["api_key"]
    )
    body = _json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": config["max_tokens"]},
    }).encode()

    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=config["timeout"]) as resp:
            data = _json.loads(resp.read().decode())

        raw_text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        tokens_used = data.get("usageMetadata", {}).get("totalTokenCount", None)

        if _contains_forbidden(raw_text):
            result["fallback_reason"] = "forbidden_content_in_response"
            result["parsed"] = {"label": "INVALIDATED", "confidence": 0.0}
            result["valid"] = False
            return result

        # Reutiliza parser seguro existente
        from src.edgehunter.core.gemini_validator import parse_gemini_validation_response
        parsed = parse_gemini_validation_response(raw_text)

        result["raw_response"] = raw_text
        result["parsed"] = parsed
        result["tokens_used"] = tokens_used
        result["valid"] = True

    except TimeoutError:
        result["fallback_reason"] = "timeout"
        result["parsed"] = {"label": "UNRESOLVED", "confidence": 0.0}
    except Exception as e:
        result["fallback_reason"] = f"error:{type(e).__name__}"
        result["parsed"] = {"label": "UNRESOLVED", "confidence": 0.0}

    return result


def validate_with_gemini(prompt: str, env: Optional[dict] = None) -> dict:
    """
    Ponto de entrada principal.

    Se GEMINI_ENABLED=false → usa fallback offline.
    Se GEMINI_ENABLED=true e API_KEY ausente → falha controlada.
    """
    config = _load_gemini_config(env)

    if not config["enabled"]:
        return _fake_gemini_validate(prompt, config)

    if not config["api_key"]:
        result = dict(_SAFE_RESULT_TEMPLATE)
        result["model"] = config["model"]
        result["fallback_reason"] = "missing_api_key"
        result["parsed"] = {"label": "UNRESOLVED", "confidence": 0.0}
        return result

    return _real_gemini_validate(prompt, config)
