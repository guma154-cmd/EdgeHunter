"""
EdgeHunter — Modelo Elo Adaptativo
Implementa rating Elo para futebol com:
- K dinâmico baseado na importância do jogo
- Ajuste por margem de vitória (MOV)
- Previsão de probabilidade via distribuição logística
- Decay temporal para ligas novas
"""
import numpy as np
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# K-factor padrão por competição (quanto mais importante, maior o K)
COMPETITION_K = {
    'champions_league': 40,
    'world_cup': 40,
    'premier_league': 30,
    'la_liga': 30,
    'bundesliga': 30,
    'serie_a': 30,
    'ligue_1': 28,
    'championship': 24,
    'default': 25
}


def expected_score(rating_a: float, rating_b: float, home_advantage: float = 100) -> float:
    """
    Probabilidade esperada de vitória do time A vs time B.
    Home advantage em pontos Elo equivale a ~67% de chance de vitória.
    """
    return 1 / (1 + 10 ** (-(rating_a - rating_b + home_advantage) / 400))


def mov_multiplier(goal_diff: int, winner_rating: float, loser_rating: float) -> float:
    """
    Multiplicador de Margin of Victory (MOV) — evita inflação do Elo.
    Baseado na fórmula do FiveThirtyEight para futebol.
    """
    if goal_diff == 0:
        return 1.0
    
    # Ajuste pela diferença de rating (underdog upset vale mais)
    rating_diff = abs(winner_rating - loser_rating)
    adj = max(1.0, (11 + goal_diff) / 8)
    adj *= max(0.5, 1 - rating_diff / 800)
    
    return adj * np.log(abs(goal_diff) + 1)


class EloModel:
    """
    Sistema de rating Elo adaptativo para futebol.
    
    Features:
    - K-factor dinâmico por competição
    - Ajuste por margem de vitória
    - Regressão à média ao início da temporada
    - Vantagem em casa configurável
    - Probabilidade de 3 outcomes (H/D/A) via método FiveThirtyEight
    """
    
    BASE_RATING = 1500
    HOME_ADVANTAGE = 100  # Pontos Elo de vantagem em casa
    SEASON_REGRESSION = 0.30  # 30% de regressão à média entre temporadas
    
    def __init__(self, home_advantage: float = 100):
        self.ratings: Dict[str, float] = {}
        self.home_advantage = home_advantage
        self.history: Dict[str, list] = {}  # Histórico de ratings por time
        self.games_played: Dict[str, int] = {}
        self.is_fitted = False
    
    def get_rating(self, team: str) -> float:
        """Retorna rating atual do time (base se não existir)."""
        return self.ratings.get(team, self.BASE_RATING)
    
    def _k_factor(self, league: str = 'default', games_played: int = 100) -> float:
        """
        K-factor dinâmico:
        - Maior para times com poucos jogos (novos no dataset)
        - Baseado na importância da liga
        """
        base_k = COMPETITION_K.get(league.lower(), COMPETITION_K['default'])
        
        # Reduzir K para times com muita história (mais estáveis)
        if games_played > 100:
            base_k *= 0.85
        
        return base_k
    
    def update(
        self,
        home_team: str,
        away_team: str,
        home_goals: int,
        away_goals: int,
        league: str = 'default'
    ) -> Tuple[float, float]:
        """
        Atualiza ratings após um resultado real.
        
        Returns:
            (nova_rating_home, nova_rating_away)
        """
        home_r = self.get_rating(home_team)
        away_r = self.get_rating(away_team)
        
        # Expected scores
        e_home = expected_score(home_r, away_r, self.home_advantage)
        e_away = 1 - e_home
        
        # Resultado observado
        if home_goals > away_goals:
            s_home, s_away = 1.0, 0.0
            goal_diff = home_goals - away_goals
            mov = mov_multiplier(goal_diff, home_r, away_r)
        elif home_goals < away_goals:
            s_home, s_away = 0.0, 1.0
            goal_diff = away_goals - home_goals
            mov = mov_multiplier(goal_diff, away_r, home_r)
        else:
            s_home, s_away = 0.5, 0.5
            mov = 1.0
        
        # K-factor dinâmico
        k_h = self._k_factor(league, self.games_played.get(home_team, 0))
        k_a = self._k_factor(league, self.games_played.get(away_team, 0))
        
        # Atualizar ratings com MOV
        new_home_r = home_r + k_h * mov * (s_home - e_home)
        new_away_r = away_r + k_a * mov * (s_away - e_away)
        
        # Armazenar
        self.ratings[home_team] = new_home_r
        self.ratings[away_team] = new_away_r
        
        # Histórico
        for team, rating in [(home_team, new_home_r), (away_team, new_away_r)]:
            if team not in self.history:
                self.history[team] = []
            self.history[team].append(rating)
            self.games_played[team] = self.games_played.get(team, 0) + 1
        
        return new_home_r, new_away_r
    
    def fit(self, matches_df) -> 'EloModel':
        """
        Treina o modelo sequencialmente nos jogos históricos.
        
        Args:
            matches_df: DataFrame ordenado por data com colunas:
                - home_team, away_team, home_score, away_score, league, match_date
        """
        df = matches_df.sort_values('match_date').copy()
        df = df.dropna(subset=['home_score', 'away_score'])
        
        current_season = None
        
        for _, row in df.iterrows():
            # Regressão à média no início de nova temporada
            season = row.get('season', None)
            if season and season != current_season:
                self._season_regression()
                current_season = season
            
            self.update(
                home_team=row['home_team'],
                away_team=row['away_team'],
                home_goals=int(row['home_score']),
                away_goals=int(row['away_score']),
                league=row.get('league', 'default')
            )
        
        self.is_fitted = True
        logger.info(f"Elo treinado: {len(self.ratings)} times")
        return self
    
    def _season_regression(self):
        """Regressão de 30% à média entre temporadas."""
        for team in self.ratings:
            self.ratings[team] = (
                self.ratings[team] * (1 - self.SEASON_REGRESSION) +
                self.BASE_RATING * self.SEASON_REGRESSION
            )
    
    def predict_1x2(
        self, home_team: str, away_team: str
    ) -> Tuple[float, float, float]:
        """
        Prediz probabilidades 1X2 usando método FiveThirtyEight.
        
        A distribuição logística é usada para converter a diferença
        de rating em probabilidade de vitória de cada time.
        O empate é estimado como 1 - P(home) - P(away) com correção.
        """
        home_r = self.get_rating(home_team)
        away_r = self.get_rating(away_team)
        
        # Probabilidade de vitória do time da casa
        prob_home_win = expected_score(home_r, away_r, self.home_advantage)
        prob_away_win = expected_score(away_r, home_r, -self.home_advantage)
        
        # Normalizamos: a soma de vitórias + empate + derrota = 1
        # Usamos fator de escala para estimar o empate
        raw_sum = prob_home_win + prob_away_win
        
        # Correção empírica: empates têm freq ~25% no futebol
        # Aplicamos fator baseado na diferença de rating
        rating_diff = abs(home_r + self.home_advantage - away_r)
        draw_factor = max(0.15, 0.30 - rating_diff / 2000)
        
        prob_draw = draw_factor
        prob_home = prob_home_win * (1 - draw_factor)
        prob_away = prob_away_win * (1 - draw_factor)
        
        # Normalizar
        total = prob_home + prob_draw + prob_away
        return prob_home / total, prob_draw / total, prob_away / total
    
    def get_rankings(self, top_n: int = 20) -> list:
        """Retorna ranking dos times por rating."""
        sorted_teams = sorted(
            self.ratings.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [
            {'rank': i+1, 'team': team, 'rating': round(rating, 1)}
            for i, (team, rating) in enumerate(sorted_teams[:top_n])
        ]
