import logging

logger = logging.getLogger(__name__)

class SurebetDetector:
    """
    Detecta oportunidades de arbitragem entre casas.
    Fórmula: (1/odd_A) + (1/odd_B) < 1 = lucro garantido
    """

    def __init__(self, min_profit_pct: float = 1.0, 
                 max_profit_pct: float = 8.0,
                 stake_pct: float = 0.10, 
                 bankroll_per_book: float = 20.0,
                 betfair_commission: float = 0.05):
        self.min_profit_pct = min_profit_pct      # lucro mínimo (ex: 1%)
        self.max_profit_pct = max_profit_pct      # MELHORIA 1 — ROI acima disso é suspeito
        self.stake_pct = stake_pct                # % da banca por lado
        self.bankroll_per_book = bankroll_per_book # banca por casa
        self.betfair_commission = betfair_commission # MELHORIA 2 — 5% comissão Betfair

    def detect(self, game_data: dict) -> list:
        """
        Analisa um jogo e retorna oportunidades de surebet.
        """
        opportunities = []
        
        soft_books = game_data.get('all_odds', {})
        bookmakers = list(soft_books.keys())

        # Comparar cada par de casas
        for i, book_A in enumerate(bookmakers):
            for book_B in bookmakers[i+1:]:
                odds_A_orig = soft_books[book_A]
                odds_B_orig = soft_books[book_B]

                for outcome_A in ['home', 'away']:
                    outcome_B = 'away' if outcome_A == 'home' else 'home'

                    odd_A = odds_A_orig.get(outcome_A)
                    odd_B = odds_B_orig.get(outcome_B)

                    if not odd_A or not odd_B:
                        continue
                    if odd_A <= 1.0 or odd_B <= 1.0:
                        continue

                    # MELHORIA 2 — Ajustar odd efetiva se for Betfair (comissão sobre o lucro)
                    # Simplificação: odd_efetiva = 1 + (odd - 1) * (1 - comissão)
                    # Se odd=2.0 e comissão=5%, lucro líquido é 0.95, odd_efetiva=1.95
                    if book_A == 'betfair':
                        odd_A = 1 + (odd_A - 1) * (1 - self.betfair_commission)
                    if book_B == 'betfair':
                        odd_B = 1 + (odd_B - 1) * (1 - self.betfair_commission)

                    # Fórmula de arbitragem com odds líquidas
                    arb = (1/odd_A) + (1/odd_B)

                    if arb < 1.0:  # existe lucro
                        profit_pct = (1 - arb) * 100
                        
                        # MELHORIA 1 — Filtro de ROI suspeito
                        if profit_pct > self.max_profit_pct:
                            logger.warning(
                                f"Surebet suspeito ignorado: ROI={profit_pct:.1f}% "
                                f"({book_A} vs {book_B}) — provável erro de scraping"
                            )
                            continue

                        if profit_pct < self.min_profit_pct:
                            continue

                        # Calcular stakes baseados na banca e no stake_pct configurado
                        max_stake_per_side = self.bankroll_per_book * self.stake_pct
                        total_stake = max_stake_per_side * 2
                        
                        stake_A = total_stake / (odd_A * arb)
                        stake_B = total_stake / (odd_B * arb)
                        guaranteed_return = stake_A * odd_A
                        guaranteed_profit = guaranteed_return - total_stake

                        # Sharp Verified (Pinnacle)
                        pinnacle_odds = soft_books.get('pinnacle', {})
                        is_sharp_verified = False
                        if pinnacle_odds:
                            pinn_odd = pinnacle_odds.get(outcome_A)
                            if pinn_odd and pinn_odd < odd_A:
                                is_sharp_verified = True

                        opportunities.append({
                            'home_team': game_data['home_team'],
                            'away_team': game_data['away_team'],
                            'league': game_data['league'],
                            'match_date': str(game_data['match_date']),
                            'outcome_A': outcome_A,
                            'bookmaker_A': book_A,
                            'odds_A': round(odd_A, 2),
                            'odds_A_raw': round(odds_A_orig.get(outcome_A), 2),
                            'stake_A': round(stake_A, 2),
                            'outcome_B': outcome_B,
                            'bookmaker_B': book_B,
                            'odds_B': round(odd_B, 2),
                            'odds_B_raw': round(odds_B_orig.get(outcome_B), 2),
                            'stake_B': round(stake_B, 2),
                            'total_stake': round(total_stake, 2),
                            'guaranteed_profit': round(guaranteed_profit, 2),
                            'profit_pct': round(profit_pct, 2),
                            'roi': round(profit_pct, 2),
                            'arb_index': round(arb, 4),
                            'is_sharp_verified': is_sharp_verified,
                            'is_premium': (book_A == 'pinnacle' or book_B == 'pinnacle')
                        })

        opportunities.sort(key=lambda x: x['profit_pct'], reverse=True)
        return opportunities
