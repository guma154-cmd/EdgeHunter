"""
EdgeHunter — Value Detector
Detecta apostas com edge positivo comparando nossas probabilidades
com as odds da Pinnacle (sharp line) e casas soft.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def implied_probability(odd: float, margin_removed: bool = False) -> float:
    """
    Converte odd decimal em probabilidade implícita.
    
    Args:
        odd: Odd decimal (ex: 2.10)
        margin_removed: Se True, remove o overround da casa
    """
    if odd <= 1.0:
        return 1.0
    return 1.0 / odd


def remove_overround(
    home_odd: float, draw_odd: float, away_odd: float
) -> Tuple[float, float, float]:
    """
    Remove o overround das odds para obter probabilidades justas.
    Usa o método Shin para distribuição proporcional.
    """
    implied_h = 1 / home_odd
    implied_d = 1 / draw_odd
    implied_a = 1 / away_odd
    
    total = implied_h + implied_d + implied_a
    
    # Normalizar (remove overround igualmente)
    return implied_h / total, implied_d / total, implied_a / total


def calculate_edge(our_prob: float, odd: float) -> float:
    """
    Edge = (nossa probabilidade × odd) - 1
    
    Edge positivo = apostamos com vantagem.
    Edge de 3% = esperamos ganhar 3 centavos por real apostado.
    """
    return (our_prob * odd) - 1.0


def kelly_fraction(our_prob: float, odd: float, fraction: float = 0.25) -> float:
    """
    Critério de Kelly Fracionado para dimensionamento de posição.
    Usamos 25% do Kelly completo (mais conservador).
    
    Args:
        our_prob: Nossa probabilidade estimada
        odd: Odd decimal disponível
        fraction: Fração do Kelly (0.25 = quarter Kelly)
    
    Returns:
        Percentual do bankroll para apostar
    """
    b = odd - 1
    q = 1 - our_prob
    kelly = (b * our_prob - q) / b
    
    return max(0, kelly * fraction)


class ValueDetector:
    """
    Detector de value bets com referência na Pinnacle (sharp line).
    
    Lógica:
    1. Converte odds Pinnacle em probabilidades justas (sem overround)
    2. Compara com nossas probabilidades calibradas
    3. Verifica se a odd nas casas soft supera nosso threshold
    4. Calcula edge, Kelly e score de confiança
    """
    
    def __init__(self, min_edge_pct: float = 3.0):
        """
        Args:
            min_edge_pct: Edge mínimo para gerar alerta (%)
        """
        self.min_edge_pct = min_edge_pct / 100.0
    
    def analyze(
        self,
        home_team: str,
        away_team: str,
        our_probs: Dict[str, float],      # {'home': 0.55, 'draw': 0.22, 'away': 0.23}
        pinnacle_odds: Dict[str, float],  # {'home': 2.10, 'draw': 3.50, 'away': 4.20}
        soft_odds: Dict[str, Dict],       # {'bet365': {'home': 2.15, ...}, ...}
    ) -> List[Dict]:
        """
        Analisa todas as oportunidades de value para um jogo.
        
        Returns:
            Lista de apostas com edge detectado, ordenadas por edge
        """
        opportunities = []
        
        # Probabilidades da Pinnacle sem overround (fair odds)
        if all(k in pinnacle_odds for k in ['home', 'draw', 'away']):
            pin_fair = remove_overround(
                pinnacle_odds['home'],
                pinnacle_odds['draw'],
                pinnacle_odds['away']
            )
            pinnacle_fair = {'home': pin_fair[0], 'draw': pin_fair[1], 'away': pin_fair[2]}
        else:
            pinnacle_fair = None
        
        # Para cada mercado 1X2
        for selection in ['home', 'draw', 'away']:
            our_p = our_probs.get(selection)
            if our_p is None:
                continue
            
            # Para cada casa soft
            for bookmaker, book_odds in soft_odds.items():
                odd = book_odds.get(selection)
                if odd is None or odd <= 1.0:
                    continue
                
                edge = calculate_edge(our_p, odd)
                edge_pct = edge * 100
                
                if edge >= self.min_edge_pct:
                    implied_p = implied_probability(odd)
                    kelly = kelly_fraction(our_p, odd)
                    
                    # Verificação adicional: nossa prob > Pinnacle fair?
                    pinnacle_p = pinnacle_fair.get(selection) if pinnacle_fair else None
                    has_edge_vs_pinnacle = (
                        pinnacle_p is not None and our_p > pinnacle_p
                    )
                    
                    # Score de confiança (0-100)
                    confidence = self._calculate_confidence(
                        edge_pct, our_p, implied_p, pinnacle_p
                    )
                    
                    opportunities.append({
                        'home_team': home_team,
                        'away_team': away_team,
                        'market': '1X2',
                        'selection': selection,
                        'bookmaker': bookmaker,
                        'odd': odd,
                        'our_prob': round(our_p, 4),
                        'implied_prob': round(implied_p, 4),
                        'pinnacle_fair_prob': round(pinnacle_p, 4) if pinnacle_p else None,
                        'edge_pct': round(edge_pct, 2),
                        'kelly_fraction': round(kelly, 4),
                        'confidence': round(confidence, 1),
                        'has_edge_vs_pinnacle': has_edge_vs_pinnacle
                    })
        
        # Ordenar por edge (maior primeiro)
        opportunities.sort(key=lambda x: x['edge_pct'], reverse=True)
        return opportunities
    
    def _calculate_confidence(
        self,
        edge_pct: float,
        our_prob: float,
        implied_prob: float,
        pinnacle_prob: Optional[float]
    ) -> float:
        """
        Score de confiança baseado em múltiplos fatores.
        Range: 0-100.
        """
        score = 0.0
        
        # Fator 1: Tamanho do edge (max 40 pts)
        score += min(40, edge_pct * 4)
        
        # Fator 2: Nossa prob vs Pinnacle (max 30 pts)
        if pinnacle_prob:
            diff = our_prob - pinnacle_prob
            score += min(30, diff * 300)
        else:
            score += 15  # Neutro se não temos Pinnacle
        
        # Fator 3: Odd não muito extrema (max 20 pts)
        # Odds muito altas têm variância enorme
        if 1.5 <= 1 / our_prob <= 5.0:
            score += 20
        elif 1.5 <= 1 / our_prob <= 10.0:
            score += 10
        
        # Fator 4: Edge vs implied prob (max 10 pts)
        score += min(10, (our_prob - implied_prob) * 100)
        
        return min(100, max(0, score))


class CLVTracker:
    """
    Rastreador de Closing Line Value.
    
    CLV positivo = apostamos antes que a linha se movesse contra nós.
    É o melhor indicador de skill a longo prazo.
    
    CLV = (odd_nossa / odd_fechamento) - 1
    """
    
    def __init__(self):
        self.clv_history: List[float] = []
    
    def calculate_clv(self, bet_odd: float, closing_odd: float) -> float:
        """
        Calcula o CLV de uma aposta específica.
        
        Args:
            bet_odd: Odd no momento da aposta
            closing_odd: Odd no fechamento do mercado
        
        Returns:
            CLV em % (positivo = bom)
        """
        if closing_odd <= 1.0:
            return 0.0
        
        clv = ((bet_odd / closing_odd) - 1) * 100
        self.clv_history.append(clv)
        return clv
    
    def calculate_sharpe_ratio(self, returns: List[float], window: int = 30) -> float:
        """
        Sharpe Ratio das apostas recentes.
        
        Args:
            returns: ROI de cada aposta (em %)
            window: Janela em número de apostas
        
        Returns:
            Sharpe Ratio (>0.5 = bom, >1.0 = excelente)
        """
        if len(returns) < 5:
            return 0.0
        
        recent = returns[-window:] if len(returns) > window else returns
        
        mean_return = np.mean(recent)
        std_return = np.std(recent)
        
        if std_return == 0:
            return 0.0
        
        return mean_return / std_return
    
    def get_clv_summary(self) -> Dict:
        """Resumo das métricas de CLV."""
        if not self.clv_history:
            return {'avg_clv': 0, 'positive_rate': 0, 'total': 0}
        
        return {
            'avg_clv': round(np.mean(self.clv_history), 3),
            'median_clv': round(np.median(self.clv_history), 3),
            'positive_rate': sum(c > 0 for c in self.clv_history) / len(self.clv_history),
            'total': len(self.clv_history),
            'last_10_avg': round(np.mean(self.clv_history[-10:]), 3) if len(self.clv_history) >= 10 else None
        }
