// EdgeHunter — Model Status Page
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ModelsAPI } from '../services/api';

function WeightBar({ label, value, colorClass }) {
  return (
    <div className="weight-row">
      <div className="weight-label">{label}</div>
      <div className="weight-track">
        <div className={`weight-fill ${colorClass}`} style={{ width: `${(value * 100).toFixed(1)}%` }} />
      </div>
      <div className="weight-pct">{(value * 100).toFixed(1)}%</div>
    </div>
  );
}

export default function ModelStatus() {
  const qc = useQueryClient();

  const { data: activeModel } = useQuery({
    queryKey: ['activeModel'],
    queryFn: ModelsAPI.getActive,
    refetchInterval: 30000
  });

  const { data: weights } = useQuery({
    queryKey: ['weights'],
    queryFn: ModelsAPI.getWeights,
    refetchInterval: 30000
  });

  const { data: drift } = useQuery({
    queryKey: ['drift'],
    queryFn: ModelsAPI.getDrift,
    refetchInterval: 30000
  });

  const { data: allModels } = useQuery({
    queryKey: ['allModels'],
    queryFn: ModelsAPI.getAll
  });

  const trainMutation = useMutation({
    mutationFn: ModelsAPI.triggerTrain,
    onSuccess: () => {
      setTimeout(() => qc.invalidateQueries(['activeModel', 'weights']), 3000);
    }
  });

  const w = weights?.weights || {};
  const metrics = activeModel?.metrics || {};
  const driftSummary = drift || {};

  const driftStatus = driftSummary.warning_active ? 'warning' : 'normal';

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">🧠 Modelo & IA</h1>
          <p className="page-subtitle">Ensemble adaptativo com 4 modelos • Pesos auto-ajustáveis</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => trainMutation.mutate()}
          disabled={trainMutation.isPending}
        >
          {trainMutation.isPending ? '⏳ Treinando...' : '🔄 Forçar Retraining'}
        </button>
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Pesos do Ensemble */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">⚖️ Pesos do Ensemble</div>
            <span className="badge badge-info">auto-ajustáveis</span>
          </div>
          <div className="weights-display">
            <WeightBar label="Dixon-Coles" value={w.dixon_coles || 0.30} colorClass="w-dc" />
            <WeightBar label="Elo Adaptativo" value={w.elo || 0.20} colorClass="w-elo" />
            <WeightBar label="XGBoost" value={w.xgboost || 0.35} colorClass="w-xgb" />
            <WeightBar label="Bayesiano" value={w.bayesian || 0.15} colorClass="w-bay" />
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 16, lineHeight: 1.5 }}>
            Pesos ajustados inversamente ao Brier Score de cada modelo. 
            Mínimo de 5% por modelo para evitar exclusão total.
          </p>
        </div>

        {/* Métricas do Modelo Ativo */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">📊 Modelo Ativo</div>
            {activeModel && <span className="badge badge-success">✅ {activeModel.version}</span>}
          </div>
          {activeModel ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {[
                { label: 'Brier Score', value: metrics.brier_score, fmt: v => v?.toFixed(4), good: v => v < 0.25, suffix: '' },
                { label: 'Sharpe Ratio (30d)', value: metrics.sharpe_ratio, fmt: v => v?.toFixed(3), good: v => v >= 0.5, suffix: '' },
                { label: 'ROI 30d', value: metrics.roi_30d, fmt: v => `${v >= 0 ? '+' : ''}${v?.toFixed(2)}%`, good: v => v > 0, suffix: '' },
                { label: 'CLV Médio', value: metrics.clv_avg, fmt: v => `${v >= 0 ? '+' : ''}${v?.toFixed(3)}%`, good: v => v > 0, suffix: '' },
                { label: 'Total Apostas', value: metrics.total_bets, fmt: v => v, good: null, suffix: '' },
              ].map((m, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{m.label}</span>
                  <span className={`mono ${m.good && m.value !== null ? (m.good(m.value) ? 'text-success' : 'text-danger') : 'text-brand'}`} style={{ fontWeight: 700 }}>
                    {m.value !== null && m.value !== undefined ? m.fmt(m.value) : '—'}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">🧠</div>
              <div className="empty-state-text">Nenhum modelo ativo. Execute o retraining inicial.</div>
            </div>
          )}
        </div>
      </div>

      {/* Drift Detection */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <div className="card-title">🔍 Concept Drift Detection</div>
          <span className={`badge ${driftStatus === 'drift' ? 'badge-danger' : driftStatus === 'warning' ? 'badge-pending' : 'badge-success'}`}>
            {driftStatus === 'drift' ? '🚨 Drift!' : driftStatus === 'warning' ? '⚠️ Warning' : '✅ Normal'}
          </span>
        </div>
        <div className="grid-2">
          <div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 16 }}>
              O sistema monitora continuamente a qualidade das previsões usando <strong style={{ color: 'var(--brand-primary)' }}>DDM (Drift Detection Method)</strong> e 
              análise de <strong style={{ color: 'var(--brand-accent)' }}>Brier Score</strong> rolling. 
              Quando detecta mudança estrutural, dispara retraining automático.
            </p>
            {driftSummary.brier_trend && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  ['Brier Score Atual', driftSummary.brier_trend?.current_brier?.toFixed(4)],
                  ['Média Histórica', driftSummary.brier_trend?.historical_avg?.toFixed(4)],
                  ['Delta', `${driftSummary.brier_trend?.delta >= 0 ? '+' : ''}${driftSummary.brier_trend?.delta?.toFixed(4)}`],
                  ['Threshold de Drift', driftSummary.brier_trend?.drift_threshold],
                  ['CLV Recente', driftSummary.clv_avg_recent !== null ? `${driftSummary.clv_avg_recent >= 0 ? '+' : ''}${driftSummary.clv_avg_recent}%` : '—'],
                ].map(([label, val], i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{label}</span>
                    <span className="mono" style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{val ?? '—'}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="card" style={{ background: 'var(--bg-secondary)', padding: 16 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Alertas de Drift</div>
              {driftSummary.drift_events?.length > 0 ? (
                driftSummary.drift_events.map((evt, i) => (
                  <div key={i} style={{ fontSize: '0.82rem', color: 'var(--brand-warning)', padding: '4px 0' }}>
                    🚨 Instância #{evt}
                  </div>
                ))
              ) : (
                <div style={{ fontSize: '0.82rem', color: 'var(--brand-accent)' }}>✅ Nenhum drift registrado</div>
              )}
            </div>
            <div className="card" style={{ background: 'var(--bg-secondary)', padding: 16 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Pipeline de Retraining</div>
              {['Detectar Drift / Horário', 'Buscar dados históricos', 'Treinar novo ensemble', 'Iniciar A/B test (50 bets)', 'Promover se superior'].map((step, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '4px 0' }}>
                  <span style={{ color: 'var(--brand-primary)', fontWeight: 700 }}>{i + 1}.</span> {step}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Histórico de Modelos */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">📋 Histórico de Versões</div>
          <span className="badge badge-info">{allModels?.models?.length ?? 0} versões</span>
        </div>
        {allModels?.models?.length > 0 ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Versão</th>
                  <th>Treinado em</th>
                  <th>Brier Score</th>
                  <th>Sharpe</th>
                  <th>ROI 30d</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {allModels.models.map(model => (
                  <tr key={model.id}>
                    <td className="mono">{model.version}</td>
                    <td style={{ fontSize: '0.82rem' }}>{model.trained_at?.slice(0, 16)?.replace('T', ' ')}</td>
                    <td className="mono">{model.metrics?.brier_score?.toFixed(4) ?? '—'}</td>
                    <td className={`mono ${model.metrics?.sharpe_ratio >= 0.5 ? 'text-success' : ''}`}>
                      {model.metrics?.sharpe_ratio?.toFixed(3) ?? '—'}
                    </td>
                    <td className={`mono ${model.metrics?.roi_30d >= 0 ? 'text-success' : 'text-danger'}`}>
                      {model.metrics?.roi_30d !== null ? `${model.metrics.roi_30d >= 0 ? '+' : ''}${model.metrics.roi_30d?.toFixed(2)}%` : '—'}
                    </td>
                    <td>
                      <span className={`badge ${
                        model.status?.is_active ? 'badge-success' :
                        model.status?.ab_status === 'testing' ? 'badge-warning' : 'badge-info'
                      }`}>
                        {model.status?.is_active ? '✅ Ativo' :
                         model.status?.ab_status === 'testing' ? '🔬 A/B Test' :
                         model.status?.ab_status === 'retired' ? '🔴 Aposentado' : '🔵 Candidato'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">🧠</div>
            <div className="empty-state-text">Nenhum modelo treinado ainda. Execute o retraining inicial.</div>
          </div>
        )}
      </div>
    </div>
  );
}
