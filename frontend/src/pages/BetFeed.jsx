// EdgeHunter — Live Feed de Value Bets
import { useQuery } from '@tanstack/react-query';
import { BetsAPI, GamesAPI } from '../services/api';
import { useState } from 'react';

const LEAGUES = ['Todas', 'Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1', 'Brasileirão'];
const selectionLabel = { home: '1 Casa', draw: 'X Empate', away: '2 Fora' };
const leagueFlag = {
  'Premier League': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'La Liga': '🇪🇸', 'Bundesliga': '🇩🇪',
  'Serie A': '🇮🇹', 'Ligue 1': '🇫🇷', 'Champions League': '🏆', 'Brasileirão': '🇧🇷'
};

function AlertCard({ bet }) {
  const confidence = ((bet.edge_pct - 3) / 10 * 100).toFixed(0);
  const bars = Math.min(10, Math.round(bet.edge_pct / 1.5));

  return (
    <div className="alert-card fade-in">
      <div className="alert-header">
        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 4 }}>
            {leagueFlag[bet.game?.league] || '⚽'} {bet.game?.league || 'Liga Desconhecida'}
          </div>
          <div className="alert-teams">
            {bet.game?.home_team || '—'} <span style={{ color: 'var(--text-muted)' }}>vs</span> {bet.game?.away_team || '—'}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="alert-edge">+{bet.edge_pct?.toFixed(1)}%</div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>edge</div>
        </div>
      </div>

      <div className="alert-details">
        <div className="alert-detail">
          <div className="alert-detail-label">Seleção</div>
          <div className="alert-detail-value">
            <span className="badge badge-info">{selectionLabel[bet.selection]}</span>
          </div>
        </div>
        <div className="alert-detail">
          <div className="alert-detail-label">Odd</div>
          <div className="alert-detail-value">{bet.odd?.toFixed(2)}</div>
        </div>
        <div className="alert-detail">
          <div className="alert-detail-label">Nossa Prob</div>
          <div className="alert-detail-value">{(bet.our_prob * 100)?.toFixed(1)}%</div>
        </div>
        <div className="alert-detail">
          <div className="alert-detail-label">Prob Implícita</div>
          <div className="alert-detail-value">{(bet.implied_prob * 100)?.toFixed(1)}%</div>
        </div>
        <div className="alert-detail">
          <div className="alert-detail-label">Casa</div>
          <div className="alert-detail-value" style={{ textTransform: 'capitalize' }}>
            {bet.bookmaker}
          </div>
        </div>
        <div className="alert-detail">
          <div className="alert-detail-label">Status</div>
          <div className="alert-detail-value">
            <span className={`badge ${
              bet.result === 'won' ? 'badge-success' :
              bet.result === 'lost' ? 'badge-danger' : 'badge-pending'
            }`}>
              {bet.result === 'won' ? '✅' : bet.result === 'lost' ? '❌' : '⏳'} {bet.result}
            </span>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 12 }}>
        <div style={{ 
          display: 'flex', alignItems: 'center', gap: 6, 
          fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 4 
        }}>
          Força do Edge: {'█'.repeat(bars)}{'░'.repeat(10 - bars)}
        </div>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          📝 Paper Trade • Stake: {bet.stake} u.
          {bet.roi !== null && (
            <span className={bet.roi > 0 ? 'text-success' : 'text-danger'} style={{ marginLeft: 8 }}>
              ROI: {bet.roi > 0 ? '+' : ''}{bet.roi?.toFixed(1)}%
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function BetFeed() {
  const [selectedLeague, setSelectedLeague] = useState('Todas');
  const [resultFilter, setResultFilter] = useState('all');

  const { data: betsData, isLoading, refetch } = useQuery({
    queryKey: ['betsFeed', resultFilter],
    queryFn: () => BetsAPI.getAll({
      result: resultFilter !== 'all' ? resultFilter : undefined,
      limit: 50,
      days: 14
    }),
    refetchInterval: 30000
  });

  const { data: pending } = useQuery({
    queryKey: ['pending'],
    queryFn: BetsAPI.getPending,
    refetchInterval: 30000
  });

  let bets = betsData?.bets || [];

  // Filtro de liga (client-side)
  if (selectedLeague !== 'Todas') {
    bets = bets.filter(b => b.game?.league === selectedLeague);
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">🎯 Live Feed</h1>
          <p className="page-subtitle">Value bets detectados em tempo real • Atualiza a cada 30s</p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span className="badge badge-warning">⏳ {pending?.count ?? 0} pendentes</span>
          <button className="btn btn-ghost" onClick={refetch} style={{ fontSize: '0.8rem', padding: '8px 14px' }}>
            🔄 Atualizar
          </button>
        </div>
      </div>

      {/* Filtros */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {['all', 'pending', 'won', 'lost'].map(r => (
            <button
              key={r}
              className={`btn btn-ghost ${resultFilter === r ? 'btn-outline' : ''}`}
              style={{ fontSize: '0.78rem', padding: '7px 14px' }}
              onClick={() => setResultFilter(r)}
            >
              {r === 'all' ? '🌐 Todas' :
               r === 'pending' ? '⏳ Pendentes' :
               r === 'won' ? '✅ Ganhas' : '❌ Perdidas'}
            </button>
          ))}
        </div>
        
        <div style={{ display: 'flex', gap: 8, marginLeft: 'auto', flexWrap: 'wrap' }}>
          {LEAGUES.map(league => (
            <button
              key={league}
              className={`btn btn-ghost ${selectedLeague === league ? 'btn-outline' : ''}`}
              style={{ fontSize: '0.78rem', padding: '7px 12px' }}
              onClick={() => setSelectedLeague(league)}
            >
              {leagueFlag[league] || '🌐'} {league}
            </button>
          ))}
        </div>
      </div>

      {/* Feed */}
      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[...Array(5)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 140, borderRadius: 'var(--radius-lg)' }} />
          ))}
        </div>
      ) : bets.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">🎯</div>
            <div className="empty-state-text">
              Nenhuma aposta encontrada com os filtros atuais.<br />
              <span style={{ fontSize: '0.8rem', marginTop: 4, display: 'block' }}>
                Configure as APIs no .env para começar a detectar value bets.
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {bets.map(bet => (
            <AlertCard key={bet.id} bet={bet} />
          ))}
        </div>
      )}
    </div>
  );
}
