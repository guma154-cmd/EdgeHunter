// EdgeHunter — Main App com Routing
import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import Dashboard from './pages/Dashboard';
import BetFeed from './pages/BetFeed';
import Analytics from './pages/Analytics';
import ModelStatus from './pages/ModelStatus';
import { ModelsAPI } from './services/api';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchInterval: 30000, // Atualiza a cada 30s
      staleTime: 15000,
      retry: 2
    }
  }
});

function Sidebar() {
  const { data: model } = useQuery({
    queryKey: ['activeModel'],
    queryFn: ModelsAPI.getActive,
    refetchInterval: 60000
  });

  const { data: drift } = useQuery({
    queryKey: ['drift'],
    queryFn: ModelsAPI.getDrift,
    refetchInterval: 60000
  });

  const driftStatus = drift?.overall || 'normal';

  const navItems = [
    { to: '/', icon: '⚡', label: 'Dashboard', end: true },
    { to: '/feed', icon: '🎯', label: 'Live Feed' },
    { to: '/analytics', icon: '📊', label: 'Analytics' },
    { to: '/model', icon: '🧠', label: 'Modelo & IA' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-mark">
          <div className="logo-icon">⚡</div>
          <div>
            <div className="logo-text">EdgeHunter</div>
            <div className="logo-badge">VALUE BETTING AI</div>
          </div>
        </div>
      </div>

      <div className="nav-section-label">Navegação</div>
      {navItems.map(item => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
        >
          <span className="nav-icon">{item.icon}</span>
          {item.label}
        </NavLink>
      ))}

      <div className="nav-section-label" style={{ marginTop: 'auto' }}>Sistema</div>

      <div className="sidebar-footer">
        <div className="status-indicator">
          <div className={`status-dot ${driftStatus === 'drift' ? 'danger' : driftStatus === 'warning' ? 'warning' : ''}`} />
          <span>
            {driftStatus === 'drift' ? '🚨 Drift Detectado' :
             driftStatus === 'warning' ? '⚠️ Warning' : '✅ Sistema Normal'}
          </span>
        </div>
        {model && (
          <div className="status-indicator" style={{ marginTop: 8 }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Modelo: {model.version || 'v1.0'}
            </span>
          </div>
        )}
      </div>
    </aside>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app-layout">
          <Sidebar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/feed" element={<BetFeed />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/model" element={<ModelStatus />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
