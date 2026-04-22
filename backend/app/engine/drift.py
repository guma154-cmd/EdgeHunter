"""
EdgeHunter — Concept Drift Detection
Detecta mudanças estruturais no mercado de apostas.
Implementa DDM (Drift Detection Method) e monitoramento de Brier Score.
"""
import numpy as np
from typing import List, Dict, Optional, Tuple
from collections import deque
import logging

logger = logging.getLogger(__name__)


class DDMDriftDetector:
    """
    Drift Detection Method (DDM) de Gama et al. (2004).
    
    Monitora a taxa de erro do modelo ao longo do tempo.
    Detecta dois níveis de alerta:
    - WARNING: performance piorando, mas ainda dentro do limite
    - DRIFT: mudança estrutural confirmada → retraining obrigatório
    """
    
    WARNING_LEVEL = 2.0   # Desvios padrão para warning
    DRIFT_LEVEL = 3.0     # Desvios padrão para drift confirmado
    MIN_INSTANCES = 30    # Mínimo de amostras antes de detectar
    
    def __init__(self):
        self.n = 0
        self.p = 1.0      # Taxa de erro atual
        self.s = 0.0      # Desvio padrão atual
        
        self.p_min = 1.0  # Melhor taxa de erro observada
        self.s_min = 0.0  # Desvio padrão na melhor taxa
        
        self.warning_detected = False
        self.drift_detected = False
        self.drift_events: List[int] = []
    
    def update(self, error: float) -> str:
        """
        Atualiza o detector com novo erro (0 = correto, 1 = errado).
        
        Args:
            error: Erro binário (0 ou 1) ou contínuo [0, 1]
        
        Returns:
            'normal', 'warning', ou 'drift'
        """
        self.n += 1
        
        # Atualizar média e desvio (estimação online)
        self.p = self.p + (error - self.p) / self.n
        self.s = np.sqrt(self.p * (1 - self.p) / self.n)
        
        if self.n < self.MIN_INSTANCES:
            return 'normal'
        
        # Atualizar mínimos
        if self.p + self.s <= self.p_min + self.s_min:
            self.p_min = self.p
            self.s_min = self.s
        
        self.drift_detected = False
        self.warning_detected = False
        
        # Verificar drift
        threshold = self.p_min + self.s_min
        current = self.p + self.s
        
        if current >= threshold + self.DRIFT_LEVEL * self.s_min:
            self.drift_detected = True
            self.drift_events.append(self.n)
            logger.warning(f"🚨 DRIFT DETECTADO em instância {self.n}! p={self.p:.4f}")
            self._reset()
            return 'drift'
        elif current >= threshold + self.WARNING_LEVEL * self.s_min:
            self.warning_detected = True
            logger.info(f"⚠️ Warning de drift em instância {self.n}. p={self.p:.4f}")
            return 'warning'
        
        return 'normal'
    
    def _reset(self):
        """Reset após drift detectado."""
        self.n = 0
        self.p = 1.0
        self.s = 0.0
        self.p_min = 1.0
        self.s_min = 0.0


class BrierDriftDetector:
    """
    Detector de drift baseado em Brier Score.
    Usa CUSUM (Cumulative Sum) para detectar deterioração contínua.
    """
    
    def __init__(self, threshold: float = 0.05, window: int = 20):
        """
        Args:
            threshold: Aumento máximo tolerado no Brier Score
            window: Janela para média móvel
        """
        self.threshold = threshold
        self.window = window
        self.brier_history: deque = deque(maxlen=200)
        self.baseline_brier: Optional[float] = None
    
    def update(self, brier_score: float) -> str:
        """
        Adiciona novo Brier Score e verifica drift.
        
        Returns:
            'normal', 'warning', ou 'drift'
        """
        self.brier_history.append(brier_score)
        
        if len(self.brier_history) < self.window * 2:
            return 'normal'
        
        # Baseline: média dos primeiros N scores
        baseline_data = list(self.brier_history)[:self.window]
        self.baseline_brier = np.mean(baseline_data)
        
        # Recente
        recent_data = list(self.brier_history)[-self.window:]
        recent_brier = np.mean(recent_data)
        
        delta = recent_brier - self.baseline_brier
        
        if delta > self.threshold * 1.5:
            logger.warning(f"🚨 Drift Brier: baseline={self.baseline_brier:.4f}, recente={recent_brier:.4f}")
            return 'drift'
        elif delta > self.threshold * 0.7:
            logger.info(f"⚠️ Warning Brier: delta={delta:.4f}")
            return 'warning'
        
        return 'normal'
    
    def get_trend(self) -> Dict:
        """Retorna tendência do Brier Score."""
        if len(self.brier_history) < 5:
            return {'trend': 'insufficient_data'}
        
        history = list(self.brier_history)
        recent = np.mean(history[-10:]) if len(history) >= 10 else np.mean(history)
        historical = np.mean(history)
        
        return {
            'current_brier': recent,
            'historical_avg': historical,
            'delta': recent - historical,
            'baseline': self.baseline_brier,
            'drift_threshold': self.threshold
        }


class MarketDriftDetector:
    """
    Detector de drift no mercado de apostas.
    Monitora:
    - Variação nos overrounds das casas
    - CLV trending negativo
    - Edge médio em declínio
    """
    
    def __init__(self):
        self.overround_history: deque = deque(maxlen=100)
        self.clv_history: deque = deque(maxlen=100)
        self.edge_history: deque = deque(maxlen=100)
        
        self.ddm = DDMDriftDetector()
        self.brier_detector = BrierDriftDetector()
    
    def update(
        self,
        overround: Optional[float] = None,
        clv: Optional[float] = None,
        edge: Optional[float] = None,
        brier: Optional[float] = None,
        prediction_error: Optional[float] = None
    ) -> Dict[str, str]:
        """
        Atualiza todos os detectores e retorna status.
        """
        results = {}
        
        if overround is not None:
            self.overround_history.append(overround)
        
        if clv is not None:
            self.clv_history.append(clv)
        
        if edge is not None:
            self.edge_history.append(edge)
        
        if brier is not None:
            results['brier_drift'] = self.brier_detector.update(brier)
        
        if prediction_error is not None:
            results['ddm_drift'] = self.ddm.update(prediction_error)
        
        # Status geral
        has_drift = any(v == 'drift' for v in results.values())
        has_warning = any(v == 'warning' for v in results.values())
        
        if has_drift:
            results['overall'] = 'drift'
        elif has_warning:
            results['overall'] = 'warning'
        else:
            results['overall'] = 'normal'
        
        return results
    
    def get_summary(self) -> Dict:
        """Resumo completo do estado de drift."""
        brier_trend = self.brier_detector.get_trend()
        
        clv_avg = np.mean(list(self.clv_history)) if self.clv_history else None
        edge_avg = np.mean(list(self.edge_history)) if self.edge_history else None
        
        return {
            'brier_trend': brier_trend,
            'clv_avg_recent': round(clv_avg, 3) if clv_avg else None,
            'edge_avg_recent': round(edge_avg, 3) if edge_avg else None,
            'drift_events': self.ddm.drift_events[-5:],  # últimos 5
            'warning_active': self.ddm.warning_detected
        }


# =========================================================
# Singleton Global
# =========================================================
_global_drift_detector: Optional[MarketDriftDetector] = None


def _get_global_drift_detector() -> Optional[MarketDriftDetector]:
    global _global_drift_detector
    if _global_drift_detector is None:
        _global_drift_detector = MarketDriftDetector()
    return _global_drift_detector
