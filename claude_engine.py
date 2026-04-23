"""
EdgeHunter — Motor de IA (Claude API)
Filtro determinístico que analisa cada value bet detectado pelo ensemble
antes de registrar a aposta. Claude age como árbitro final de qualidade.
"""
import anthropic
import logging
import json
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class ClaudeEngine:
    """
    Motor de decisão baseado em Claude API.

    Fluxo:
    1. Ensemble detecta edge > threshold
    2. ClaudeEngine recebe o contexto completo
    3. Claude analisa e decide GO / NO-GO
    4. Apenas apostas aprovadas são registradas
    """

    MODEL = "claude-opus-4-6"
    MAX_TOKENS = 500

    SYSTEM_PROMPT = """Você é um analista quantitativo sênior especializado em value betting esportivo.

Seu trabalho é avaliar oportunidades de apostas detectadas por um modelo estatístico ensemble
(Dixon-Coles Poisson + Elo + XGBoost + Bayesian) e decidir se a aposta tem qualidade suficiente.

Você recebe:
- Probabilidades do modelo vs probabilidade implícita da odd
- Edge calculado (vantagem matemática)
- Contexto do jogo (times, liga, importância)
- Odds da Pinnacle (referência sharp) e casa soft (onde apostaremos)

Sua decisão deve considerar:
1. Edge real vs edge mínimo aceitável (3%)
2. Coerência entre modelo e Pinnacle (se divergem muito, suspeite)
3. Qualidade da odd (evitar odds muito extremas > 5.0)
4. Liga e nível de competição (dados mais confiáveis em ligas top)
5. Contexto óbvio que o modelo não captura

REGRAS:
- Responda SEMPRE em JSON válido, sem texto fora do JSON
- Seja conservador: em caso de dúvida, NO-GO
- Edge > 8% com confirmação Pinnacle = GO quase certo
- Edge 3-5% exige contexto favorável adicional
- Nunca aprove odds > 6.0 (variância extrema)

Formato obrigatório:
{
  "decision": "GO" ou "NO-GO",
  "confidence": 0-100,
  "reasoning": "máximo 2 frases objetivas",
  "risk_flags": ["lista de alertas, se houver"]
}"""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.decisions_today = 0
        self.go_count = 0
        self.nogo_count = 0

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
        pinnacle_prob: Optional[float],
        model_weights: dict,
        match_date: str,
        additional_context: str = ""
    ) -> dict:
        """
        Analisa uma oportunidade de value bet.

        Returns:
            {
                'decision': 'GO' | 'NO-GO',
                'confidence': int,
                'reasoning': str,
                'risk_flags': list,
                'raw_response': str
            }
        """

        # Mapear selection para português
        sel_map = {"home": f"Vitória {home_team}", "draw": "Empate", "away": f"Vitória {away_team}"}
        sel_label = sel_map.get(selection, selection)

        # Calcular divergência vs Pinnacle
        pin_divergence = ""
        if pinnacle_prob:
            diff = our_prob - pinnacle_prob
            pin_divergence = f"\n- Nossa prob vs Pinnacle: {diff:+.1%} ({'alinhado' if abs(diff) < 0.05 else 'DIVERGENTE'})"

        # Construir prompt
        user_prompt = f"""OPORTUNIDADE DE VALUE BET — Análise requerida

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JOGO: {home_team} vs {away_team}
Liga: {league}
Data: {match_date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

APOSTA PROPOSTA:
- Seleção: {sel_label}
- Odd disponível: {odds:.2f} ({bookmaker})
- Odd implica probabilidade: {implied_prob:.1%}

ANÁLISE DO MODELO:
- Nossa probabilidade: {our_prob:.1%}
- Edge calculado: +{edge_pct:.1f}%{pin_divergence}
- Pinnacle (sharp): {f'{pinnacle_prob:.1%}' if pinnacle_prob else 'não disponível'}

PESOS DO ENSEMBLE ATUAL:
{json.dumps(model_weights, indent=2)}

{f'CONTEXTO ADICIONAL:{chr(10)}{additional_context}' if additional_context else ''}

Decida: esta aposta deve ser registrada (GO) ou descartada (NO-GO)?"""

        try:
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            raw = response.content[0].text.strip()

            # Parse JSON
            # Remove possíveis backticks
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            result = json.loads(raw)
            result["raw_response"] = raw

            # Atualizar contadores
            self.decisions_today += 1
            if result.get("decision") == "GO":
                self.go_count += 1
                logger.info(
                    f"[Claude] ✅ GO — {home_team} vs {away_team} | {sel_label} @ {odds:.2f} | "
                    f"confiança={result.get('confidence')}% | {result.get('reasoning', '')}"
                )
            else:
                self.nogo_count += 1
                logger.info(
                    f"[Claude] ❌ NO-GO — {home_team} vs {away_team} | {sel_label} | "
                    f"motivo={result.get('reasoning', '')}"
                )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"[Claude] Erro ao parsear JSON: {e} | Raw: {raw[:200]}")
            # Fallback conservador
            return {
                "decision": "NO-GO",
                "confidence": 0,
                "reasoning": "Erro ao parsear resposta da IA — descartado por segurança.",
                "risk_flags": ["parse_error"],
                "raw_response": raw if 'raw' in dir() else ""
            }
        except Exception as e:
            logger.error(f"[Claude] Erro na API: {e}")
            return {
                "decision": "NO-GO",
                "confidence": 0,
                "reasoning": f"Erro na API Claude: {str(e)[:100]}",
                "risk_flags": ["api_error"],
                "raw_response": ""
            }

    def get_stats(self) -> dict:
        """Estatísticas de decisões do motor."""
        total = self.go_count + self.nogo_count
        return {
            "total_decisions": total,
            "go": self.go_count,
            "no_go": self.nogo_count,
            "approval_rate": round(self.go_count / max(total, 1), 4),
            "decisions_today": self.decisions_today
        }


# ── Singleton global ──────────────────────────────────────────────────────────
_claude_engine: Optional[ClaudeEngine] = None


def init_claude_engine(api_key: str) -> ClaudeEngine:
    global _claude_engine
    _claude_engine = ClaudeEngine(api_key)
    logger.info("🤖 Claude Engine inicializado — motor de IA ativo.")
    return _claude_engine


def get_claude_engine() -> Optional[ClaudeEngine]:
    return _claude_engine
