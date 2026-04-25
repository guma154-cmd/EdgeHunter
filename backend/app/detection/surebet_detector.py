import logging
import math
import os

logger = logging.getLogger(__name__)

class SurebetDetector:
    """
    Detecta oportunidades de arbitragem entre casas.
    Suporta mercados de 2 vias (Home/Away) e 3 vias (1X2).
    """

    def __init__(self, min_profit_pct: float = None, 
                 max_profit_pct: float = None,
                 stake_pct: float = 0.25,
                 bankroll_per_book: float = 20.0,
                 min_stake: float = 5.0,
                 betfair_commission: float = 0.05):
        # Usar .env se não for passado explicitamente
        self.min_profit_pct = min_profit_pct or float(os.getenv('MIN_SUREBET_PROFIT', '0.3'))
        self.max_profit_pct = max_profit_pct or float(os.getenv('MAX_SUREBET_ROI', '15.0'))
        
        self.stake_pct = stake_pct
        self.bankroll_per_book = bankroll_per_book
        self.min_stake = min_stake
        self.betfair_commission = betfair_commission
        
        logger.info(f"Detector inicializado: Min={self.min_profit_pct}%, Max={self.max_profit_pct}%")

    def detect(self, game_data: dict) -> list:
        """
        Analisa um jogo e retorna oportunidades de surebet.
        """
        opportunities = []
        home = game_data.get('home_team', 'Unknown')
        away = game_data.get('away_team', 'Unknown')
        
        all_odds = game_data.get('all_odds', {})
        bookmakers = list(all_odds.keys())

        if len(bookmakers) < 2:
            return []

        logger.debug(f"Analisando: {home} vs {away} | Casas: {bookmakers}")

        # 1. DETECÇÃO 2-WAY (Home/Away ou Over/Under se disponível)
        # (Lógica simplificada para Home/Away)
        for i, book_A in enumerate(bookmakers):
            for book_B in bookmakers:
                if book_A == book_B: continue
                
                odds_A = all_odds[book_A]
                odds_B = all_odds[book_B]
                
                # Mapear chaves (podem vir como '1', '2' ou 'home', 'away')
                oa = odds_A.get('1') or odds_A.get('home')
                ob = odds_B.get('2') or odds_B.get('away')
                
                if not oa or not ob: continue
                
                # Ajuste Betfair
                eff_oa = 1 + (oa - 1) * (1 - self.betfair_commission) if book_A == 'betfair' else oa
                eff_ob = 1 + (ob - 1) * (1 - self.betfair_commission) if book_B == 'betfair' else ob
                
                arb = (1/eff_oa) + (1/eff_ob)
                if arb < 1.0:
                    self._process_opp(opportunities, game_data, [book_A, book_B], [eff_oa, eff_ob], ['1', '2'], arb)

        # 2. DETECÇÃO 3-WAY (1X2)
        for i, book_1 in enumerate(bookmakers):
            for book_X in bookmakers:
                for book_2 in bookmakers:
                    # Odds para 1, X e 2
                    o1 = all_odds[book_1].get('1') or all_odds[book_1].get('home')
                    oX = all_odds[book_X].get('X') or all_odds[book_X].get('draw')
                    o2 = all_odds[book_2].get('2') or all_odds[book_2].get('away')
                    
                    if not o1 or not oX or not o2: continue
                    
                    # Ajustes Betfair
                    e1 = 1 + (o1 - 1) * (1 - self.betfair_commission) if book_1 == 'betfair' else o1
                    eX = 1 + (oX - 1) * (1 - self.betfair_commission) if book_X == 'betfair' else oX
                    e2 = 1 + (o2 - 1) * (1 - self.betfair_commission) if book_2 == 'betfair' else o2
                    
                    arb = (1/e1) + (1/eX) + (1/e2)
                    
                    if arb < 1.0:
                        profit = (1 - arb) * 100
                        if self.min_profit_pct <= profit <= self.max_profit_pct:
                            self._process_opp_3way(opportunities, game_data, [book_1, book_X, book_2], [e1, eX, e2], ['1', 'X', '2'], arb)

        opportunities.sort(key=lambda x: x['profit_pct'], reverse=True)
        return opportunities

    def _process_opp_3way(self, opportunities, game_data, books, odds, outcomes, arb):
        profit_pct = (1 - arb) * 100
        
        # Cálculo de stakes (3-way)
        # total_stake = bankroll_per_book * stake_pct * 3 (assumindo que usamos 3 casas ou balanceamos)
        total_stake = self.bankroll_per_book * self.stake_pct * 3
        s1 = math.ceil(total_stake / (odds[0] * arb))
        sX = math.ceil(total_stake / (odds[1] * arb))
        s2 = math.ceil(total_stake / (odds[2] * arb))
        
        actual_total = s1 + sX + s2
        actual_return = min(s1 * odds[0], sX * odds[1], s2 * odds[2])
        actual_profit = actual_return - actual_total
        actual_roi = (actual_profit / actual_total) * 100

        if actual_profit <= 0: return

        opportunities.append({
            'home_team': game_data['home_team'],
            'away_team': game_data['away_team'],
            'league': game_data.get('league', 'N/A'),
            'match_date': str(game_data.get('match_date', '')),
            'outcome_A': outcomes[0],
            'bookmaker_A': books[0],
            'odds_A': round(odds[0], 2),
            'stake_A': float(s1),
            'outcome_B': outcomes[2], # Usando B para o outro lado (simplificado para o modelo atual)
            'bookmaker_B': books[2],
            'odds_B': round(odds[2], 2),
            'stake_B': float(s2),
            # Incluir dados do empate se necessário ou adaptar o modelo para 3 casas
            'extra_outcome': outcomes[1],
            'extra_bookmaker': books[1],
            'extra_odds': round(odds[1], 2),
            'extra_stake': float(sX),
            'total_stake': float(actual_total),
            'guaranteed_profit': round(float(actual_profit), 2),
            'profit_pct': round(float(actual_roi), 2),
            'roi': round(float(actual_roi), 2),
            'arb_index': round(arb, 4),
            'is_premium': any('pinnacle' in b for b in books)
        })

    def _process_opp(self, opportunities, game_data, books, odds, outcomes, arb):
        profit_pct = (1 - arb) * 100
        
        if profit_pct > self.max_profit_pct:
            logger.warning(f"ROI suspeito ({profit_pct:.1f}%) ignorado em {game_data['home_team']}")
            return

        if profit_pct < self.min_profit_pct:
            return

        # Cálculo de stakes (simplificado para 2-way)
        total_stake = self.bankroll_per_book * self.stake_pct * 2
        sA = math.ceil(total_stake / (odds[0] * arb))
        sB = math.ceil(total_stake / (odds[1] * arb))
        
        actual_total = sA + sB
        actual_return = min(sA * odds[0], sB * odds[1])
        actual_profit = actual_return - actual_total
        actual_roi = (actual_profit / actual_total) * 100

        if actual_profit <= 0: return

        opportunities.append({
            'home_team': game_data['home_team'],
            'away_team': game_data['away_team'],
            'league': game_data.get('league', 'N/A'),
            'match_date': str(game_data.get('match_date', '')),
            'outcome_A': outcomes[0],
            'bookmaker_A': books[0],
            'odds_A': round(odds[0], 2),
            'stake_A': float(sA),
            'outcome_B': outcomes[1],
            'bookmaker_B': books[1],
            'odds_B': round(odds[1], 2),
            'stake_B': float(sB),
            'total_stake': float(actual_total),
            'guaranteed_profit': round(float(actual_profit), 2),
            'profit_pct': round(float(actual_roi), 2),
            'roi': round(float(actual_roi), 2),
            'arb_index': round(arb, 4),
            'is_premium': ('pinnacle' in books)
        })
