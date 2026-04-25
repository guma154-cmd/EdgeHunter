# EdgeHunter — Sistema de Value Betting com Auto-Aperfeiçoamento

<!-- teste: validar GitHub Actions deploy -->
<!-- teste local: push para validar atualização no servidor -->
<!-- teste webhook: push para validar deploy local via listener -->
<!-- teste webhook final: push apos cadastro do hook GitHub -->
<!-- fase1 deploy auto test -->

## Visão Geral

O **EdgeHunter** é um sistema completo de detecção de value bets com loop de auto-aperfeiçoamento contínuo. Usa um ensemble de 4 modelos matemáticos cujos pesos se ajustam automaticamente baseados na performance real.

```
Backend Flask (Python) ←→ SQLite DB
       ↓
  Ensemble Engine (Dixon-Coles + Elo + XGBoost + Bayesiano)
       ↓
  Value Detector (edge mínimo 3%)
       ↓
  Telegram Bot → Alertas instantâneos
       ↓
  React Dashboard → http://localhost:5173
```

## Pré-requisitos

- Python 3.10+ (instalado em `venv/`)
- Node.js 18+
- Chaves de API (ver Configuração)

## Instalação Rápida

```bash
# 1. Clone e configure
cp .env.example backend/.env
# Edite backend/.env com suas chaves de API

# 2. Backend (já instalado no venv/)
# As dependências já estão instaladas no venv/

# 3. Frontend
cd frontend
npm install  # já feito
```

## Iniciar o Sistema

**Opção 1: Double-click em `start.bat`**

**Opção 2: Manual**
```powershell
# Terminal 1 — Backend
cd backend
..\venv\Scripts\python run.py

# Terminal 2 — Frontend
cd frontend
npm run dev
```

- Frontend: http://localhost:5173
- API Backend: http://localhost:5000/api/health

## Configuração das APIs

Edite `backend/.env`:

### 1. The Odds API
```
ODDS_API_KEY=sua_chave_aqui
```
- Cadastro gratuito: https://the-odds-api.com
- Tier free: 500 req/mês (suficiente para desenvolvimento)

### 2. Football-Data.org
```
FOOTBALL_DATA_API_KEY=sua_chave_aqui
```
- Cadastro gratuito: https://www.football-data.org
- Dados históricos de ligas europeias e Brasileirão

### 3. Telegram Bot
```
TELEGRAM_BOT_TOKEN=token_do_botfather
TELEGRAM_CHAT_ID=seu_chat_id
```
- Crie o bot via @BotFather no Telegram
- Para obter o chat ID: envie uma mensagem para o bot e acesse:
  `https://api.telegram.org/bot{TOKEN}/getUpdates`

## Arquitetura do Ensemble

### Modelos

| Modelo | Peso Inicial | Função |
|--------|-------------|--------|
| Dixon-Coles | 30% | Poisson bivariado com correção para placares baixos |
| Elo Adaptativo | 20% | Rating de força com K-factor dinâmico e MOV |
| XGBoost | 35% | Features: Elo, forma recente, H2H, dias de descanso |
| Bayesiano | 15% | Prior Dirichlet com atualização online |

### Auto-Ajuste de Pesos
Os pesos se ajustam automaticamente:
- Peso ∝ 1 / (Brier Score + ε)
- Mínimo de 5% por modelo
- Atualizado a cada resultado real

### Calibração (Platt Scaling)
- Converte scores brutos em probabilidades reais
- Avaliado por Brier Score e ECE
- Bookmaker típico: Brier ≈ 0.26-0.28 (com overround)

## Loop de Aprendizado

```
Odds detectadas (a cada 15min)
    ↓
Previsão do Ensemble
    ↓
Value Detector (edge ≥ 3%)
    ↓
Alerta Telegram + Paper Bet registrado
    ↓
Resultado real (a cada 30min)
    ↓
Online update (Elo + Bayesiano)
    ↓
Brier Score calculado por modelo
    ↓
Pesos do ensemble atualizados
    ↓
Retraining diário (4h UTC)
    ↓
A/B Test silencioso (50 bets)
    ↓
Promover se superior → Alerta Telegram
```

## Métricas Monitoradas

| Métrica | Objetivo | Significado |
|---------|----------|-------------|
| **CLV** | > 0% | Apostamos antes da linha se mover contra nós |
| **Sharpe Ratio** | > 0.5 | Retorno ajustado por risco |
| **ROI** | > 3% (30d) | Lucro líquido por unidade apostada |
| **Brier Score** | < 0.25 | Qualidade das probabilidades |
| **Win Rate** | ~55%+ | Taxa de acerto (varia por mercado) |

## APIs Disponíveis

```
GET  /api/health              # Status do sistema
GET  /api/bets/               # Listagem de apostas
GET  /api/bets/stats          # Estatísticas gerais
GET  /api/bets/clv            # Análise de CLV
GET  /api/games/              # Jogos disponíveis
GET  /api/games/upcoming      # Próximas 24h
GET  /api/analytics/overview  # Dashboard geral
GET  /api/analytics/roi-by-league
GET  /api/models/active       # Modelo em produção
GET  /api/models/weights      # Pesos do ensemble
GET  /api/models/drift        # Status de drift
POST /api/models/train        # Forçar retraining
```

## Dashboard React

- **Dashboard**: Métricas principais, ROI timeline, edge distribution
- **Live Feed**: Apostas detectadas em tempo real com filtros
- **Analytics**: ROI por liga, CLV analysis, distribuição de edge
- **Modelo & IA**: Pesos do ensemble, drift detection, histórico de versões

## Deploy Automático

O workflow de deploy em `.github/workflows/deploy.yml` roda em um runner self-hosted e faz o deploy a partir do clone persistente no servidor, não do workspace temporário do GitHub Actions.

Configure a variável de repositório `DEPLOY_DIR` com o caminho real do projeto no servidor, por exemplo:

```text
/srv/edgehunter
```

Pré-requisitos no servidor:
- O repositório já deve estar clonado em `DEPLOY_DIR`
- O arquivo `backend/.env` deve existir dentro desse diretório
- Docker com `docker compose` ou `docker-compose` deve estar instalado
- O runner self-hosted deve ter acesso a `git`, `curl` e `docker`

## Deploy por Webhook Local

Como fallback mais robusto ao runner self-hosted, o repositório inclui os artefatos do webhook local em `deploy/server/`:

- `deploy/server/deploy.sh`
- `deploy/server/hooks.json`
- `deploy/server/webhook.service`

Instalacao no servidor:

```bash
sudo cp deploy/server/deploy.sh /home/telematica/deploy.sh
sudo cp deploy/server/hooks.json /home/telematica/hooks.json
sudo cp deploy/server/webhook.service /etc/systemd/system/webhook.service
sudo chown telematica:telematica /home/telematica/deploy.sh /home/telematica/hooks.json
sudo chmod +x /home/telematica/deploy.sh
sudo apt-get update && sudo apt-get install -y webhook
sudo systemctl daemon-reload
sudo systemctl enable --now webhook
```

Webhook no GitHub:

- Payload URL: `http://100.0.4.90:9000/hooks/deploy-edgehunter`
- Content type: `application/json`
- Secret: `edgehunter-webhook-secret-2026`
- Events: `Just the push event`

O arquivo `.github/workflows/deploy.yml` foi mantido apenas como backup manual e nao roda mais em `push`.

## Paper Trading (30 dias)

O sistema opera em modo **paper trading** por padrão:
- Todas as apostas são registradas com stake virtual de 10 unidades
- Resultados calculados automaticamente após cada jogo
- Após 30 dias com:
  - CLV médio > 0
  - Sharpe Ratio > 0.5
  - ROI > 3% com ≥ 50 apostas
  - Brier Score < 0.25

...considerar migração para dinheiro real.

## Estrutura de Arquivos

```
EdgeHunter/
├── backend/
│   ├── app/
│   │   ├── engine/       # Dixon-Coles, Elo, XGBoost, Bayesiano, Ensemble
│   │   ├── detection/    # Value Detector, CLV Tracker
│   │   ├── data/         # Odds API, Football-Data, Scheduler
│   │   ├── alerts/       # Telegram Bot
│   │   ├── models/       # SQLAlchemy models
│   │   └── routes/       # Flask REST API
│   ├── .env              # Configurações (preencher)
│   └── run.py            # Entry point
├── frontend/
│   └── src/
│       ├── pages/        # Dashboard, BetFeed, Analytics, ModelStatus
│       └── services/     # API layer
├── database/
│   └── edgehunter.db     # SQLite database
├── venv/                 # Python virtualenv
└── start.bat             # Iniciar tudo com um clique
```
