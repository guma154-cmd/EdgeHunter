"""
Módulo para orquestrar notificações Telegram de sinais PENDENTES e RESOLVIDOS.
Garante que não sejam enviadas mensagens duplicadas.
Não executa ação financeira.
"""
import logging
from typing import Optional

from src.edgehunter.integrations.telegram_notifier import (
    notify_signal_pending,
    notify_signal_resolved,
)

logger = logging.getLogger(__name__)


def resolve_signal_result(selection: str, home_score: Optional[int], away_score: Optional[int]) -> Optional[str]:
    """
    Compara a hipótese (selection) com o placar final.
    Retorna "GREEN", "RED" ou None se o placar estiver incompleto.
    """
    if home_score is None or away_score is None:
        return None
        
    try:
        home_score = int(home_score)
        away_score = int(away_score)
    except ValueError:
        return None

    sel = selection.lower().strip()
    
    # Mandante vence
    if "mandante" in sel or "home" in sel:
        return "GREEN" if home_score > away_score else "RED"
        
    # Visitante vence
    if "visitante" in sel or "away" in sel:
        return "GREEN" if away_score > home_score else "RED"
        
    # Empate
    if "empate" in sel or "draw" in sel:
        return "GREEN" if home_score == away_score else "RED"
        
    # Fallback caso não identifique (nunca deveria ocorrer em prod limpo)
    return None


def process_and_notify_signals(
    pending_signals: list[dict],
    resolved_outcomes: list[dict],
    notified_set: set[str],
    env: dict,
    _mock_send: Optional[callable] = None,
) -> None:
    """
    Processa sinais recentes (Gemini) e resultados recentes (Outcomes).
    Notifica via Telegram se ainda não notificado no ciclo atual/memória.
    
    - pending_signals: lista de dicts com chaves do signal (home, away, selection...)
    - resolved_outcomes: lista de dicts com o resultado final (home_score, away_score, original_signal...)
    """
    
    # 1. Enviar PENDENTE para novos sinais
    for sig in pending_signals:
        sig_id = sig.get("signal_id")
        if not sig_id:
            continue
            
        pending_key = f"{sig_id}_PENDING"
        if pending_key not in notified_set:
            try:
                res = notify_signal_pending(sig, env=env, _mock_send=_mock_send)
                if res.get("sent"):
                    notified_set.add(pending_key)
            except Exception as e:
                logger.warning(f"Failed to send PENDING notification for {sig_id}: {e}")

    # 2. Enviar GREEN/RED para resultados resolvidos
    for out in resolved_outcomes:
        sig_id = out.get("signal_id")
        if not sig_id:
            continue
            
        resolved_key = f"{sig_id}_RESOLVED"
        if resolved_key in notified_set:
            continue
            
        # Tenta resolver o GREEN/RED baseado no placar
        selection = out.get("selection", "")
        h_score = out.get("home_score")
        a_score = out.get("away_score")
        
        label = resolve_signal_result(selection, h_score, a_score)
        if not label:
            logger.debug(f"Signal {sig_id} unresolved (incomplete result or unknown selection).")
            continue
            
        out_data = dict(out)
        out_data["label"] = label
        
        try:
            res = notify_signal_resolved(out_data, env=env, _mock_send=_mock_send)
            if res.get("sent"):
                notified_set.add(resolved_key)
        except Exception as e:
            logger.warning(f"Failed to send RESOLVED notification for {sig_id}: {e}")
