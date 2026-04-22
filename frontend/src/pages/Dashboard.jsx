// EdgeHunter — Dashboard Principal
import { useQuery } from '@tanstack/react-query';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Cell
} from 'recharts';
import { AnalyticsAPI, BetsAPI } from '../services/api';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

function MetricCard({ label, value, sub, icon, colorClass = 'neutral', prefix = '' }) {
  return (
    <div className="metric-card fade-in">
      <div className="metric-icon">{icon}</div>
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${colorClass}`}>
        {prefix}{typeof value === 'number' ? value.toFixed(2) : value}
      </div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

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

function RecentBets({ bets }) {
  const selectionLabel = { home: '1 Casa', draw: 'X Empate', away: '2 Fora' };
  
  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Jogo</th>
            <th>Seleção</th>
            <th>Odd</th>
            <th>Edge</th>
            <th>Casa</th>
            <th>Status</th>
            <th>ROI</th>
          </tr>
        </thead>
        <tbody>
          {bets?.slice(0, 10).map(bet => (
            <tr key={bet.id}>
              <td>
                <span style={{ fontSize: '0.85rem' }}>
                  {bet.game?.home_team || '—'} vs {bet.game?.away_team || '—'}
                </span>
              </td>
              <td>
                <span className="badge badge-info">
                  {selectionLabel[bet.selection] || bet.selection}
                </span>
              </td>
              <td className="mono">{bet.odd?.toFixed(2)}</td>
              <td>
                <div className="edge-bar">
                  <div className="edge-bar-track">
                    <div
                      className="edge-bar-fill"
                      style={{ width: `${Math.min(bet.edge_pct * 7, 100)}%` }}
                    />
                  </div>
                  <span className="mono text-brand" style={{ fontSize: '0.8rem', width: 40 }}>
                    +{bet.edge_pct?.toFixed(1)}%
                  </span>
                </div>
              </td>
              <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                {bet.bookmaker}
              </td>
              <td>
                <span className={`badge ${
                  bet.result === 'won' ? 'badge-success' :
                  bet.result === 'lost' ? 'badge-danger' : 'badge-pending'
                }`}>
                  {bet.result === 'won' ? '✅ Ganhou' :
                   bet.result === 'lost' ? '❌ Perdeu' : '⏳ Pendente'}
                </span>
              </td>
              <td className={`mono ${bet.roi > 0 ? 'text-success' : bet.roi < 0 ? 'text-danger' : ''}`}>
                {bet.roi !== null ? `${bet.roi > 0 ? '+' : ''}${bet.roi?.toFixed(1)}%` : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Dashboard() {
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['overview', 30],
    queryFn: () => AnalyticsAPI.getOverview(30)
  });

  const { data: timeline } = useQuery({
    queryKey: ['timeline', 30],
    queryFn: () => AnalyticsAPI.getROITimeline(30)
  });

  const { data: betsData } = useQuery({
    queryKey: ['bets'],
    queryFn: () => BetsAPI.getAll({ limit: 10 })
  });

  const { data: edgeDist } = useQuery({
    queryKey: ['edgeDist'],
    queryFn: AnalyticsAPI.getEdgeDistribution
  });

  const perf = overview?.performance || {};
  const summary = overview?.summary || {};

  const timelineData = timeline?.timeline?.map(t => ({
    date: t.date?.slice(5, 10),
    roi: t.roi,
    profit: t.cumulative_profit
  })) || [];

  const edgeData = edgeDist?.distribution || [];

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">
            <span className="glow-text">EdgeHunter</span> Dashboard
          </h1>
          <p className="page-subtitle">
            Paper Trading • Atualizado em tempo real • {new Date().toLocaleDateString('pt-BR')}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <span className="badge badge-success">🟢 Sistema Ativo</span>
          <span className="badge badge-info">📝 Paper Trade</span>
        </div>
      </div>

      {/* Métricas Principais */}
      <div className="metric-grid">
        <MetricCard
          label="ROI Acumulado (30d)"
          value={perf.roi ?? 0}
          prefix={perf.roi >= 0 ? '+' : ''}
          colorClass={perf.roi >= 0 ? 'positive' : 'negative'}
          icon="📈"
          sub={`${summary.settled ?? 0} apostas liquidadas`}
        />
        <MetricCard
          label="Sharpe Ratio (30d)"
          value={perf.sharpe_ratio ?? 0}
          colorClass={perf.sharpe_ratio >= 0.5 ? 'positive' : 'neutral'}
          icon="📊"
          sub="Meta: > 0.5"
        />
        <MetricCard
          label="CLV Médio"
          value={perf.clv_avg ?? 0}
          prefix={perf.clv_avg >= 0 ? '+' : ''}
          colorClass={perf.clv_avg > 0 ? 'positive' : 'negative'}
          icon="🎯"
          sub="Closing Line Value"
        />
        <MetricCard
          label="Edge Médio Detectado"
          value={perf.avg_edge_detected ?? 0}
          prefix="+"
          colorClass="neutral"
          icon="⚡"
          sub="% acima da linha justa"
        />
        <MetricCard
          label="Apostas Pendentes"
          value={summary.pending ?? 0}
          colorClass="neutral"
          icon="⏳"
          sub={`${summary.wins ?? 0}W / ${summary.losses ?? 0}L`}
        />
        <MetricCard
          label="Win Rate"
          value={summary.win_rate ?? 0}
          colorClass={summary.win_rate >= 50 ? 'positive' : 'neutral'}
          icon="🏆"
          sub="% de apostas ganhas"
        />
      </div>

      {/* Gráficos */}
      <div className="grid-2-1" style={{ marginBottom: 24 }}>
        {/* Timeline de ROI */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">📈 Evolução do ROI (30d)</div>
          </div>
          {timelineData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={timelineData}>
                <defs>
                  <linearGradient id="roiGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fill: '#475569', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#475569', fontSize: 11 }} axisLine={false} tickLine={false} unit="%" />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="roi"
                  name="ROI"
                  stroke="#00d4ff"
                  strokeWidth={2}
                  fill="url(#roiGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">📊</div>
              <div className="empty-state-text">Sem dados ainda. Apostas aparecerão aqui após os resultados.</div>
            </div>
          )}
        </div>

        {/* Distribuição de Edge */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">⚡ Distribuição de Edge</div>
          </div>
          {edgeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={edgeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="range" tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Apostas" radius={[4, 4, 0, 0]}>
                  {edgeData.map((_, i) => (
                    <Cell key={i} fill={`hsl(${180 + i * 30}, 80%, 60%)`} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">⚡</div>
              <div className="empty-state-text">Aguardando detecção de value bets...</div>
            </div>
          )}
        </div>
      </div>

      {/* Tabela de apostas recentes */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">🎯 Apostas Recentes</div>
          <span className="badge badge-info">{betsData?.total ?? 0} total</span>
        </div>
        {betsData?.bets?.length > 0 ? (
          <RecentBets bets={betsData.bets} />
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">🎯</div>
            <div className="empty-state-text">
              Nenhuma aposta detectada ainda.<br />
              Configure as APIs e aguarde o próximo ciclo de detecção.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
