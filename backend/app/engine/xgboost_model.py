"""
EdgeHunter — XGBoost Model para Previsão de Futebol
Features temporais, históricas e de forma recente.
"""
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Optional, List
import joblib
import os
import logging

logger = logging.getLogger(__name__)

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    logger.warning("XGBoost não instalado. Instale com: pip install xgboost")


class XGBoostModel:
    """
    XGBoost para previsão de futebol.
    
    Features utilizadas:
    - Elo ratings dos dois times
    - Forma recente (últimos 5 jogos)
    - Média de gols marcados/sofridos (rolling)
    - Diferença de posição na tabela
    - Head-to-head histórico
    - Dias desde o último jogo (fadiga)
    - Força do adversário médio recente
    """
    
    MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'xgboost_model.pkl')
    
    def __init__(self):
        self.model_home = None
        self.model_draw = None  
        self.model_away = None
        self.feature_names: List[str] = []
        self.is_fitted = False
    
    def _build_features(self, df: pd.DataFrame, elo_ratings: Dict) -> pd.DataFrame:
        """
        Constrói feature matrix a partir dos dados de jogos.
        """
        features = []
        
        for _, row in df.iterrows():
            home = row['home_team']
            away = row['away_team']
            match_date = pd.Timestamp(row['match_date'])
            
            # Jogos anteriores a esta data
            past = df[df['match_date'] < row['match_date']].copy()
            
            feat = {}
            
            # --- Elo Ratings ---
            feat['elo_home'] = elo_ratings.get(home, 1500)
            feat['elo_away'] = elo_ratings.get(away, 1500)
            feat['elo_diff'] = feat['elo_home'] - feat['elo_away']
            
            # --- Forma recente (últimos 5 jogos) ---
            for team, prefix, is_home in [(home, 'home', True), (away, 'away', False)]:
                team_games = past[
                    (past['home_team'] == team) | (past['away_team'] == team)
                ].tail(5)
                
                if len(team_games) == 0:
                    feat[f'{prefix}_form_pts'] = 1.5  # Média neutra
                    feat[f'{prefix}_goals_scored_avg'] = 1.5
                    feat[f'{prefix}_goals_conceded_avg'] = 1.5
                    feat[f'{prefix}_win_rate'] = 0.4
                    feat[f'{prefix}_days_rest'] = 7
                else:
                    pts = []
                    goals_scored = []
                    goals_conceded = []
                    
                    for _, g in team_games.iterrows():
                        if g['home_team'] == team:
                            gs, gc = g['home_score'], g['away_score']
                            hs = True
                        else:
                            gs, gc = g['away_score'], g['home_score']
                            hs = False
                        
                        goals_scored.append(gs if not pd.isna(gs) else 1)
                        goals_conceded.append(gc if not pd.isna(gc) else 1)
                        
                        if gs > gc:
                            pts.append(3)
                        elif gs == gc:
                            pts.append(1)
                        else:
                            pts.append(0)
                    
                    feat[f'{prefix}_form_pts'] = np.mean(pts)
                    feat[f'{prefix}_goals_scored_avg'] = np.mean(goals_scored)
                    feat[f'{prefix}_goals_conceded_avg'] = np.mean(goals_conceded)
                    feat[f'{prefix}_win_rate'] = sum(p == 3 for p in pts) / len(pts)
                    
                    # Dias de descanso
                    last_game = team_games['match_date'].max()
                    days_rest = (match_date - pd.Timestamp(last_game)).days
                    feat[f'{prefix}_days_rest'] = min(days_rest, 30)
            
            # --- Head-to-Head ---
            h2h = past[
                ((past['home_team'] == home) & (past['away_team'] == away)) |
                ((past['home_team'] == away) & (past['away_team'] == home))
            ].tail(10)
            
            if len(h2h) == 0:
                feat['h2h_home_win_rate'] = 0.4
                feat['h2h_total_goals_avg'] = 2.6
            else:
                home_wins = sum(
                    1 for _, g in h2h.iterrows()
                    if (g['home_team'] == home and g['home_score'] > g['away_score']) or
                       (g['away_team'] == home and g['away_score'] > g['home_score'])
                )
                feat['h2h_home_win_rate'] = home_wins / len(h2h)
                feat['h2h_total_goals_avg'] = (
                    (h2h['home_score'].fillna(0) + h2h['away_score'].fillna(0)).mean()
                )
            
            # --- Diferencial de gols esperados ---
            feat['xg_diff'] = (
                feat['home_goals_scored_avg'] - feat['home_goals_conceded_avg'] -
                feat['away_goals_scored_avg'] + feat['away_goals_conceded_avg']
            )
            
            features.append(feat)
        
        return pd.DataFrame(features)
    
    def fit(self, matches_df: pd.DataFrame, elo_ratings: Dict) -> 'XGBoostModel':
        """
        Treina os 3 classificadores (home/draw/away).
        """
        if not HAS_XGBOOST:
            logger.error("XGBoost não disponível")
            return self
        
        df = matches_df.dropna(subset=['home_score', 'away_score']).copy()
        
        if len(df) < 100:
            logger.warning(f"Apenas {len(df)} jogos. XGBoost precisa de mais dados.")
            return self
        
        X = self._build_features(df, elo_ratings)
        self.feature_names = X.columns.tolist()
        
        # Labels binários para cada outcome
        y_home = (df['home_score'] > df['away_score']).astype(int).values
        y_draw = (df['home_score'] == df['away_score']).astype(int).values
        y_away = (df['home_score'] < df['away_score']).astype(int).values
        
        params = {
            'n_estimators': 200,
            'max_depth': 5,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'use_label_encoder': False,
            'eval_metric': 'logloss',
            'random_state': 42
        }
        
        self.model_home = xgb.XGBClassifier(**params)
        self.model_draw = xgb.XGBClassifier(**params)
        self.model_away = xgb.XGBClassifier(**params)
        
        self.model_home.fit(X, y_home)
        self.model_draw.fit(X, y_draw)
        self.model_away.fit(X, y_away)
        
        self.is_fitted = True
        logger.info(f"XGBoost treinado com {len(df)} jogos e {len(self.feature_names)} features")
        return self
    
    def predict_1x2(
        self,
        home_team: str,
        away_team: str,
        elo_ratings: Dict,
        match_date: str,
        historical_df: pd.DataFrame
    ) -> Tuple[float, float, float]:
        """
        Retorna probabilidades 1X2.
        """
        if not self.is_fitted or not HAS_XGBOOST:
            return 0.45, 0.27, 0.28  # Fallback: média histórica do futebol
        
        # Criar row sintético para este jogo
        game_row = pd.DataFrame([{
            'home_team': home_team,
            'away_team': away_team,
            'match_date': match_date,
            'home_score': np.nan,
            'away_score': np.nan
        }])
        
        full_df = pd.concat([historical_df, game_row], ignore_index=True)
        X = self._build_features(full_df, elo_ratings)
        X_pred = X.tail(1)[self.feature_names]
        
        prob_home = self.model_home.predict_proba(X_pred)[0][1]
        prob_draw = self.model_draw.predict_proba(X_pred)[0][1]
        prob_away = self.model_away.predict_proba(X_pred)[0][1]
        
        # Normalizar
        total = prob_home + prob_draw + prob_away
        if total == 0:
            return 0.45, 0.27, 0.28
        
        return prob_home / total, prob_draw / total, prob_away / total
    
    def save(self, path: str = None):
        """Salva o modelo em disco."""
        save_path = path or self.MODEL_PATH
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump({
            'model_home': self.model_home,
            'model_draw': self.model_draw,
            'model_away': self.model_away,
            'feature_names': self.feature_names
        }, save_path)
        logger.info(f"XGBoost salvo em: {save_path}")
    
    def load(self, path: str = None) -> 'XGBoostModel':
        """Carrega o modelo do disco."""
        load_path = path or self.MODEL_PATH
        if os.path.exists(load_path):
            data = joblib.load(load_path)
            self.model_home = data['model_home']
            self.model_draw = data['model_draw']
            self.model_away = data['model_away']
            self.feature_names = data['feature_names']
            self.is_fitted = True
            logger.info("XGBoost carregado do disco")
        return self
