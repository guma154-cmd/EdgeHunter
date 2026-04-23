"""
EdgeHunter — Motor de IA Híbrido (Gemini 2.5 Flash + Groq Llama 3.3 70B)
Árbitro final de qualidade para cada value bet detectado pelo ensemble.
Fallback automático: Gemini → Groq → modo degradado (ensemble decide sozinho)
"""
import logging
import json
import requests
import time
from typing import Optional

logger = logging.getLogger(__name__)


# ── Prompt do sistema ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Você é um analista quantitativo sênior especializado em value betting esportivo.

Seu trabalho é avaliar oportunidades de apostas detectadas por um modelo ensemble estatístico
(Dixon-Coles Poisson + Elo + XGBoost + Bayesian) e decidir se a aposta tem qualidade suficiente.

Você recebe:
- Probabilidades do modelo vs probabilidade implícita da odd
- Edge calculado (vantagem matemática sobre a casa)
- Odds da Pinnacle (sharp line) e casa soft (onde apostaremos)
- Contexto do jogo

Critérios de decisão:
1. Edge > 8% com alinhamento Pinnacle → GO quase certo
2. Edge 3-5% exige contexto favorável adicional
3. Odds > 6.0 → rejeitar (variância extrema)
4. Divergência > 10% entre modelo e Pinnacle → suspeito
5. Em caso de dúvida → NO-GO (conservador)

RESPONDA SEMPRE em JSON puro, sem texto fora do JSON, sem markdown:
{
  "decision": "GO" ou "NO-GO",
  "confidence": 0-100,
  "reasoning": "máximo 2 frases objetivas em português",
  "risk_flags": ["lista de alertas se houver, senão []"]
}"""


def _build_prompt(
    home_team: str, away_team: str, league: str, selection: str,
    odds: float, bookmaker: str, our_prob: float, implied_prob: float,
    edge_pct: float, pinnacle_prob: Optional[float], model_weights: dict,
    match_date: str
) -> str:
    sel_map = {
        "home": f"Vitória {home_team}",
        "draw": "Empate",
        "away": f"Vitória {away_team}"
    }
    sel_label = sel_map.get(selection, selection)

    pin_line = ""
    if pinnacle_prob:
        diff = our_prob - pinnacle_prob
        status = "alinhado" if abs(diff) < 0.05 else "DIVERGENTE"
        pin_line = f"\n- Modelo vs Pinnacle: {diff:+.1%} ({status})"

    return f"""OPORTUNIDADE DE VALUE BET

Jogo: {home_team} vs {away_team}
Liga: {league} | Data: {match_date}

APOSTA: {sel_label} @ {odds:.2f} ({bookmaker})
- Odd implica: {implied_prob:.1%}
- Nossa prob: {our_prob:.1%}
- Edge: +{edge_pct:.1f}%{pin_line}
- Pinnacle: {f'{pinnacle_prob:.1%}' if pinnacle_prob else 'indisponível'}

Pesos ensemble: DC={model_weights.get('dixon_coles', 0):.0%} \
Elo={model_weights.get('elo', 0):.0%} \
XGB={model_weights.get('xgboost', 0):.0%} \
Bay={model_weights.get('bayesian', 0):.0%}

Decisão: GO ou NO-GO?"""


# ── Cliente Gemini ────────────────────────────────────────────────────────────
class GeminiClient:
    MODEL = "gemini-2.5-flash"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.calls = 0
        self.errors = 0

    def generate(self, prompt: str) -> Optional[str]:
        url = f"{self.BASE_URL}/{self.MODEL}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 300,
                "responseMimeType": "application/json"
            }
        }
        try:
            r = requests.post(url, json=payload, timeout=15)
            r.raise_for_status()
            self.calls += 1
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except requests.exceptions.HTTPError as e:
            if r.status_code == 429:
                logger.warning("[Gemini] Rate limit atingido → fallback Groq")
            else:
                logger.error(f"[Gemini] HTTP {r.status_code}: {e}")
            self.errors += 1
            return None
        except Exception as e:
            logger.error(f"[Gemini] Erro: {e}")
            self.errors += 1
            return None


# ── Cliente Groq ──────────────────────────────────────────────────────────────
class GroqClient:
    MODEL = "llama-3.3-70b-versatile"
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.calls = 0
        self.errors = 0

    def generate(self, prompt: str) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 300,
            "response_format": {"type": "json_object"}
        }
        try:
            r = requests.post(self.BASE_URL, headers=headers,
                              json=payload, timeout=10)
            r.raise_for_status()
            self.calls += 1
            return r.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            if r.status_code == 429:
                logger.warning("[Groq] Rate limit atingido → modo degradado")
            else:
                logger.error(f"[Groq] HTTP {r.status_code}: {e}")
            self.errors += 1
            return None
        except Exception as e:
            logger.error(f"[Groq] Erro: {e}")
            self.errors += 1
            return None


# ── Motor híbrido principal ───────────────────────────────────────────────────
class HybridAIEngine:
    """
    Motor híbrido Gemini 2.5 Flash → Groq Llama 3.3 70B → modo degradado.
    Árbitro final de qualidade para value bets do ensemble.
    """

    def __init__(self, gemini_key: str, groq_key: str):
        self.gemini = GeminiClient(gemini_key)
        self.groq   = GroqClient(groq_key)
        self.go_count   = 0
        self.nogo_count = 0
        self.degraded   = 0   # decisões sem IA (ambos falharam)
        logger.info("🤖 HybridAIEngine inicializado: Gemini 2.5 Flash + Groq Llama 3.3 70B")

    def analyze(
        self,
        home_team: str,
        away_team: str,
        league: str,
        selection: str,
        odds: float,
        bookmaker: str,
        our_prob: float,
        implied_prob: float,
        edge_pct: float,
        pinnacle_prob: Optional[float] = None,
        model_weights: dict = None,
        match_date: str = ""
    ) -> dict:
        """
        Analisa value bet via Gemini → Groq → degradado.
        Retorna dict com decision, confidence, reasoning, risk_flags, provider.
        """
        model_weights = model_weights or {}
        prompt = _build_prompt(
            home_team, away_team, league, selection, odds, bookmaker,
            our_prob, implied_prob, edge_pct, pinnacle_prob,
            model_weights, match_date
        )

        # 1. Tentar Gemini
        raw = self.gemini.generate(prompt)
        provider = "gemini"

        # 2. Fallback Groq
        if raw is None:
            raw = self.groq.generate(prompt)
            provider = "groq"

        # 3. Parse do JSON
        if raw:
            result = self._parse(raw, provider)
        else:
            # Modo degradado — ensemble decide sozinho com regra simples
            result = self._degraded_decision(edge_pct, odds, pinnacle_prob, our_prob)
            provider = "degraded"

        result["provider"] = provider

        # Log e contadores
        sel_map = {"home": f"V.{home_team}", "draw": "Empate", "away": f"V.{away_team}"}
        if result["decision"] == "GO":
            self.go_count += 1
            logger.info(
                f"[IA:{provider}] ✅ GO — {home_team} vs {away_team} | "
                f"{sel_map.get(selection, selection)} @ {odds:.2f} | "
                f"conf={result['confidence']}% | {result['reasoning']}"
            )
        else:
            self.nogo_count += 1
            logger.info(
                f"[IA:{provider}] ❌ NO-GO — {home_team} vs {away_team} | "
                f"{result['reasoning']}"
            )

        return result

    def _parse(self, raw: str, provider: str) -> dict:
        """Parse JSON da resposta com fallback conservador."""
        try:
            # Limpar possíveis backticks
            clean = raw.strip()
            if "```" in clean:
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            result = json.loads(clean)
            # Validar campos obrigatórios
            assert "decision" in result
            assert result["decision"] in ("GO", "NO-GO")
            result.setdefault("confidence", 50)
            result.setdefault("reasoning", "")
            result.setdefault("risk_flags", [])
            return result
        except Exception as e:
            logger.error(f"[IA:{provider}] Parse falhou: {e} | raw={raw[:150]}")
            return {
                "decision": "NO-GO",
                "confidence": 0,
                "reasoning": "Erro ao interpretar resposta da IA — descartado.",
                "risk_flags": ["parse_error"]
            }

    def _degraded_decision(
        self, edge_pct: float, odds: float,
        pinnacle_prob: Optional[float], our_prob: float
    ) -> dict:
        """
        Regra determinística quando ambas as APIs falham.
        Conservadora: só aprova edge alto com odds razoáveis.
        """
        self.degraded += 1
        flags = ["degraded_mode"]

        if odds > 6.0:
            return {"decision": "NO-GO", "confidence": 90,
                    "reasoning": "Odds extrema (>6.0) — rejeitado em modo degradado.",
                    "risk_flags": flags + ["high_odds"]}

        if pinnacle_prob and abs(our_prob - pinnacle_prob) > 0.10:
            return {"decision": "NO-GO", "confidence": 80,
                    "reasoning": "Divergência alta vs Pinnacle — rejeitado em modo degradado.",
                    "risk_flags": flags + ["pinnacle_divergence"]}

        if edge_pct >= 6.0:
            return {"decision": "GO", "confidence": 60,
                    "reasoning": f"Edge {edge_pct:.1f}% aprovado por regra (APIs indisponíveis).",
                    "risk_flags": flags}

        return {"decision": "NO-GO", "confidence": 70,
                "reasoning": "Edge insuficiente para aprovação em modo degradado.",
                "risk_flags": flags}

    def get_stats(self) -> dict:
        total = self.go_count + self.nogo_count
        return {
            "total_decisions": total,
            "go": self.go_count,
            "no_go": self.nogo_count,
            "degraded": self.degraded,
            "approval_rate": round(self.go_count / max(total, 1), 4),
            "gemini_calls": self.gemini.calls,
            "gemini_errors": self.gemini.errors,
            "groq_calls": self.groq.calls,
            "groq_errors": self.groq.errors
        }


# ── Singleton global ──────────────────────────────────────────────────────────
_engine: Optional[HybridAIEngine] = None


def init_ai_engine(gemini_key: str, groq_key: str) -> HybridAIEngine:
    global _engine
    _engine = HybridAIEngine(gemini_key, groq_key)
    return _engine


def get_ai_engine() -> Optional[HybridAIEngine]:
    return _engine