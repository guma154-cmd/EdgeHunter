"""
EdgeHunter — Modelo Dixon-Coles (Poisson Bivariado Corrigido)
Implementa o modelo clássico de Mark Dixon e Stuart Coles (1997)
para predição de resultados de futebol.

Referência: Dixon, M.J. & Coles, S.G. (1997). 
"Modelling Association Football Scores and Inefficiencies in the 
Football Betting Market." Applied Statistics, 46(2), 265-280.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson
from typing import Dict, Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


def tau_correction(x: int, y: int, lambda_: float, mu_: float, rho: float) -> float:
    """
    Fator de correção tau de Dixon-Coles para placar baixo (0-0, 1-0, 0-1, 1-1).
    Ajusta a distribuição bivariada de Poisson para correlações reais.
    """
    if x == 0 and y == 0:
        return 1 - lambda_ * mu_ * rho
    elif x == 1 and y == 0:
        return 1 + mu_ * rho
    elif x == 0 and y == 1:
        return 1 + lambda_ * rho
    elif x == 1 and y == 1:
        return 1 - rho
    else:
        return 1.0


def dixon_coles_log_likelihood(
    params: np.ndarray,
    teams: List[str],
    home_teams: List[str],
    away_teams: List[str],
    home_goals: List[int],
    away_goals: List[int],
    weights: Optional[List[float]] = None
) -> float:
    """
    Log-likelihood negativa do modelo Dixon-Coles.
    Minimizamos esta função para encontrar os parâmetros ótimos.
    """
    n_teams = len(teams)
    team_idx = {team: i for i, team in enumerate(teams)}
    
    # Extrair parâmetros
    alphas = params[:n_teams]          # Força de ataque
    betas = params[n_teams:2*n_teams]  # Força de defesa
    gamma = params[2*n_teams]          # Vantagem casa
    rho = params[2*n_teams + 1]        # Correlação Dixon-Coles
    
    if weights is None:
        weights = [1.0] * len(home_teams)
    
    log_lik = 0.0
    
    for i, (ht, at, hg, ag, w) in enumerate(
        zip(home_teams, away_teams, home_goals, away_goals, weights)
    ):
        if ht not in team_idx or at not in team_idx:
            continue
        
        hi = team_idx[ht]
        ai = team_idx[at]
        
        # Taxa esperada de gols
        lambda_ = np.exp(alphas[hi] + betas[ai] + gamma)  # Gols esperados em casa
        mu_ = np.exp(alphas[ai] + betas[hi])               # Gols esperados fora
        
        # Correção para placares baixos
        tau = tau_correction(hg, ag, lambda_, mu_, rho)
        
        if tau <= 0:
            return 1e10  # Penalidade para parâmetros inválidos
        
        log_lik += w * (
            np.log(tau) +
            np.log(poisson.pmf(hg, lambda_)) +
            np.log(poisson.pmf(ag, mu_))
        )
    
    return -log_lik  # Negativo porque minimizamos


class DixonColesModel:
    """
    Modelo de Dixon-Coles para previsão de futebol.
    
    Implementa:
    - Estimação MLE dos parâmetros de ataque/defesa
    - Fator de vantagem em casa
    - Correção tau para placar baixo
    - Decay temporal (xi) para dar mais peso a jogos recentes
    """
    
    def __init__(self, xi: float = 0.002):
        """
        Args:
            xi: Parâmetro de decay temporal. 
                0.002 = meia-vida de ~1 ano (padrão Dixon-Coles)
        """
        self.xi = xi
        self.teams: List[str] = []
        self.alphas: Dict[str, float] = {}  # Força de ataque
        self.betas: Dict[str, float] = {}   # Força de defesa
        self.gamma: float = 0.0              # Vantagem em casa
        self.rho: float = -0.13             # Correlação D-C (típico)
        self.is_fitted = False
    
    def _compute_time_weights(self, match_dates, reference_date=None) -> List[float]:
        """Calcula pesos temporais com decay exponencial."""
        import pandas as pd
        if reference_date is None:
            reference_date = pd.Timestamp.now()
        
        weights = []
        for date in match_dates:
            days_ago = (reference_date - pd.Timestamp(date)).days
            weight = np.exp(-self.xi * days_ago)
            weights.append(max(weight, 0.001))
        
        return weights
    
    def fit(self, matches_df) -> 'DixonColesModel':
        """
        Treina o modelo nos dados históricos.
        
        Args:
            matches_df: DataFrame com colunas:
                - home_team, away_team
                - home_score, away_score
                - match_date
        """
        import pandas as pd
        
        df = matches_df.copy()
        df = df.dropna(subset=['home_score', 'away_score'])
        
        if len(df) < 50:
            logger.warning(f"Apenas {len(df)} jogos para treinar Dixon-Coles. Mínimo recomendado: 200")
        
        # Teams únicos
        all_teams = sorted(set(df['home_team'].tolist() + df['away_team'].tolist()))
        self.teams = all_teams
        n_teams = len(all_teams)
        
        # Pesos temporais
        weights = self._compute_time_weights(df['match_date'])
        
        # Parâmetros iniciais
        alpha_init = np.zeros(n_teams)
        beta_init = np.zeros(n_teams)
        gamma_init = np.array([0.3])   # Vantagem em casa
        rho_init = np.array([-0.1])    # Correlação
        
        x0 = np.concatenate([alpha_init, beta_init, gamma_init, rho_init])
        
        # Restrição: soma dos alphas = 0 (identificabilidade)
        constraints = {
            'type': 'eq',
            'fun': lambda params: np.sum(params[:n_teams])
        }
        
        # Limites razoáveis
        bounds = (
            [(-3, 3)] * n_teams +      # alphas
            [(-3, 3)] * n_teams +      # betas
            [(0, 1)] +                  # gamma
            [(-0.5, 0.5)]              # rho
        )
        
        result = minimize(
            dixon_coles_log_likelihood,
            x0,
            args=(
                all_teams,
                df['home_team'].tolist(),
                df['away_team'].tolist(),
                df['home_score'].astype(int).tolist(),
                df['away_score'].astype(int).tolist(),
                weights
            ),
            method='L-BFGS-B',
            bounds=bounds,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )
        
        if not result.success:
            logger.warning(f"Otimização Dixon-Coles: {result.message}")
        
        # Armazenar parâmetros
        params = result.x
        for i, team in enumerate(all_teams):
            self.alphas[team] = params[i]
            self.betas[team] = params[n_teams + i]
        
        self.gamma = params[2 * n_teams]
        self.rho = params[2 * n_teams + 1]
        self.is_fitted = True
        
        logger.info(f"Dixon-Coles treinado: {n_teams} times, {len(df)} jogos, γ={self.gamma:.3f}, ρ={self.rho:.3f}")
        return self
    
    def predict_score_matrix(
        self, home_team: str, away_team: str, max_goals: int = 10
    ) -> np.ndarray:
        """
        Retorna matriz de probabilidade de placar [home_goals x away_goals].
        """
        if not self.is_fitted:
            raise ValueError("Modelo não treinado. Chame fit() primeiro.")
        
        # Usar média global para times desconhecidos
        alpha_h = self.alphas.get(home_team, np.mean(list(self.alphas.values())))
        beta_h = self.betas.get(home_team, np.mean(list(self.betas.values())))
        alpha_a = self.alphas.get(away_team, np.mean(list(self.alphas.values())))
        beta_a = self.betas.get(away_team, np.mean(list(self.betas.values())))
        
        lambda_ = np.exp(alpha_h + beta_a + self.gamma)
        mu_ = np.exp(alpha_a + beta_h)
        
        matrix = np.zeros((max_goals + 1, max_goals + 1))
        
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                tau = tau_correction(i, j, lambda_, mu_, self.rho)
                matrix[i][j] = tau * poisson.pmf(i, lambda_) * poisson.pmf(j, mu_)
        
        # Normalizar para garantir soma = 1
        matrix = matrix / matrix.sum()
        return matrix
    
    def predict_1x2(self, home_team: str, away_team: str) -> Tuple[float, float, float]:
        """
        Retorna probabilidades (home_win, draw, away_win).
        """
        matrix = self.predict_score_matrix(home_team, away_team)
        
        # Probabilidade de vitória em casa (diagonal acima)
        prob_home = np.sum(np.tril(matrix, -1))
        # Probabilidade de empate (diagonal principal)
        prob_draw = np.sum(np.diag(matrix))
        # Probabilidade de vitória fora (diagonal abaixo)
        prob_away = np.sum(np.triu(matrix, 1))
        
        # Normalizar
        total = prob_home + prob_draw + prob_away
        return prob_home / total, prob_draw / total, prob_away / total
    
    def predict_over_under(
        self, home_team: str, away_team: str, line: float = 2.5
    ) -> Tuple[float, float]:
        """
        Retorna probabilidades (over, under) para uma linha de gols.
        """
        matrix = self.predict_score_matrix(home_team, away_team)
        n = matrix.shape[0]
        
        prob_over = 0.0
        prob_under = 0.0
        
        for i in range(n):
            for j in range(n):
                total_goals = i + j
                if total_goals > line:
                    prob_over += matrix[i][j]
                else:
                    prob_under += matrix[i][j]
        
        total = prob_over + prob_under
        return prob_over / total, prob_under / total
    
    def get_team_strengths(self) -> Dict[str, Dict]:
        """Retorna força de ataque e defesa de todos os times."""
        if not self.is_fitted:
            return {}
        
        return {
            team: {
                'attack': self.alphas.get(team, 0),
                'defense': self.betas.get(team, 0),
                'overall': self.alphas.get(team, 0) - self.betas.get(team, 0)
            }
            for team in self.teams
        }
