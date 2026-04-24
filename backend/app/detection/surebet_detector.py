class SurebetDetector:
    """
    Detecta oportunidades de arbitragem entre casas.
    Fórmula: (1/odd_A) + (1/odd_B) < 1 = lucro garantido
    """

    def __init__(self, min_profit_pct: float = 1.0, 
                 stake_pct: float = 0.10, 
                 bankroll_per_book: float = 20.0):
        self.min_profit_pct = min_profit_pct  # lucro mínimo 1%
        self.stake_pct = stake_pct            # 10% por casa em testes
        self.bankroll_per_book = bankroll_per_book # R$20 por casa

    def detect(self, game_data: dict) -> list:
        """
        Analisa um jogo e retorna oportunidades de surebet.
        game_data deve conter odds de múltiplas casas.

        Retorna lista de dicts:
        {
          'home_team': str,
          'away_team': str,
          'league': str,
          'match_date': str,
          'outcome_A': str,       # ex: 'home'
          'bookmaker_A': str,     # ex: 'bet365'
          'odds_A': float,
          'stake_A': float,       # stake calculado
          'outcome_B': str,       # ex: 'away'
          'bookmaker_B': str,     # ex: 'betano'
          'odds_B': float,
          'stake_B': float,
          'total_stake': float,   # stake total
          'guaranteed_profit': float,  # lucro em R$
          'profit_pct': float,    # % de lucro
          'roi': float
        }
        """
        opportunities = []
        
        soft_books = game_data.get('all_odds', {})
        # all_odds = {'bet365': {'home': 2.10, 'draw': 3.40, 'away': 3.20},
        #             'betano': {'home': 2.05, 'draw': 3.50, 'away': 3.30}, ...}

        bookmakers = list(soft_books.keys())

        # Comparar cada par de casas
        for i, book_A in enumerate(bookmakers):
            for book_B in bookmakers[i+1:]:
                odds_A = soft_books[book_A]
                odds_B = soft_books[book_B]

                # Testar cada combinação de mercado 2-way
                # (home vs away, ignorando draw para simplificar)
                for outcome_A in ['home', 'away']:
                    outcome_B = 'away' if outcome_A == 'home' else 'home'

                    odd_A = odds_A.get(outcome_A)
                    odd_B = odds_B.get(outcome_B)

                    if not odd_A or not odd_B:
                        continue
                    if odd_A <= 1.0 or odd_B <= 1.0:
                        continue

                    # Fórmula de arbitragem
                    arb = (1/odd_A) + (1/odd_B)

                    if arb < 1.0:  # existe lucro
                        profit_pct = (1 - arb) * 100
                        if profit_pct < self.min_profit_pct:
                            continue

                        # Calcular stakes proporcionais
                        # max_stake_per_side = BANKROLL_PER_BOOK * STAKE_PCT
                        # total_stake = max_stake_per_side * 2
                        max_stake_per_side = self.bankroll_per_book * self.stake_pct
                        total_stake = max_stake_per_side * 2
                        
                        stake_A = total_stake / (odd_A * arb)
                        stake_B = total_stake / (odd_B * arb)
                        guaranteed_return = stake_A * odd_A
                        guaranteed_profit = guaranteed_return - total_stake

                        # Verificar se é "Sharp Verified" (confirmado pela Pinnacle)
                        pinnacle_odds = soft_books.get('pinnacle', {})
                        is_sharp_verified = False
                        if pinnacle_odds:
                            # Se a odd da Pinnacle é menor que a odd oferecida, o edge é mais provável de ser real
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
                            'stake_A': round(stake_A, 2),
                            'outcome_B': outcome_B,
                            'bookmaker_B': book_B,
                            'odds_B': round(odd_B, 2),
                            'stake_B': round(stake_B, 2),
                            'total_stake': round(total_stake, 2),
                            'guaranteed_profit': round(guaranteed_profit, 2),
                            'profit_pct': round(profit_pct, 2),
                            'roi': round(profit_pct, 2),
                            'arb_index': round(arb, 4),
                            'is_sharp_verified': is_sharp_verified,
                            'is_premium': (book_A == 'pinnacle' or book_B == 'pinnacle')
                        })

        # Ordenar por maior lucro
        opportunities.sort(key=lambda x: x['profit_pct'], reverse=True)
        return opportunities

    def calculate_stakes(self, odd_A: float, odd_B: float,
                         total_stake: float) -> tuple:
        """Calcula stakes proporcionais para garantir lucro igual nos dois lados."""
        arb = (1/odd_A) + (1/odd_B)
        stake_A = total_stake / (odd_A * arb)
        stake_B = total_stake / (odd_B * arb)
        return round(stake_A, 2), round(stake_B, 2)
