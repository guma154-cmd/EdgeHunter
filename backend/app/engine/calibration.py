"""
EdgeHunter — Calibração de Probabilidades (Platt Scaling)
Converte scores dos modelos em probabilidades reais e bem calibradas.
Calcula Brier Score e ECE (Expected Calibration Error).
"""
import numpy as np
from typing import Tuple, List, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import calibration_curve
import logging

logger = logging.getLogger(__name__)


def brier_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Brier Score = MSE das probabilidades preditas.
    Range: [0, 1]. Menor = melhor.
    Referência: bookmaker típico ≈ 0.26-0.28 (com overround)
    """
    return float(np.mean((y_pred - y_true) ** 2))


def ece_score(y_true: np.ndarray, y_pred: np.ndarray, n_bins: int = 10) -> float:
    """
    Expected Calibration Error (ECE).
    Mede o quão bem calibradas estão as probabilidades.
    ECE = 0 significa calibração perfeita.
    """
    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    
    for i in range(n_bins):
        mask = (y_pred >= bin_edges[i]) & (y_pred < bin_edges[i + 1])
        if mask.sum() == 0:
            continue
        
        bin_accuracy = y_true[mask].mean()
        bin_confidence = y_pred[mask].mean()
        bin_weight = mask.sum() / len(y_true)
        
        ece += bin_weight * abs(bin_confidence - bin_accuracy)
    
    return float(ece)


class PlattCalibration:
    """
    Platt Scaling para calibração de probabilidades.
    
    Treina um modelo logístico para transformar as probabilidades
    brutas do ensemble em probabilidades reais e calibradas.
    """
    
    def __init__(self):
        self.calibrators = {
            'home': LogisticRegression(),
            'draw': LogisticRegression(),
            'away': LogisticRegression()
        }
        self.is_fitted = False
        self._calibration_data = {
            'pred': [],
            'true': []
        }
    
    def fit(
        self,
        predicted_probs: List[Tuple[float, float, float]],
        actual_outcomes: List[str]  # 'home', 'draw', 'away'
    ) -> 'PlattCalibration':
        """
        Treina os calibradores Platt Scaling.
        
        Args:
            predicted_probs: Lista de (prob_home, prob_draw, prob_away)
            actual_outcomes: Resultados reais para cada jogo
        """
        if len(predicted_probs) < 30:
            logger.warning("Dados insuficientes para calibração Platt. Mín: 30 jogos")
            return self
        
        X = np.array(predicted_probs)
        
        outcomes = {
            'home': np.array([1 if o == 'home' else 0 for o in actual_outcomes]),
            'draw': np.array([1 if o == 'draw' else 0 for o in actual_outcomes]),
            'away': np.array([1 if o == 'away' else 0 for o in actual_outcomes])
        }
        
        for outcome, calibrator in self.calibrators.items():
            y = outcomes[outcome]
            if y.sum() > 3:  # Precisa de pelo menos 3 positivos
                calibrator.fit(X, y)
        
        self.is_fitted = True
        logger.info(f"Platt Scaling calibrado com {len(predicted_probs)} amostras")
        return self
    
    def transform(
        self, probs: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """
        Calibra um conjunto de probabilidades.
        Se não treinado, retorna as probabilidades originais.
        """
        if not self.is_fitted:
            return probs
        
        X = np.array([probs])
        
        try:
            cal_home = self.calibrators['home'].predict_proba(X)[0][1]
            cal_draw = self.calibrators['draw'].predict_proba(X)[0][1]
            cal_away = self.calibrators['away'].predict_proba(X)[0][1]
            
            # Normalizar para somar 1
            total = cal_home + cal_draw + cal_away
            if total == 0:
                return probs
            
            return cal_home / total, cal_draw / total, cal_away / total
        except Exception:
            return probs
    
    def evaluate(
        self,
        predicted_probs: List[Tuple[float, float, float]],
        actual_outcomes: List[str]
    ) -> Dict:
        """
        Avalia a qualidade de calibração com Brier Score e ECE.
        """
        if not predicted_probs:
            return {}
        
        X = np.array(predicted_probs)
        
        # Outcome one-hot
        y_home = np.array([1 if o == 'home' else 0 for o in actual_outcomes])
        y_draw = np.array([1 if o == 'draw' else 0 for o in actual_outcomes])
        y_away = np.array([1 if o == 'away' else 0 for o in actual_outcomes])
        
        return {
            'brier_home': brier_score(y_home, X[:, 0]),
            'brier_draw': brier_score(y_draw, X[:, 1]),
            'brier_away': brier_score(y_away, X[:, 2]),
            'brier_avg': (
                brier_score(y_home, X[:, 0]) +
                brier_score(y_draw, X[:, 1]) +
                brier_score(y_away, X[:, 2])
            ) / 3,
            'ece_home': ece_score(y_home, X[:, 0]),
            'ece_draw': ece_score(y_draw, X[:, 1]),
            'ece_away': ece_score(y_away, X[:, 2]),
            'n_samples': len(predicted_probs)
        }


# Importação para evitar erro no ensemble.py
from typing import Dict
