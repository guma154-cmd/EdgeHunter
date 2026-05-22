# PRD-01: OddsHistorian v2

## 1. Metadata
- **ID**: PRD-01
- **Status**: Accepted
- **Owner**: Rafael
- **Parent**: PRD-00
- **Created**: 2026-05-14
- **Depends on**: ADR-004 (SQLite), Utility `app/utils/match_id.py`

## 2. Problem Statement
Os scrapers existentes coletam odds a cada 15min, mas **SOBRESCREVEM** os dados temporais (overwrite a cada ciclo). Para o Value Betting, precisamos de:
- Histórico completo de snapshots preservado.
- Match IDs consistentes entre fontes (resolvendo os IDs inconsistentes atuais).
- Risco mitigado de snapshot async (o mercado movendo entre coletas, gerando latência na sincronia).
- Sistema de health checks (atualmente, falha de scraper passa despercebida).

A solução será atuar como um *wrapper* sobre os scrapers existentes + utility `match_id` + validation layer + health monitoring, evitando alterar os scrapers base.

## 3. Goals
- 100% dos snapshots persistidos sem perda de dados.
- 100% dos snapshots com `max_latency_seconds` <= 120s OU devidamente sinalizados com a flag `valid_for_analysis = False`.
- Match ID determinístico funcionando para 99%+ dos jogos coletados.
- Health check capaz de detectar um scraper quebrado em <2 ciclos (30min).
- Query do histórico de 1000 matches executada em < 200ms.

## 4. Non-Goals
- NÃO modificar scrapers existentes (esta feature apenas adiciona um layer por cima).
- NÃO fazer análise dos dados ou detecção de value (responsabilidade do ValueDetector).
- NÃO armazenar dados de tênis ou outros esportes (escopo reservado para a Fase 4+).
- NÃO recuperar histórico anterior à implementação desta v2.

## 5. User Stories

- [ ] **STORY-01-001**: Criar utility `match_id` para padronização
  - **Status**: todo | **Estimate**: 4h | **Priority**: high
  - **Acceptance**: 
    - Função `generate_match_id()` funciona com diferentes formats
    - Função `normalize_team()` remove acentos, sufixos
    - 100% determinístico (mesmo input → mesmo output)
    - Cobertura de testes >90% com casos reais (Flamengo FC, S. Paulo, etc)
    - **CRITICAL ACCEPTANCE TESTS** (não devem colidir):
      - `generate_match_id("Manchester United", "Liverpool", date, "premier_league")` ≠ `generate_match_id("Manchester City", "Liverpool", date, "premier_league")`
      - `generate_match_id("Atlético Madrid", "Real Madrid", date, "la_liga")` ≠ `generate_match_id("Real Madrid", "Atlético Madrid", date, "la_liga")` (mandante/visitante invertidos = jogos diferentes)
      - `generate_match_id("Athletic Bilbao", "Real Madrid", date, "la_liga")` ≠ `generate_match_id("Athletico Paranaense", "Real Madrid", date, "brasileirao")`
      - `generate_match_id("São Paulo FC", "Palmeiras", date, "brasileirao")` == `generate_match_id("S. Paulo", "Palmeiras", date, "brasileirao")` (abreviações comuns devem colapsar pro mesmo ID)
  - **Files**: `backend/app/utils/match_id.py`, `tests/test_match_id.py`

- [ ] **STORY-01-002**: Inicializar schema SQL idempotente com sync fields
  - **Status**: todo | **Estimate**: 3h | **Priority**: high
  - **Acceptance**: 
    - Tabelas `matches`, `odds_snapshots`, `scraper_health` criadas
    - Indexes apropriados
    - Re-execução não quebra (CREATE IF NOT EXISTS)
    - Campos de sincronia presentes (max_latency_seconds, bookmakers_synced)

- [ ] **STORY-01-003**: Registrar match novo detectado pelos scrapers
  - **Status**: todo | **Estimate**: 3h | **Priority**: high
  - **Acceptance**: 
    - `register_match()` usa `generate_match_id()` para ID consistente
    - Idempotente (re-registrar não duplica)
    - Valida timezone (rejeita se naive datetime)

- [ ] **STORY-01-004**: Armazenar snapshot validado com sincronia
  - **Status**: todo | **Estimate**: 5h | **Priority**: high
  - **Acceptance**: 
    - Aceita dict de odds por bookmaker
    - Calcula `max_latency_seconds` (max diff entre timestamps)
    - Se latency > 120s: marca como `valid_for_analysis = False`
    - Persiste TODOS os snapshots (mesmo inválidos, para debugging)
    - Valida ranges de odds (entre 1.01 e 100.0)

- [ ] **STORY-01-005**: Atualizar resultado final do match
  - **Status**: todo | **Estimate**: 2h | **Priority**: medium
  - **Acceptance**: 
    - `update_match_result()` é idempotente
    - Calcula `result` (home_win/draw/away_win) automaticamente
    - Update status: pending → finished

- [ ] **STORY-01-006**: Query matches finalizados com última odd válida
  - **Status**: todo | **Estimate**: 4h | **Priority**: high
  - **Acceptance**: 
    - `get_finished_matches_with_last_odds()` retorna lista estruturada
    - Filtra apenas snapshots com `valid_for_analysis = True`
    - Suporta filtro por liga e limit
    - Performance < 200ms para 1000 matches

- [ ] **STORY-01-007**: Implementar health check de scrapers
  - **Status**: todo | **Estimate**: 5h | **Priority**: high
  - **Acceptance**: 
    - Detecta se scraper não produziu dados em últimos 2 ciclos (30min)
    - Detecta se odds não mudaram em 1h (likely cached/broken)
    - Detecta divergência > 10% entre Pinnacle e OddsPortal (cross-validation)
    - Persiste em `scraper_health` table
    - Trigger Telegram alert se status = CRITICAL

- [ ] **STORY-01-008**: Cleanup automático (retention policy)
  - **Status**: todo | **Estimate**: 3h | **Priority**: low
  - **Acceptance**: 
    - Cron job mensal deleta snapshots > 6 meses
    - Mantém match_results indefinidamente
    - Logs antes de deletar (audit trail)

- [ ] **STORY-01-009**: Testes unitários e integration
  - **Status**: todo | **Estimate**: 6h | **Priority**: high
  - **Acceptance**: 
    - Coverage > 85% em todas as funções públicas
    - Tests de race condition (multi-threaded insert)
    - Tests de edge cases (latency exatamente 120s, odds inválidas, etc)
    - Integration test com scraper mockado

- [ ] **STORY-01-010**: Backup automático do SQLite
  - **Status**: todo | **Estimate**: 3h | **Priority**: high
  - **Acceptance**: 
    - Backup diário do edge_hunter.db @ 03:00 UTC
    - Mantém últimos 7 backups (rotação automática FIFO)
    - Backup vai para diretório separado (`/backups/`)
    - Compressão gzip para economizar espaço
    - Procedimento de restore documentado em `docs/runbooks/db_restore.md`
    - Alert Telegram se backup falhar
    - Backup inclui arquivos auxiliares (.db-wal, .db-shm)
    - Antes de fazer cópia, executa wal_checkpoint(FULL)
    - Verifica integridade pós-backup (PRAGMA integrity_check)
  - **Files**: 
    - `backend/app/data/db_backup.py` (NEW)
    - `docs/runbooks/db_restore.md` (NEW)
  - **Rationale**: Fase 1 (Coleta Passiva) acumula 3+ semanas de dados historicos críticos. Perda zeraria o cronograma do projeto.
  - **Implementation hint**:
```python
    # Cron job @ 03:00 UTC
    @scheduler.scheduled_job('cron', hour=3, minute=0)
    async def daily_db_backup():
        backup_path = f"/backups/edge_hunter_{datetime.utcnow():%Y%m%d}.db.gz"
        # Use sqlite3 .backup() API (consistent snapshot)
        # Compress with gzip
        # Rotate (keep last 7)
        # Alert if fails
```

- [ ] **STORY-01-011**: WAL Checkpoint diário
  - **Status**: todo | **Estimate**: 1h | **Priority**: medium
  - **Acceptance**: 
    - Job diário @ 02:00 UTC executa `wal_checkpoint(PASSIVE)`
    - Log de tamanho do WAL antes/depois
    - Backup (STORY-01-010) deve incluir .db-wal e .db-shm
  - **Files**: `backend/app/data/scheduler.py` (modify)

## 6. Technical Specification

### 6.1 Match ID Utility

**File**: `backend/app/utils/match_id.py`

```python
import hashlib
import unicodedata
from datetime import datetime

TEAM_SUFFIXES = [
    # Sufixos genéricos que NÃO diferenciam (apenas categoria do clube)
    ' fc', ' ec', ' sc', ' ac', ' cf', ' cd',
    ' clube', ' esporte clube',
]

# NÃO REMOVER (esses são DIFERENCIADORES, parte do nome único):
# - united (Manchester United, Newcastle United)
# - city (Manchester City, Leicester City)
# - athletic / athletico (Athletic Bilbao, Athletico Paranaense)
# - atlético (Atlético Madrid, Atlético Mineiro)
# - real (Real Madrid, Real Sociedad, Real Betis)

def normalize_team(team_name: str) -> str:
    """
    Normaliza nome de time para gerar match_id consistente.
    
    Steps:
    1. Lowercase
    2. Remove acentos (NFKD)
    3. Remove sufixos comuns
    4. Strip + replace espaços por underscore
    
    Examples:
        "Flamengo FC" -> "flamengo"
        "São Paulo SC" -> "sao_paulo"
        "Manchester United" -> "manchester"
    """
    if not team_name or not team_name.strip():
        raise ValueError("team_name cannot be empty")
    
    name = unicodedata.normalize('NFKD', team_name).encode('ascii', 'ignore').decode().lower()
    
    for suffix in TEAM_SUFFIXES:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    
    return name.strip().replace(' ', '_')

def generate_match_id(
    home_team: str,
    away_team: str,
    match_date: datetime,
    league: str
) -> str:
    """
    Gera match_id determinístico (16 chars).
    
    Args:
        home_team: Nome do time mandante
        away_team: Nome do time visitante
        match_date: Data do jogo (timezone-aware required)
        league: Nome da liga
    
    Returns:
        16-character hex hash
    
    Raises:
        ValueError: Se match_date é naive (sem timezone)
    """
    if match_date.tzinfo is None:
        raise ValueError("match_date must be timezone-aware (use UTC)")
    
    normalized = (
        f"{league.lower().replace(' ', '_')}|"
        f"{normalize_team(home_team)}|"
        f"{normalize_team(away_team)}|"
        f"{match_date.strftime('%Y-%m-%d')}"
    )
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]
```

### 6.1.1 Hash Collision Risk Analysis

**Capacidade**: SHA256 truncado para 16 chars hex = 64 bits = 1.8 × 10^19 IDs únicos

**Escala atual estimada** (Fase 1+2):
- Brasileirão: 380 jogos/ano × 5 anos = 1.900 jogos
- Premier League: 380 × 5 = 1.900 jogos
- **Total**: ~4.000 jogos em escopo

**Birthday paradox**: 50% chance de colisão em ~5 bilhões de IDs gerados. Estamos 6 ordens de magnitude abaixo. Risco efetivamente zero.

**Mitigação extra**: Function `register_match()` faz check de colisão; se mesmo match_id já existe com teams/data DIFERENTES, raise exception.

### 6.2 Database Schema

```sql
-- Matches table (1 row per game)
CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,  -- generated via match_id utility
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    league TEXT NOT NULL,
    match_date TIMESTAMP NOT NULL,  -- UTC, timezone-aware
    home_goals INTEGER,
    away_goals INTEGER,
    result TEXT,  -- 'home_win', 'draw', 'away_win' (NULL if pending)
    status TEXT DEFAULT 'pending',  -- 'pending', 'finished', 'cancelled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_league_date ON matches(league, match_date);

-- Odds snapshots (N rows per match, ~every 15min)
CREATE TABLE IF NOT EXISTS odds_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT NOT NULL,
    
    -- Pinnacle (benchmark sharp)
    pinnacle_home REAL,
    pinnacle_draw REAL,
    pinnacle_away REAL,
    pinnacle_timestamp TIMESTAMP,
    
    -- Bet365
    bet365_home REAL,
    bet365_draw REAL,
    bet365_away REAL,
    bet365_timestamp TIMESTAMP,
    
    -- Betano
    betano_home REAL,
    betano_draw REAL,
    betano_away REAL,
    betano_timestamp TIMESTAMP,
    
    -- OddsPortal (aggregate)
    oddsportal_avg_home REAL,
    oddsportal_avg_draw REAL,
    oddsportal_avg_away REAL,
    oddsportal_timestamp TIMESTAMP,
    
    -- Sync metadata (CRITICAL)
    max_latency_seconds INTEGER,  -- Max diff entre timestamps dos bookmakers
    bookmakers_synced TEXT,  -- JSON array: ["pinnacle", "bet365", "betano"]
    valid_for_analysis BOOLEAN DEFAULT 1,  -- False if latency > 120s
    
    snapshot_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_match_time 
    ON odds_snapshots(match_id, snapshot_timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_valid 
    ON odds_snapshots(valid_for_analysis, snapshot_timestamp);

-- Scraper health monitoring
CREATE TABLE IF NOT EXISTS scraper_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scraper_name TEXT NOT NULL,  -- 'pinnacle', 'bet365', 'betano', 'oddsportal'
    
    last_successful_run TIMESTAMP,
    last_data_collected TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0,
    
    -- Validation flags
    odds_stale BOOLEAN DEFAULT 0,  -- True if odds não mudam em 1h
    divergence_detected BOOLEAN DEFAULT 0,  -- True if Pinnacle vs OddsPortal >10%
    
    status TEXT,  -- 'healthy', 'warning', 'critical'
    last_alert_sent TIMESTAMP,
    
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scraper_health_status ON scraper_health(scraper_name, status);
```

### 6.3 API Contract (OddsHistorian class)

```python
from datetime import datetime
from typing import Optional

class OddsHistorian:
    """Manager para snapshots históricos de odds + health checks"""
    
    def __init__(self, db_path: str = "edge_hunter.db"):
        self.db_path = db_path
        self._ensure_schema()
    
    def _ensure_schema(self) -> None:
        """Cria tabelas se não existem (idempotente)"""
    
    def register_match(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,  # MUST be timezone-aware
        league: str
    ) -> str:
        """
        Registra match e retorna match_id gerado.
        Idempotente: re-registrar mesmo jogo retorna mesmo ID sem erro.
        
        Raises:
            ValueError: Se match_date é naive
        """
    
    def store_snapshot(
        self,
        match_id: str,
        odds_by_bookmaker: dict[str, dict[str, float | datetime]]
    ) -> int:
        """
        Armazena snapshot com validação de sincronia.
        
        odds_by_bookmaker estrutura esperada:
        {
            'pinnacle': {
                'home': 2.10, 'draw': 3.40, 'away': 3.20,
                'timestamp': datetime(2025, 5, 14, 14, 0, 0, tzinfo=UTC)
            },
            'bet365': {...},
            'betano': {...},
            'oddsportal_avg': {...}
        }
        
        Validações:
        - Odds entre 1.01 e 100.0 (raise ValueError se fora)
        - Timestamps timezone-aware (raise ValueError se naive)
        - Match_id existe (raise ValueError se não)
        
        Calcula automaticamente:
        - max_latency_seconds (max diff entre timestamps dos bookmakers)
        - bookmakers_synced (lista dos que tem dados)
        - valid_for_analysis (True se max_latency <= 120s)
        
        Returns: ID do snapshot criado
        """
    
    def update_match_result(
        self,
        match_id: str,
        home_goals: int,
        away_goals: int
    ) -> None:
        """
        Atualiza resultado e calcula `result` automaticamente.
        Idempotente (UPDATE, não INSERT).
        """
    
    def get_snapshots(
        self,
        match_id: Optional[str] = None,
        league: Optional[str] = None,
        days_back: Optional[int] = None,
        valid_only: bool = True
    ) -> list[dict]:
        """Query com filtros"""
    
    def get_finished_matches_with_last_odds(
        self,
        league: Optional[str] = None,
        limit: int = 1000
    ) -> list[dict]:
        """
        Para treinar modelo Poisson.
        
        Returns: lista de dicts com schema:
        {
            'match_id': str,
            'home_team': str,
            'away_team': str,
            'league': str,
            'match_date': datetime,
            'home_goals': int,
            'away_goals': int,
            'result': str,
            'pinnacle_home': float,
            'pinnacle_draw': float,
            'pinnacle_away': float,
            'last_snapshot_at': datetime
        }
        
        Filtra apenas snapshots com valid_for_analysis=True.
        """
    
    # ============ Health Check Methods ============
    
    def update_scraper_health(
        self,
        scraper_name: str,
        success: bool,
        data_collected: bool = True
    ) -> None:
        """Chamado pelos scrapers após cada execução"""
    
    def check_all_scrapers_health(self) -> dict[str, dict]:
        """
        Avalia health de todos os scrapers.
        
        Returns: {
            'pinnacle': {'status': 'healthy', 'last_run': ..., 'issues': []},
            'bet365': {'status': 'critical', 'last_run': ..., 'issues': ['no_data_2_cycles']},
            ...
        }
        
        Issues detectados:
        - 'no_data_2_cycles': sem dados em últimas 2 execuções
        - 'odds_stale': odds não mudam em 1h
        - 'divergence_detected': diff > 10% com cross-source
        """
    
    def detect_cross_source_divergence(
        self,
        threshold: float = 0.10
    ) -> list[dict]:
        """
        Compara Pinnacle vs OddsPortal_avg para mesmo match.
        Se divergência > 10%, flag como suspicious.
        """
    
    # ============ Cleanup ============
    
    def cleanup_old_snapshots(self, retention_days: int = 180) -> int:
        """Deleta snapshots > X dias. Returns rows deleted."""
```

### 6.4 Performance Requirements

| Operation | Target | Measurement |
|-----------|--------|-------------|
| `store_snapshot` (single) | p95 < 50ms | 1000 inserts test |
| `get_snapshots` (1000 matches) | < 200ms | Production-like data |
| `register_match` (idempotent) | < 30ms | Including hash gen |
| `check_all_scrapers_health` | < 100ms | All 4 scrapers |
| `cleanup_old_snapshots` | < 5s for 100k rows | Batch delete |

### 6.5 Integration with Existing Scheduler

Modificar `backend/app/data/scheduler.py`:

```python
from app.data.odds_historian import OddsHistorian

historian = OddsHistorian()

# Hook após fetch_odds existente
async def fetch_odds_with_history():
    # ... código existente que coleta odds ...
    odds_results = await collect_all_scrapers()
    
    # NOVO: persiste em histórico
    for match_data in odds_results:
        match_id = historian.register_match(
            home_team=match_data['home'],
            away_team=match_data['away'],
            match_date=match_data['date_utc'],  # MUST be UTC
            league=match_data['league']
        )
        
        try:
            historian.store_snapshot(match_id, match_data['odds'])
        except ValueError as e:
            logger.warning(f"Invalid snapshot skipped: {e}")
    
    # NOVO: atualiza health dos scrapers
    for scraper_name in ['pinnacle', 'bet365', 'betano', 'oddsportal']:
        historian.update_scraper_health(
            scraper_name,
            success=scraper_name in odds_results['successful_scrapers']
        )

# NOVO: Job a cada 30min para verificar health
@scheduler.scheduled_job('interval', minutes=30)
async def check_scraper_health():
    health = historian.check_all_scrapers_health()
    for scraper, status in health.items():
        if status['status'] == 'critical':
            await telegram_bot.send_alert(
                f"🚨 Scraper {scraper} em estado crítico: {status['issues']}"
            )

# NOVO: Cron mensal para cleanup
@scheduler.scheduled_job('cron', day=1, hour=3)
async def monthly_cleanup():
    deleted = historian.cleanup_old_snapshots(retention_days=180)
    logger.info(f"Cleanup: {deleted} snapshots deletados")
```

### 6.6 Concurrent Writes Strategy (SQLite WAL)

**Problema**: Os scrapers do EdgeHunter executam assincronamente:
- Pinnacle: aiohttp async direto
- Bet365/Betano: Playwright (subprocess)
- OddsPortal: Playwright + BS4

No modo padrão do SQLite (`journal_mode=DELETE`), inserts concorrentes geram `OperationalError: database is locked` em picos do ciclo de 15min.

**Solução**: Habilitar Write-Ahead Logging (WAL) + configurações de concorrência.

**Implementação** (no `_ensure_schema()` da classe OddsHistorian):

```python
def _ensure_schema(self) -> None:
    """Cria schema + configura SQLite para concorrência"""
    with sqlite3.connect(self.db_path, timeout=10) as conn:
        cursor = conn.cursor()
        
        # CRITICAL: Habilitar WAL para escritas concorrentes
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # Timeout antes de raise OperationalError (5s default)
        cursor.execute("PRAGMA busy_timeout=5000")
        
        # NORMAL é seguro com WAL (FULL é overkill, OFF é perigoso)
        cursor.execute("PRAGMA synchronous=NORMAL")
        
        # Cache em memória para performance
        cursor.execute("PRAGMA cache_size=-10000")  # 10MB
        
        # Foreign keys ON
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # Cria tabelas (CREATE IF NOT EXISTS)
        cursor.execute(CREATE_MATCHES_TABLE)
        cursor.execute(CREATE_SNAPSHOTS_TABLE)
        cursor.execute(CREATE_HEALTH_TABLE)
        
        # Cria indexes
        for idx_stmt in CREATE_INDEXES:
            cursor.execute(idx_stmt)
        
        conn.commit()
```

**Trade-offs WAL Mode**:
- ✅ Múltiplos readers + 1 writer concurrent (vs DELETE: lock global)
- ✅ Performance ~3x melhor em writes
- ✅ Crash-safe (WAL é replayed na próxima conexão)
- ⚠️ Cria arquivos auxiliares `.db-wal` e `.db-shm` (incluir no backup!)
- ⚠️ Cleanup periódico necessário: `PRAGMA wal_checkpoint(PASSIVE)`

## 7. Acceptance Criteria (módulo como um todo)
- [ ] Stories 01-001 a 01-011 todas completas
- [ ] Coverage > 85%
- [ ] Performance requirements atendidos (com benchmark tests)
- [ ] Zero regressão nos scrapers existentes (smoke test)
- [ ] Health checks geram alerts em <30min
- [ ] Match IDs consistentes em 99%+ dos casos (validação manual com 50 jogos)
- [ ] Documentação inline completa
- [ ] Integration test end-to-end passa

## 8. Dependencies
- **Upstream**: 
  - Scrapers existentes (devem retornar dict estruturado com timestamps UTC)
  - Utility `match_id` (STORY-01-001 é blocker)
- **Downstream**: 
  - PRD-02 (PoissonModel) consome `get_finished_matches_with_last_odds()`
  - PRD-03 (ValueDetector) consome `get_snapshots(valid_only=True)`

## 9. Decisions

### 9.1 Accepted Decisions
- Persistir snapshots inválidos quando `latency > 120s`; marcar com `valid_for_analysis=False` para debugging e exclusão automática da análise.
- Tratar jogos cancelados/adiados com `status='cancelled'` ou `status='postponed'`; manter snapshots persistidos, mas fora do fluxo de análise ativa.

Justificativa técnica: as duas decisões afetam schema lógico e comportamento default observável do pipeline histórico. Persistir snapshots inválidos com flag explícita evita perda de evidência operacional, mantém rastreabilidade para debugging e impede que a camada analítica trate latência ruim como dado confiável. Isso precisa estar decidido antes da implementação porque altera colunas, filtros e contratos de leitura.

Também era necessário fechar agora o tratamento de jogos cancelados/adiados porque isso define o ciclo de vida dos registros e evita lógica ambígua em consumidores downstream. Manter os snapshots, mas removê-los do fluxo ativo, preserva auditabilidade sem contaminar treino, cross-validation ou detecção de valor.

### 9.2 Deferred Decisions
- Cross-validation Pinnacle vs OddsPortal: manter o threshold de 10% na v1 e revisar depois conforme o `docs/decisions/deferred_decisions.md`.

## 10. References
- ADR-001: Por que Poisson (PoissonModel consome dados aqui)
- ADR-002: Pinnacle como benchmark (importante para cross-validation)
- ADR-004: Por que SQLite
- PRD-00 Section 11.1 Gap 1, 4: Match ID + Timezone strategy
