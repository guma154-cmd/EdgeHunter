// EdgeHunter — Analytics Page
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts';
import { AnalyticsAPI } from '../services/api';

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <div className="label">{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="value" style={{ color: p.color }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(2) : p.value}
        </div>
      ))}
    </div>
  );
}

export default function Analytics() {
  const [days, setDays] = useState(30);

  const { data: overview } = useQuery({
    queryKey: ['overview', days],
    queryFn: () => AnalyticsAPI.getOverview(days)
  });

  const { data: roiByLeague } = useQuery({
    queryKey: ['roiByLeague', days],
    queryFn: () => AnalyticsAPI.getROIByLeague(days)
  });

  const { data: edgeDist } = useQuery({
    queryKey: ['edgeDist'],
    queryFn: AnalyticsAPI.getEdgeDistribution
  });

  const leagueData = roiByLeague?.by_league || [];
  const edgeData = edgeDist?.distribution || [];
  const perf = overview?.performance || {};
  const summary = overview?.summary || {};

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">📊 Analytics</h1>
          <p className="page-subtitle">Performance detalhada por liga, mercado e período</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {[7, 14, 30, 60, 90].map(d => (
            <button
              key={d}
              className={`btn btn-ghost ${days === d ? 'btn-outline' : ''}`}
              style={{ fontSize: '0.8rem', padding: '8px 14px' }}
              onClick={() => setDays(d)}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="metric-grid" style={{ marginBottom: 24 }}>
        {[
          { label: 'Total Apostas', value: summary.total_bets ?? 0, icon: '💼', fmt: v => v, color: 'neutral' },
          { label: 'Lucro Total (u.)', value: perf.total_profit_units ?? 0, icon: '💰', fmt: v => `${v >= 0 ? '+' : ''}${v?.toFixed(2)}`, color: perf.total_profit_units >= 0 ? 'positive' : 'negative' },
          { label: 'Win Rate', value: summary.win_rate ?? 0, icon: '🎯', fmt: v => `${v?.toFixed(1)}%`, color: summary.win_rate >= 50 ? 'positive' : 'neutral' },
          { label: 'Sharpe Ratio', value: perf.sharpe_ratio ?? 0, icon: '📊', fmt: v => v?.toFixed(3), color: perf.sharpe_ratio >= 0.5 ? 'positive' : 'neutral' },
        ].map((m, i) => (
          <div key={i} className="metric-card fade-in">
            <div className="metric-icon">{m.icon}</div>
            <div className="metric-label">{m.label}</div>
            <div className={`metric-value ${m.color}`}>{m.fmt(m.value)}</div>
            <div className="metric-sub">últimos {days} dias</div>
          </div>
        ))}
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* ROI por Liga */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">🏆 ROI por Liga</div>
            <span className="badge badge-info">{leagueData.length} ligas</span>
          </div>
          {leagueData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={leagueData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#475569', fontSize: 11 }} axisLine={false} tickLine={false} unit="%" />
                <YAxis dataKey="league" type="category" width={120} tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="roi" name="ROI" radius={[0, 4, 4, 0]}>
                  {leagueData.map((entry, i) => (
                    <Cell key={i} fill={entry.roi >= 0 ? '#10b981' : '#ef4444'} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">🏆</div>
              <div className="empty-state-text">Sem dados de liga ainda</div>
            </div>
          )}
        </div>

        {/* Edge Distribution */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">⚡ Edge × ROI</div>
            <span className="badge badge-purple">por faixa</span>
          </div>
          {edgeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={edgeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="range" tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Apostas" radius={[4,4,0,0]} fill="#00d4ff" fillOpacity={0.7} />
                <Bar dataKey="avg_roi" name="ROI Médio%" radius={[4,4,0,0]} fill="#7c3aed" fillOpacity={0.7} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">⚡</div>
              <div className="empty-state-text">Aguardando dados de edge</div>
            </div>
          )}
        </div>
      </div>

      {/* CLV Analysis */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">🎯 Closing Line Value (CLV)</div>
          <span className="badge badge-success">CLV {'>'} 0 = Skill confirmado</span>
        </div>
        <div className="grid-2">
          <div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 16 }}>
              O <strong style={{ color: 'var(--brand-primary)' }}>CLV</strong> mede se você apostou 
              antes da linha da casa se mover contra você. É o melhor indicador de{' '}
              <strong style={{ color: 'var(--brand-accent)' }}>skill real</strong> em apostas, 
              independente dos resultados de curto prazo.
            </p>
            {[
              ['CLV Médio (período)', perf.clv_avg, '%'],
              ['Sharpe Ratio', perf.sharpe_ratio, ''],
              ['ROI por Aposta', perf.roi_avg_per_bet, '%'],
              ['Edge Médio Detectado', perf.avg_edge_detected, '%'],
            ].map(([label, val, suffix], i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{label}</span>
                <span className={`mono ${val > 0 ? 'text-success' : val < 0 ? 'text-danger' : 'text-brand'}`} style={{ fontWeight: 700 }}>
                  {val !== null && val !== undefined ? `${val >= 0 ? '+' : ''}${val?.toFixed(3)}${suffix}` : '—'}
                </span>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
            <div style={{ 
              fontSize: '4rem', fontWeight: 800, fontFamily: 'var(--font-mono)',
              background: 'var(--grad-primary)', WebkitBackgroundClip: 'text', 
              WebkitTextFillColor: 'transparent', backgroundClip: 'text'
            }}>
              {(perf.clv_avg >= 0 ? '+' : '')}{(perf.clv_avg || 0).toFixed(2)}%
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 8 }}>
              CLV Médio • {days}d
            </div>
            <div style={{ marginTop: 20 }}>
              {(perf.clv_avg || 0) > 1 ? (
                <span className="badge badge-success">Edge confirmado</span>
              ) : (
                <span className="badge badge-pending">Aguardando dados</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
