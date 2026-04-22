"""
EdgeHunter — Ensemble com Pesos Adaptativos
Orquestra os 4 modelos com pesos que se ajustam baseados
na performance histórica de cada um (Brier Score).
"""
import numpy as np
from typing import Dict, Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class EnsembleModel:
    """
    Ensemble adaptativo de 4 modelos com pesos auto-ajustáveis.
    
    O peso de cada modelo é inversamente proporcional ao seu Brier Score:
    - Modelo mais acurado → maior peso
    - Pesos se normalizam para somar 1
    - Mínimo de 5% por modelo (evita exclusão total)
    
    Método: Performance-Weighted Average
    """
    
    MIN_WEIGHT = 0.05  # Peso mínimo por modelo
    
    def __init__(self, initial_weights: Optional[Dict[str, float]] = None):
        self.weights = initial_weights or {
            'dixon_coles': 0.30,
            'elo': 0.20,
            'xgboost': 0.35,
            'bayesian': 0.15
        }
        
        # Histórico de performance por modelo
        self.brier_history: Dict[str, List[float]] = {
            model: [] for model in self.weights
        }
        
        self._validate_weights()
    
    def _validate_weights(self):
        """Garante que os pesos somam 1 e respeitam o mínimo."""
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}
        
        # Aplicar mínimo
        for model in self.weights:
            self.weights[model] = max(self.weights[model], self.MIN_WEIGHT)
        
        # Renormalizar
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}
    
    def predict_1x2(
        self,
        dc_probs: Tuple[float, float, float],    # Dixon-Coles
        elo_probs: Tuple[float, float, float],   # Elo
        xgb_probs: Tuple[float, float, float],   # XGBoost
        bay_probs: Tuple[float, float, float]    # Bayesiano
    ) -> Tuple[float, float, float]:
        """
        Combina as probabilidades dos 4 modelos com pesos adaptativos.
        
        Returns:
            (prob_home, prob_draw, prob_away) calibradas
        """
        probs = {
            'dixon_coles': np.array(dc_probs),
            'elo': np.array(elo_probs),
            'xgboost': np.array(xgb_probs),
            'bayesian': np.array(bay_probs)
        }
        
        # Média ponderada
        ensemble = np.zeros(3)
        for model, prob in probs.items():
            ensemble += self.weights[model] * np.array(prob)
        
        # Normalizar
        total = ensemble.sum()
        if total == 0:
            return 0.45, 0.27, 0.28
        
        ensemble = ensemble / total
        return float(ensemble[0]), float(ensemble[1]), float(ensemble[2])
    
    def update_weights_from_brier(
        self,
        model_brier_scores: Dict[str, float],
        window: int = 50
    ):
        """
        Atualiza os pesos baseados no Brier Score recente de cada modelo.
        
        Modelos com Brier Score menor recebem peso maior.
        Usa transformação: peso ∝ 1 / (brier_score + ε)
        
        Args:
            model_brier_scores: {'dixon_coles': 0.22, 'elo': 0.24, ...}
            window: últimos N resultados para calcular
        """
        # Adicionar ao histórico
        for model, score in model_brier_scores.items():
            if model in self.brier_history:
                self.brier_history[model].append(score)
                # Manter apenas os últimos N
                self.brier_history[model] = self.brier_history[model][-window:]
        
        # Calcular média de Brier de cada modelo
        avg_briers = {}
        for model in self.weights:
            history = self.brier_history[model]
            if len(history) < 10:
                avg_briers[model] = 0.25  # Prior: média histórica do futebol
            else:
                avg_briers[model] = np.mean(history[-window:])
        
        # Pesos inversamente proporcionais ao Brier Score
        epsilon = 0.01
        raw_weights = {model: 1 / (brier + epsilon) for model, brier in avg_briers.items()}
        
        # Normalizar e aplicar mínimo
        total = sum(raw_weights.values())
        new_weights = {model: w / total for model, w in raw_weights.items()}
        
        # Garantir mínimo
        for model in new_weights:
            new_weights[model] = max(new_weights[model], self.MIN_WEIGHT)
        
        # Renormalizar após mínimo
        total = sum(new_weights.values())
        self.weights = {model: w / total for model, w in new_weights.items()}
        
        logger.info(f"Pesos atualizados: {self.get_weights_summary()}")
    
    def get_weights_summary(self) -> str:
        return " | ".join([f"{k}: {v:.1%}" for k, v in self.weights.items()])
    
    def to_dict(self) -> Dict:
        return {
            'weights': self.weights,
            'brier_history_size': {
                model: len(hist) for model, hist in self.brier_history.items()
            }
        }


class ModelEnsemble:
    """
    Orquestrador principal que integra todos os modelos.
    Gerencia o ciclo de vida e previsões.
    """
    
    def __init__(self):
        from app.engine.dixon_coles import DixonColesModel
        from app.engine.elo import EloModel
        from app.engine.xgboost_model import XGBoostModel
        from app.engine.bayesian import BayesianModel
        from app.engine.calibration import PlattCalibration
        
        self.dixon_coles = DixonColesModel()
        self.elo = EloModel()
        self.xgboost = XGBoostModel()
        self.bayesian = BayesianModel()
        self.ensemble = EnsembleModel()
        self.calibration = PlattCalibration()
        
        self.historical_df = None
        self.is_ready = False
    
    def train(self, matches_df) -> 'ModelEnsemble':
        """Treina todos os modelos."""
        import pandas as pd
        self.historical_df = matches_df.copy()
        
        logger.info("Iniciando treinamento do ensemble...")
        
        # 1. Dixon-Coles
        try:
            self.dixon_coles.fit(matches_df)
            logger.info("✅ Dixon-Coles treinado")
        except Exception as e:
            logger.error(f"❌ Dixon-Coles falhou: {e}")
        
        # 2. Elo (treinamento sequencial)
        try:
            self.elo.fit(matches_df)
            logger.info("✅ Elo treinado")
        except Exception as e:
            logger.error(f"❌ Elo falhou: {e}")
        
        # 3. XGBoost
        try:
            self.xgboost.fit(matches_df, self.elo.ratings)
            logger.info("✅ XGBoost treinado")
        except Exception as e:
            logger.error(f"❌ XGBoost falhou: {e}")
        
        # 4. Bayesiano
        try:
            self.bayesian.fit(matches_df)
            logger.info("✅ Bayesiano treinado")
        except Exception as e:
            logger.error(f"❌ Bayesiano falhou: {e}")
        
        self.is_ready = True
        logger.info(f"Ensemble pronto. Pesos: {self.ensemble.get_weights_summary()}")
        return self
    
    def predict(
        self,
        home_team: str,
        away_team: str,
        match_date: str = None
    ) -> Dict:
        """
        Gera previsão completa para um jogo.
        
        Returns:
            Dict com probabilidades individuais, ensemble e calibradas
        """
        if not self.is_ready:
            raise ValueError("Ensemble não treinado. Chame train() primeiro.")
        
        import pandas as pd
        match_date = match_date or pd.Timestamp.now().isoformat()
        
        # Previsões individuais
        try:
            dc = self.dixon_coles.predict_1x2(home_team, away_team)
        except Exception:
            dc = (0.45, 0.27, 0.28)
        
        try:
            elo = self.elo.predict_1x2(home_team, away_team)
        except Exception:
            elo = (0.45, 0.27, 0.28)
        
        try:
            xgb = self.xgboost.predict_1x2(
                home_team, away_team, self.elo.ratings,
                match_date, self.historical_df
            )
        except Exception:
            xgb = (0.45, 0.27, 0.28)
        
        try:
            bay = self.bayesian.predict_1x2(home_team, away_team)
        except Exception:
            bay = (0.45, 0.27, 0.28)
        
        # Ensemble
        ensemble_probs = self.ensemble.predict_1x2(dc, elo, xgb, bay)
        
        # Calibração (Platt Scaling)
        calibrated = self.calibration.transform(ensemble_probs)
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'individual_models': {
                'dixon_coles': {'home': dc[0], 'draw': dc[1], 'away': dc[2]},
                'elo': {'home': elo[0], 'draw': elo[1], 'away': elo[2]},
                'xgboost': {'home': xgb[0], 'draw': xgb[1], 'away': xgb[2]},
                'bayesian': {'home': bay[0], 'draw': bay[1], 'away': bay[2]}
            },
            'ensemble': {
                'home': ensemble_probs[0],
                'draw': ensemble_probs[1],
                'away': ensemble_probs[2]
            },
            'calibrated': {
                'home': calibrated[0],
                'draw': calibrated[1],
                'away': calibrated[2]
            },
            'weights': self.ensemble.weights
        }
    
    def online_update(
        self, home_team: str, away_team: str, home_goals: int, away_goals: int
    ):
        """Atualização online após resultado real."""
        # Atualizar Elo
        self.elo.update(home_team, away_team, home_goals, away_goals)
        
        # Atualizar Bayesiano
        self.bayesian.online_update(home_team, away_team, home_goals, away_goals)
        
        # Adicionar ao histórico
        import pandas as pd
        new_row = pd.DataFrame([{
            'home_team': home_team,
            'away_team': away_team,
            'home_score': home_goals,
            'away_score': away_goals,
            'match_date': pd.Timestamp.now()
        }])
        
        if self.historical_df is not None:
            self.historical_df = pd.concat(
                [self.historical_df, new_row], ignore_index=True
            )
        
        logger.info(f"Online update: {home_team} {home_goals}-{away_goals} {away_team}")


# =========================================================
# Singleton Global — compartilhado entre scheduler e rotas
# =========================================================
_global_ensemble: Optional['ModelEnsemble'] = None
_global_challenger: Optional['ModelEnsemble'] = None


def _get_global_ensemble() -> Optional['ModelEnsemble']:
    return _global_ensemble


def _set_global_ensemble(ensemble: 'ModelEnsemble', challenger: bool = False):
    global _global_ensemble, _global_challenger
    if challenger:
        _global_challenger = ensemble
        logger.info("Challenger ensemble configurado para A/B test")
    else:
        _global_ensemble = ensemble
        logger.info("Global ensemble atualizado")
