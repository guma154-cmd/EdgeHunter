"""
EdgeHunter — Modelo Bayesiano
Atualização Bayesiana usando prior conjugado (Dirichlet-Multinomial).

A cada novo resultado, atualiza a distribuição de probabilidade
dos três outcomes (H/D/A) para cada par de times.
"""
import numpy as np
from typing import Dict, Tuple, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class BayesianModel:
    """
    Modelo Bayesiano com prior Dirichlet para outcomes 1X2.
    
    Prior: Dirichlet(α_H, α_D, α_A) onde as concentrações representam
    nossa crença inicial sobre a distribuição de resultados.
    
    Posterior: Após observar resultados reais, o posterior é:
    Dirichlet(α_H + n_H, α_D + n_D, α_A + n_A)
    
    Predição: E[p] = α_i / sum(α)
    """
    
    # Prior baseado na distribuição histórica do futebol europeu
    GLOBAL_PRIOR = {'home': 45.0, 'draw': 27.0, 'away': 28.0}
    
    def __init__(self, prior_strength: float = 20.0):
        """
        Args:
            prior_strength: Força do prior (equiv. a N jogos anteriores).
                          Maior = mais conservador, menor = mais reativo.
        """
        self.prior_strength = prior_strength
        
        # Contadores por par de times (H2H direto)
        self.h2h_counts: Dict[str, Dict[str, float]] = {}
        
        # Contadores por time em casa e fora
        self.home_counts: Dict[str, Dict[str, float]] = {}
        self.away_counts: Dict[str, Dict[str, float]] = {}
        
        # Contadores globais
        self.global_counts = {'home': 0.0, 'draw': 0.0, 'away': 0.0}
        self.total_games = 0
        
        self.is_fitted = False
    
    def _h2h_key(self, home: str, away: str) -> str:
        return f"{home}__vs__{away}"
    
    def update(
        self,
        home_team: str,
        away_team: str,
        home_goals: int,
        away_goals: int,
        weight: float = 1.0
    ):
        """
        Atualiza as contagens Bayesianas após um resultado.
        Suporta peso fracionário (decay temporal).
        """
        key = self._h2h_key(home_team, away_team)
        
        if key not in self.h2h_counts:
            self.h2h_counts[key] = {'home': 0.0, 'draw': 0.0, 'away': 0.0}
        if home_team not in self.home_counts:
            self.home_counts[home_team] = {'home': 0.0, 'draw': 0.0, 'away': 0.0}
        if away_team not in self.away_counts:
            self.away_counts[away_team] = {'home': 0.0, 'draw': 0.0, 'away': 0.0}
        
        if home_goals > away_goals:
            outcome = 'home'
        elif home_goals == away_goals:
            outcome = 'draw'
        else:
            outcome = 'away'
        
        self.h2h_counts[key][outcome] += weight
        self.home_counts[home_team][outcome] += weight
        self.away_counts[away_team][outcome] += weight
        self.global_counts[outcome] += weight
        self.total_games += weight
    
    def fit(self, matches_df) -> 'BayesianModel':
        """
        Treina o modelo com dados históricos usando decay temporal.
        """
        import pandas as pd
        
        df = matches_df.sort_values('match_date').copy()
        df = df.dropna(subset=['home_score', 'away_score'])
        
        reference_date = pd.Timestamp.now()
        
        for _, row in df.iterrows():
            # Decay temporal: jogos mais antigos têm menos peso
            days_ago = (reference_date - pd.Timestamp(row['match_date'])).days
            weight = np.exp(-0.002 * days_ago)  # Mesmo decay do Dixon-Coles
            
            self.update(
                home_team=row['home_team'],
                away_team=row['away_team'],
                home_goals=int(row['home_score']),
                away_goals=int(row['away_score']),
                weight=max(weight, 0.05)
            )
        
        self.is_fitted = True
        logger.info(f"Bayesiano treinado: {self.total_games:.0f} jogos (com decay)")
        return self
    
    def predict_1x2(
        self,
        home_team: str,
        away_team: str,
        use_h2h: bool = True
    ) -> Tuple[float, float, float]:
        """
        Prediz probabilidades 1X2 combinando:
        1. Prior global (distribuição média do futebol)
        2. Performance do time em casa
        3. Performance do adversário fora
        4. H2H direto (se disponível)
        
        Retorna: (prob_home, prob_draw, prob_away)
        """
        # --- Prior global ---
        prior_total = sum(self.GLOBAL_PRIOR.values())
        prior_h = self.GLOBAL_PRIOR['home'] / prior_total
        prior_d = self.GLOBAL_PRIOR['draw'] / prior_total
        prior_a = self.GLOBAL_PRIOR['away'] / prior_total
        
        # --- Posterior do time em casa ---
        home_data = self.home_counts.get(home_team, {})
        home_total = sum(home_data.values()) + self.prior_strength
        home_h = (home_data.get('home', 0) + self.prior_strength * prior_h) / home_total
        home_d = (home_data.get('draw', 0) + self.prior_strength * prior_d) / home_total
        home_a = (home_data.get('away', 0) + self.prior_strength * prior_a) / home_total
        
        # --- Posterior do time fora ---
        away_data = self.away_counts.get(away_team, {})
        away_total = sum(away_data.values()) + self.prior_strength
        away_h = (away_data.get('home', 0) + self.prior_strength * prior_h) / away_total
        away_d = (away_data.get('draw', 0) + self.prior_strength * prior_d) / away_total
        away_a = (away_data.get('away', 0) + self.prior_strength * prior_a) / away_total
        
        # --- H2H direto ---
        key = self._h2h_key(home_team, away_team)
        h2h_data = self.h2h_counts.get(key, {})
        h2h_total = sum(h2h_data.values())
        h2h_weight = min(1.0, h2h_total / 10)  # Peso máximo com 10 jogos H2H
        
        # Combinar: home + away (50/50) e ajustar com H2H
        combined_h = (home_h + away_h) / 2
        combined_d = (home_d + away_d) / 2
        combined_a = (home_a + away_a) / 2
        
        if use_h2h and h2h_total > 0:
            h2h_h = (h2h_data.get('home', 0) + self.prior_strength * prior_h) / (h2h_total + self.prior_strength)
            h2h_d = (h2h_data.get('draw', 0) + self.prior_strength * prior_d) / (h2h_total + self.prior_strength)
            h2h_a = (h2h_data.get('away', 0) + self.prior_strength * prior_a) / (h2h_total + self.prior_strength)
            
            # Blend: H2H mais relevante quando há mais jogos
            combined_h = combined_h * (1 - h2h_weight) + h2h_h * h2h_weight
            combined_d = combined_d * (1 - h2h_weight) + h2h_d * h2h_weight
            combined_a = combined_a * (1 - h2h_weight) + h2h_a * h2h_weight
        
        # Normalizar
        total = combined_h + combined_d + combined_a
        if total == 0:
            return 0.45, 0.27, 0.28
        
        return combined_h / total, combined_d / total, combined_a / total
    
    def online_update(
        self, home_team: str, away_team: str, home_goals: int, away_goals: int
    ):
        """
        Atualização online após resultado real (sem refit completo).
        Peso = 1.0 (jogo atual, sem decay).
        """
        self.update(home_team, away_team, home_goals, away_goals, weight=1.0)
        logger.debug(f"Bayesiano atualizado: {home_team} {home_goals}-{away_goals} {away_team}")
