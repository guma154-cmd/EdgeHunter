# PRD-03: Value Detector

| Metadados | Valor |
|---|---|
| **ID** | PRD-03 |
| **Status** | Accepted |
| **Aceito em** | 2026-05-23 |
| **Responsável** | John (PM) |
| **Pai** | [PRD-00: Pivot de Value Betting](./00_master_value_betting.md) |
| **Criado em** | 15/05/2026 |

---

## 1. Declaração do Problema

Os bookmakers embutem uma margem de lucro (overround ~5-7% em casas "soft", ~2-3% na Pinnacle). Quando a Bet365 ou a Betano oferecem odds maiores que a "verdade" do mercado (representada pela Pinnacle) ou maiores que a nossa estimativa independente (PoissonModel), há **valor** — uma expectativa matemática positiva de lucro no longo prazo.

O `ValueDetector` é o coração analítico do pivô para Value Betting do EdgeHunter. Sem ele, todos os outros módulos (coleta de dados, modelagem) são apenas infraestrutura sem aplicação prática.

---

## 2. Metas

- **Velocidade**: Detectar oportunidades de valor em menos de 30 segundos após um novo snapshot de odds ser armazenado.
- **Precisão**: Manter uma taxa de falso positivo abaixo de 20% (validado contra resultados reais em backtests).
- **Flexibilidade**: Suportar três modos de detecção (baseado na Pinnacle, baseado no Modelo Poisson, e Consenso).
- **Auditabilidade**: Manter um log completo e detalhado para cada detecção, permitindo auditoria e análise de performance.
- **Eficiência**: Garantir deduplicação efetiva para não alertar sobre a mesma oportunidade repetidamente dentro de uma janela de tempo.

---

## 3. Não-Metas

- **Execução de Apostas**: Este módulo NÃO realizará apostas automaticamente. Sua responsabilidade termina ao alertar (tarefa do PRD-05).
- **Cálculo de Stake**: NÃO calculará o valor a ser apostado. O Critério de Kelly é responsabilidade do PRD-05.
- **Validação com IA**: NÃO fará validação com IA. A integração com Gemini é responsabilidade do PRD-04.
- **Ajuste de Thresholds**: NÃO ajustará dinamicamente os thresholds de EV. Isso é tarefa do módulo de AutoEvolution (PRD-05).

---

## 4. Histórias de Usuário

- [ ] **STORY-03-001**: Implementar cálculo de EV (função pura)
  - **Status**: a fazer | **Estimativa**: 1h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Função `calculate_ev(true_prob: float, offered_odds: float) -> float`.
    - Retorna `(true_prob * offered_odds) - 1`.
    - Valida inputs: probabilidade deve estar em [0,1], odds devem ser >= 1.01.
    - Levanta `ValueError` se os inputs forem inválidos.
    - Cobertura de testes de 100% para esta função crítica.

- [ ] **STORY-03-002**: Query de snapshots recentes válidos
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Método `get_recent_snapshots(minutes=30, league=None)`.
    - Filtra por padrão apenas snapshots com `valid_for_analysis = True`.
    - Performance da query < 100ms para 1000 snapshots.
    - Retorna uma estrutura de dados tipada (e.g., lista de Pydantic models).

- [ ] **STORY-03-003**: Detectar valor vs. benchmark da Pinnacle
  - **Status**: a fazer | **Estimativa**: 4h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Compara odds de Bet365 e Betano contra a probabilidade implícita da Pinnacle (`1 / pinnacle_odds`).
    - Aplica um threshold de EV configurável (padrão: 2%).
    - Ignora a oportunidade se a Pinnacle não tiver dados para o jogo.
    - Registra `detection_source = 'pinnacle'` no log da detecção.

- [ ] **STORY-03-004**: Detectar valor vs. Modelo Poisson
  - **Status**: a fazer | **Estimativa**: 4h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Usa o resultado de `poisson_model.predict_probabilities(home, away)` como `true_prob`.
    - **CRÍTICO**: Lida corretamente com o retorno `None` do modelo (caso de time não visto no treino), ignorando a oportunidade.
    - Ignora a detecção baseada no modelo se `PoissonModel.trained = False`.
    - Aplica um threshold de EV configurável.
    - Registra `detection_source = 'model'` no log.

- [ ] **STORY-03-005**: Implementar modo de consenso (Pinnacle E Modelo)
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - O modo é controlado pela configuração `consensus_required=True/False`.
    - Quando `True`, uma oportunidade é detectada APENAS se (EV da Pinnacle > threshold) E (EV do Modelo > threshold).
    - Registra `detection_source = 'consensus'` quando ambos confirmam.
    - Este é o modo recomendado para a fase inicial (Fase 3a) por ser mais conservador.

- [ ] **STORY-03-006**: Deduplicação de detecções
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - A mesma oportunidade (`match_id`, `outcome`, `bookmaker`) não é detectada duas vezes em uma janela de 1 hora.
    - Permite re-detecção se as odds mudarem significativamente (>5%), mesmo dentro da janela.
    - Usa um hash determinístico para identificar duplicatas.
    - Verificação de duplicatas deve ter performance < 10ms.

- [ ] **STORY-03-007**: Persistir detecções na tabela `value_detections`
  - **Status**: a fazer | **Estimativa**: 2h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Todos os campos do schema da tabela são persistidos corretamente.
    - A flag `alerted` tem valor padrão `False` (será atualizada pelo PRD-05).
    - A chave estrangeira para `odds_snapshots.id` é mantida.
    - Índices em (`match_id`, `detected_at`) para queries rápidas são criados.

- [ ] **STORY-03-008**: API REST para frontend consultar detecções
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: média
  - **Critério de Aceitação**:
    - Endpoint `GET /api/value-detections` retorna JSON paginado.
    - Suporta filtros: `?league=`, `?bookmaker=`, `?min_ev=`, `?since=`.
    - Comportamento padrão: retorna detecções das últimas 24h, ordenadas por EV descendente.
    - Documentação via OpenAPI/Swagger é gerada.
    - Performance do endpoint < 100ms (p95).

- [ ] **STORY-03-009**: Sanity check do detector
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Uma função `sanity_check()` é validada antes de ativar o detector.
    - Verificações:
      1. Taxa de detecção em janela de teste: entre 0.5% e 10% das oportunidades analisadas (não 0%, não 100%).
      2. Taxa de falso positivo < 25% em backtest.
      3. Cálculo de EV bate com cálculo manual em 100 cenários sintéticos.
      4. Deduplicação funciona (mesma oportunidade não é duplicada).
    - Se falhar, o detector é desabilitado e um alerta do Telegram é enviado.
    - Roda automaticamente na inicialização do scheduler.

- [ ] **STORY-03-010**: Testes unitários e adversariais
  - **Status**: a fazer | **Estimativa**: 5h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Cobertura de testes > 85% em todas as funções públicas.
    - **Testes Adversariais OBRIGATÓRIOS** (devem passar):
      ```python
      def test_ev_calculation_correctness():
          """EV(0.6, 2.0) = 0.2 exato"""

      def test_skip_when_pinnacle_odds_missing():
          """Snapshot sem Pinnacle não causa crash; retorna []"""

      def test_skip_when_model_returns_none():
          """Time desconhecido (model.predict retorna None) → skip"""

      def test_skip_when_model_not_trained():
          """PoissonModel.trained=False → usa só Pinnacle benchmark"""

      def test_consensus_requires_both():
          """Modo consensus: se só Pinnacle detecta, NÃO detect"""

      def test_no_duplicate_within_1h():
          """Mesma opp em 30min: detectada apenas 1 vez"""

      def test_duplicate_allowed_when_odds_changed_5pct():
          """Mesma opp com odds 5%+ diferentes: detectada de novo"""

      def test_handle_invalid_snapshot_filtered():
          """Snapshot com valid_for_analysis=False NÃO entra em análise"""

      def test_ev_threshold_filtering():
          """EV abaixo de threshold (ex: 1%) NÃO detectado"""

      def test_zero_division_protection():
          """Odds 0 ou negativa: ValueError, não crash"""
      ```

---

## 5. Especificação Técnica

### 5.1 Schema de Banco de Dados

```sql
CREATE TABLE IF NOT EXISTS value_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    
    -- Informações da partida (desnormalizado para queries rápidas)
    match_id TEXT NOT NULL,
    home_team TEXT,
    away_team TEXT,
    league TEXT,
    
    -- Detalhes da detecção
    outcome TEXT NOT NULL,  -- 'home_win', 'draw', 'away_win'
    bookmaker TEXT NOT NULL,  -- 'bet365', 'betano'
    
    -- Probabilidades & EV
    pinnacle_prob REAL,  -- 1 / pinnacle_odds
    model_prob REAL,     -- poisson_model.predict()
    offered_odds REAL NOT NULL,
    
    ev_pinnacle REAL,   -- EV calculado contra Pinnacle
    ev_model REAL,      -- EV calculado contra Modelo
    
    -- Metadados da detecção
    detection_source TEXT NOT NULL,  -- 'pinnacle', 'model', 'consensus'
    min_threshold REAL NOT NULL,
    
    -- Flags de ciclo de vida
    alerted BOOLEAN DEFAULT 0,        -- PRD-05 atualiza após alerta no Telegram
    bet_placed BOOLEAN DEFAULT 0,     -- PRD-05 atualiza após aposta manual
    
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (snapshot_id) REFERENCES odds_snapshots(id)
);

CREATE INDEX IF NOT EXISTS idx_detections_match_time 
    ON value_detections(match_id, detected_at);
CREATE INDEX IF NOT EXISTS idx_detections_alerted 
    ON value_detections(alerted, detected_at);
CREATE INDEX IF NOT EXISTS idx_detections_dedup 
    ON value_detections(match_id, outcome, bookmaker, detected_at);
```

### 5.2 Contrato de API (classe ValueDetector)

```python
from typing import Optional, List, Dict, Literal
from app.models.poisson_model import PoissonModel
from app.data.odds_historian import OddsHistorian

DetectionSource = Literal['pinnacle', 'model', 'consensus']

class ValueDetector:
    """Detector de oportunidades de value betting."""
    
    def __init__(
        self,
        db_path: str = "edge_hunter.db",
        league: str = "brasileirao",
        min_ev_threshold: float = 0.02,  # 2%, ajustado por AutoEvolution
        consensus_required: bool = False
    ):
        self.db_path = db_path
        self.league = league
        self.min_ev_threshold = min_ev_threshold
        self.consensus_required = consensus_required
        self.historian = OddsHistorian(db_path)
        self.model = PoissonModel(db_path, league)
        self.model.load_weights()
    
    @staticmethod
    def calculate_ev(true_prob: float, offered_odds: float) -> float:
        """EV = (P × odds) - 1. Função pura, sem efeitos colaterais."""
        if not 0 <= true_prob <= 1:
            raise ValueError(f"true_prob fora de [0,1]: {true_prob}")
        if offered_odds < 1.01:
            raise ValueError(f"offered_odds inválida: {offered_odds}")
        return (true_prob * offered_odds) - 1
    
    def find_value_opportunities(
        self,
        recent_minutes: int = 30
    ) -> List[Dict]:
        """
        Detecta oportunidades em snapshots recentes.
        
        Retorna: Lista ordenada por EV descendente.
        """
        # ...
    
    def log_detection(self, opportunity: Dict) -> int:
        """Persiste uma detecção no banco de dados. Retorna o ID criado."""
        # ...
    
    def is_duplicate(
        self,
        match_id: str,
        outcome: str,
        bookmaker: str,
        offered_odds: float,
        window_hours: int = 1
    ) -> bool:
        """
        Verifica se a detecção é uma duplicata.
        Não é duplicata se as odds mudaram >5% mesmo dentro da janela.
        """
        # ...
    
    def sanity_check(self) -> tuple[bool, List[str]]:
        """
        Validação pré-uso do detector.
        Retorna (passou: bool, falhas: List[str]).
        """
        # ...
```

### 5.3 Algoritmo de Detecção (Pseudocódigo)

```python
def find_value_opportunities(recent_minutes=30):
    opportunities = []
    snapshots = historian.get_snapshots(
        league=self.league,
        days_back=1,
        valid_only=True  # CRÍTICO: só snapshots sincronizados
    )
    # Filtra apenas snapshots dos últimos N minutos
    snapshots = [s for s in snapshots 
                 if (now - s['snapshot_timestamp']).seconds < recent_minutes*60]

    for snapshot in snapshots:
        for outcome in ['home_win', 'draw', 'away_win']:
            # Fonte da verdade 1: Pinnacle
            pinnacle_prob = None
            if snapshot[f'pinnacle_odds_{outcome}']:
                pinnacle_prob = 1 / snapshot[f'pinnacle_odds_{outcome}']
            
            # Fonte da verdade 2: Modelo
            model_prob = None
            if self.model.trained:
                model_probs = self.model.predict_probabilities(snapshot['home_team'], snapshot['away_team'])
                if model_probs is not None:  # CRÍTICO: pode ser None
                    model_prob = model_probs[outcome]
            
            if pinnacle_prob is None and model_prob is None:
                continue
            
            for bookmaker in ['bet365', 'betano']:
                offered_odds = snapshot[f'{bookmaker}_odds_{outcome}']
                if offered_odds is None or offered_odds < 1.01:
                    continue
                
                ev_pinnacle = calculate_ev(pinnacle_prob, offered_odds) if pinnacle_prob else None
                ev_model = calculate_ev(model_prob, offered_odds) if model_prob else None
                
                detected = False
                source = None
                
                if self.consensus_required:
                    if (ev_pinnacle is not None and ev_pinnacle > self.min_ev_threshold 
                        and ev_model is not None and ev_model > self.min_ev_threshold):
                        detected = True
                        source = 'consensus'
                else:
                    if ev_pinnacle is not None and ev_pinnacle > self.min_ev_threshold:
                        detected = True
                        source = 'pinnacle'
                    if ev_model is not None and ev_model > self.min_ev_threshold:
                        if detected:
                            source = 'consensus'
                        else:
                            detected = True
                            source = 'model'
                
                if detected and not self.is_duplicate(snapshot['match_id'], outcome, bookmaker, offered_odds):
                    opportunities.append({...})

    return sorted(opportunities, key=lambda x: max(x.get('ev_pinnacle') or 0, x.get('ev_model') or 0), reverse=True)
```

### 5.4 Requisitos de Performance

| Operação | Alvo | Como Medir |
|---|---|---|
| `find_value_opportunities()` (100 snapshots) | < 500ms | Benchmark |
| `calculate_ev()` | < 1µs | Teste unitário |
| `log_detection()` (single insert) | < 50ms | p95 |
| `is_duplicate()` (janela de 1h) | < 10ms | p95 |
| API `GET /api/value-detections` | < 100ms (p95) | Teste de carga |

---

## 6. Critério de Aceitação (Módulo Completo)

- [ ] Histórias 03-001 a 03-010 todas concluídas.
- [ ] Cobertura de testes > 85% em funções públicas.
- [ ] **Todos os 10 testes adversariais da STORY-03-010 passando.**
- [ ] O `sanity_check` é executado automaticamente na inicialização.
- [ ] Taxa de falso positivo < 25% em backtest (validar manualmente na Fase 2 de Paper Trading).
- [ ] API REST documentada via OpenAPI/Swagger.
- [ ] Documentação inline (docstrings) em PT-BR.

---

## 7. Dependências

- **Upstream**:
  - PRD-01 (OddsHistorian): consome `get_snapshots(valid_only=True)`.
  - PRD-02 (PoissonModel): chama `predict_probabilities()` (tratando `None`).
- **Downstream**:
  - PRD-04 (GeminiValidator): recebe oportunidades com EV > 5% para validação.
  - PRD-05 (AutoEvolution): consome detecções para calcular stake (Kelly) e enviar alertas.

---

## 8. Decisions

### 8.1 Accepted Decisions
- Quando a Pinnacle ainda não tiver odds para o jogo, ignorar a oportunidade na v1 e aguardar a próxima coleta.

Justificativa técnica: esta decisão afeta comportamento default observável da detecção e precisava ser resolvida agora porque muda o contrato da função de avaliação. Sem benchmark da Pinnacle, o sistema teria de escolher entre bloquear, estimar um proxy ou emitir oportunidade com base incompleta; isso altera tanto risco operacional quanto a interpretação do usuário sobre o significado do alerta.

Ignorar a oportunidade na v1 é a decisão mais segura porque preserva a premissa central do detector: comparar a oportunidade contra um benchmark sharp confiável. Forçar um proxy nessa fase aumentaria risco de falso positivo e criaria uma semântica híbrida mal definida logo no início do produto.

### 8.2 Deferred Decisions
- O threshold inicial de 2% fica mantido na v1; revisão posterior conforme `docs/decisions/deferred_decisions.md`.
- O cálculo de EV não vai considerar overround na v1; revisão posterior conforme `docs/decisions/deferred_decisions.md`.
- A janela de deduplicação fica em 1 hora na v1; revisão posterior conforme `docs/decisions/deferred_decisions.md`.

---

## 9. Consequências

Este PRD obriga o backend a expor uma camada de detecção determinística e auditável, com cálculo de EV, deduplicação e persistência completa das oportunidades encontradas. O código não pode tratar a detecção como heurística informal; ele precisa registrar a origem da decisão, suportar filtros por validade do snapshot e manter performance previsível mesmo com crescimento do histórico.

Na prática, isso introduz schema dedicado (`value_detections`), regras explícitas de deduplicação e contratos claros entre OddsHistorian, PoissonModel, GeminiValidator e AutoEvolution. Também implica que a API e o scheduler passem a trabalhar com eventos de detecção como entidades próprias, e não apenas como logs soltos ou mensagens efêmeras.

Como consequência operacional, qualquer mudança em threshold, benchmark ou semântica de oportunidade detectada precisa preservar a rastreabilidade definida aqui. Isso reduz risco de falso positivo invisível e garante que PRD-04 e PRD-05 recebam insumos estáveis para validação, staking e alertas.

## 10. Referências

- **Interna**:
    - ADR-002: Pinnacle como sharp benchmark ([ADR-002](../architecture/adr_002_pinnacle_benchmark.md)).
    - ADR-003: Estratégia híbrida ([ADR-003](../architecture/adr_003_hybrid_logic_ai.md)).
- **Externa**:
    - Critério de Kelly (implementação no PRD-05).
    - Trabalhos acadêmicos sobre value betting em mercados esportivos.
