"""
EdgeHunter — Telegram Bot para Alertas de Value Bets
Envia alertas formatados com todos os detalhes da oportunidade detectada.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import requests as req_lib
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def format_flag(league: str) -> str:
    """Retorna emoji de bandeira por liga."""
    flags = {
        'Premier League': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
        'La Liga': '🇪🇸',
        'Bundesliga': '🇩🇪',
        'Serie A': '🇮🇹',
        'Ligue 1': '🇫🇷',
        'Champions League': '🏆',
        'Brasileirão': '🇧🇷',
        'Primeira Liga': '🇵🇹',
        'Eredivisie': '🇳🇱'
    }
    return flags.get(league, '⚽')


def format_selection(selection: str) -> str:
    """Formata a seleção de forma legível."""
    return {'home': '1 (Casa)', 'draw': 'X (Empate)', 'away': '2 (Fora)'}.get(selection, selection)


def format_confidence_bar(confidence: float) -> str:
    """Barra visual de confiança."""
    filled = int(confidence / 10)
    return '█' * filled + '░' * (10 - filled)

# CORREÇÃO 3 — Deep links para as casas
DEEPLINKS = {
    'bet365':  'https://www.bet365.com/#/AS/B1/',
    'betano':  'https://www.betano.com/sport/futebol/',
    'betfair': 'https://www.betfair.com/exchange/plus/football',
    'pinnacle': 'https://www.pinnacle.com/pt/football/matchups'
}

class TelegramBot:
    """
    Bot Telegram para envio de alertas do EdgeHunter.
    Usa a API REST do Telegram diretamente (sem biblioteca extra).
    """
    
    TELEGRAM_API = 'https://api.telegram.org/bot'
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"{self.TELEGRAM_API}{token}"
    
    def _send(self, text: str, parse_mode: str = 'HTML', disable_notification: bool = False) -> bool:
        """Envia mensagem via API REST."""
        if not self.token or not self.chat_id:
            logger.warning("Telegram não configurado. Pulando envio.")
            return False
        
        try:
            response = req_lib.post(
                f"{self.base_url}/sendMessage",
                json={
                    'chat_id': self.chat_id,
                    'text': text,
                    'parse_mode': parse_mode,
                    'disable_notification': disable_notification,
                    'disable_web_page_preview': True
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Telegram error {response.status_code}: {response.text[:200]}")
        
        except Exception as e:
            logger.error(f"Erro ao enviar Telegram: {e}")
        
        return False
    
    def send_value_alert(self, opportunity: Dict, game_info: Dict, ai_result: Optional[Dict] = None) -> bool:
        """Envia alerta de value bet formatado."""
        league = game_info.get('league', 'Desconhecida')
        match_date = game_info.get('match_date', '')
        
        flag = format_flag(league)
        selection = format_selection(opportunity['selection'])
        confidence = opportunity.get('confidence', 0)
        edge = opportunity['edge_pct']
        
        # Determinar ícone de urgência
        if edge >= 8:
            urgency = '🔥🔥🔥'
        elif edge >= 5:
            urgency = '🔥🔥'
        else:
            urgency = '🔥'
        
        # Verificar se tem edge vs Pinnacle
        pinnacle_badge = '✅ Confirmado vs Pinnacle' if opportunity.get('has_edge_vs_pinnacle') else '⚠️ Sem referência Pinnacle'
        
        # Bloco Motor IA (se disponivel)
        ai = ai_result or opportunity.get('ai_result')
        if ai and ai.get('decision') == 'GO':
            ai_confidence = ai.get('confidence', 0)
            ai_reasoning = ai.get('reasoning', '')
            provider = ai.get('provider', 'IA').upper()
            ai_block = (
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 <b>{provider}:</b> ✅ GO ({ai_confidence}%)\n"
                f"💬 <i>{ai_reasoning[:120]}</i>\n"
            )
        else:
            ai_block = ""

        message = f"""
{urgency} <b>VALUE BET DETECTADO</b> {urgency}

{flag} <b>{league}</b>
🏟️ <b>{opportunity['home_team']} vs {opportunity['away_team']}</b>
📅 {match_date[:16].replace('T', ' ')} UTC

━━━━━━━━━━━━━━━━━━━━━
📊 <b>SELEÇÃO:</b> {selection}
🏪 <b>Casa:</b> <code>{opportunity['bookmaker'].title()}</code>
💰 <b>Odd:</b> <code>{opportunity['odd']:.2f}</code>
━━━━━━━━━━━━━━━━━━━━━
🎯 <b>EDGE:</b> <code>+{edge:.1f}%</code>
📈 <b>Nossa Prob:</b> <code>{opportunity['our_prob']*100:.1f}%</code>
📉 <b>Prob Implícita:</b> <code>{opportunity['implied_prob']*100:.1f}%</code>
{f"📌 <b>Pinnacle Fair:</b> <code>{opportunity['pinnacle_fair_prob']*100:.1f}%</code>" if opportunity.get('pinnacle_fair_prob') else ''}
━━━━━━━━━━━━━━━━━━━━━
🧠 <b>Confiança:</b> {format_confidence_bar(confidence)} {confidence:.0f}/100
{pinnacle_badge}
🎲 <b>Kelly (25%):</b> <code>{opportunity['kelly_fraction']*100:.2f}%</code> do bankroll
{ai_block}━━━━━━━━━━━━━━━━━━━━━
<i>📝 Paper Trading — Não arrisque dinheiro real ainda</i>
<i>🤖 EdgeHunter v1.0 | {datetime.utcnow().strftime('%H:%M UTC')}</i>
"""
        
        return self._send(message.strip())
    
    def send_daily_summary(self, stats: Dict) -> bool:
        """Envia resumo diário de performance."""
        roi = stats.get('roi', 0)
        roi_icon = '📈' if roi > 0 else '📉'
        
        message = f"""
📊 <b>RESUMO DIÁRIO — EdgeHunter</b>
📅 {datetime.utcnow().strftime('%d/%m/%Y')}

━━━━━━━━━━━━━━━━━━━━━
🎯 <b>Apostas Hoje:</b> {stats.get('bets_today', 0)}
✅ <b>Ganhas:</b> {stats.get('wins', 0)}
❌ <b>Perdidas:</b> {stats.get('losses', 0)}
⏳ <b>Pendentes:</b> {stats.get('pending', 0)}
━━━━━━━━━━━━━━━━━━━━━
{roi_icon} <b>ROI Hoje:</b> <code>{roi:+.2f}%</code>
💼 <b>ROI 30d:</b> <code>{stats.get('roi_30d', 0):+.2f}%</code>
📊 <b>Sharpe 30d:</b> <code>{stats.get('sharpe', 0):.2f}</code>
🎯 <b>CLV Médio:</b> <code>{stats.get('clv_avg', 0):+.2f}%</code>
━━━━━━━━━━━━━━━━━━━━━
<i>🤖 EdgeHunter | Paper Trading</i>
"""
        return self._send(message.strip())
    
    def send_drift_alert(self, drift_info: Dict) -> bool:
        """Alerta de concept drift detectado."""
        message = f"""
🚨 <b>CONCEPT DRIFT DETECTADO</b>

O modelo identificou mudança estrutural no mercado.

📊 <b>Brier Score Recente:</b> <code>{drift_info.get('recent_brier', 'N/A'):.4f}</code>
📊 <b>Baseline:</b> <code>{drift_info.get('baseline_brier', 'N/A'):.4f}</code>
⚠️ <b>Delta:</b> <code>+{drift_info.get('delta', 0):.4f}</code>

🔄 Iniciando retraining automático...

<i>🤖 EdgeHunter | Sistema de Auto-Aperfeiçoamento</i>
"""
        return self._send(message.strip())
    
    def send_model_promoted(self, new_version: str, metrics: Dict) -> bool:
        """Notifica promoção de novo modelo após A/B test."""
        message = f"""
🎉 <b>NOVO MODELO PROMOVIDO</b>

Após {metrics.get('ab_bets', 0)} apostas de A/B test,
o modelo <b>{new_version}</b> superou o campeão anterior.

📊 <b>Brier Score:</b> <code>{metrics.get('brier', 0):.4f}</code>
💼 <b>ROI:</b> <code>{metrics.get('roi', 0):+.2f}%</code>
📈 <b>Sharpe:</b> <code>{metrics.get('sharpe', 0):.2f}</code>
🎯 <b>CLV Médio:</b> <code>{metrics.get('clv', 0):+.2f}%</code>

✅ Modelo ativo atualizado.

<i>🤖 EdgeHunter | Auto-Aperfeiçoamento</i>
"""
        return self._send(message.strip())
    
    def test_connection(self) -> bool:
        """Testa a conexão com o Telegram."""
        return self._send("🤖 EdgeHunter conectado com sucesso! Sistema de value betting ativo.")


def send_message(text: str, parse_mode: str = 'HTML'):
    """Função auxiliar para enviar mensagens rápidas via Telegram."""
    from flask import current_app
    token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    chat_id = current_app.config.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        return False
    
    bot = TelegramBot(token, chat_id)
    return bot._send(text, parse_mode=parse_mode)


def send_heartbeat(scheduler_jobs: list, ai_active: bool, surebets_today: int,
                   req_used: int = 0):
    """Envia status do sistema a cada 2 horas."""
    from datetime import datetime
    now = datetime.utcnow().strftime('%d/%m %H:%M')

    status_ai = "✅" if ai_active else "❌"

    msg = (
        f"🔒 <b>EdgeHunter — Heartbeat</b>\n"
        f"🕐 {now} UTC\n\n"
        f"{status_ai} IA híbrida (Gemini + Groq)\n"
        f"⚙️ Scheduler: {len(scheduler_jobs)} jobs rodando\n"
        f"🔍 Fonte: OddsPortal Scraper\n"
        f"🏦 Casas: Pinnacle | Betfair | Bet365 | Betano\n"
        f"🎯 Surebets hoje: <b>{surebets_today}</b>\n\n"
        f"<i>Sistema operacional</i> 🟢"
    )
    send_message(msg)


def send_surebet_alert(opp: dict):
    """Envia alerta de arbitragem (surebet) formatado."""
    from datetime import datetime, timedelta
    detected_at = datetime.utcnow()
    expires_at = detected_at + timedelta(seconds=90)

    # CORREÇÃO 3 — Obter deep links
    link_A = DEEPLINKS.get(opp['bookmaker_A'].lower(), '#')
    link_B = DEEPLINKS.get(opp['bookmaker_B'].lower(), '#')

    msg = (
        f"🔒 <b>SUREBET — LUCRO GARANTIDO</b>\n"
        f"⏰ <b>EXECUTE EM ATÉ 90 SEGUNDOS</b>\n"
        f"🕐 Detectado: {detected_at.strftime('%H:%M:%S')} UTC\n"
        f"⚠️ Expira: {expires_at.strftime('%H:%M:%S')} UTC\n\n"
        f"🏟 <code>{opp['home_team']}</code> vs <code>{opp['away_team']}</code>\n"
        f"🏆 {opp['league']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"APOSTA 1️⃣\n"
        f"🏦 <b>{opp['bookmaker_A'].upper()}</b>\n"
        f"📌 {opp['outcome_A'].upper()}\n"
        f"💰 Odd: <code>{opp['odds_A_raw'] if 'odds_A_raw' in opp else opp['odds_A']}</code>\n"
        f"💵 Stake: <b>R$ {opp['stake_A']}</b>\n"
        f"🔗 <a href='{link_A}'>Abrir {opp['bookmaker_A'].upper()}</a>\n\n"
        f"APOSTA 2️⃣\n"
        f"🏦 <b>{opp['bookmaker_B'].upper()}</b>\n"
        f"📌 {opp['outcome_B'].upper()}\n"
        f"💰 Odd: <code>{opp['odds_B_raw'] if 'odds_B_raw' in opp else opp['odds_B']}</code>\n"
        f"💵 Stake: <b>R$ {opp['stake_B']}</b>\n"
        f"🔗 <a href='{link_B}'>Abrir {opp['bookmaker_B'].upper()}</a>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 Stake total: <code>R$ {opp['total_stake']}</code>\n"
        f"✅ Lucro líquido: <b>R$ {opp['guaranteed_profit']}</b>\n"
        f"📈 ROI Real: <code>{opp['profit_pct']}%</code>\n"
        f"🔒 <b>LUCRO INDEPENDENTE DO RESULTADO</b>"
    )
    send_message(msg)
