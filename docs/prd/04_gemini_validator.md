# PRD-04: Gemini Validator

| Metadados | Valor |
|---|---|
| **ID** | PRD-04 |
| **Status** | Accepted |
| **Aceito em** | 2026-05-23 |
| **Responsável** | John (PM) |
| **Pai** | [PRD-00: Pivot de Value Betting](./00_master_value_betting.md) |
| **Criado em** | 15/05/2026 |

---

## 1. Declaração do Problema

Os módulos analíticos do EdgeHunter (PRD-02 e PRD-03) são determinísticos e estatísticos — excelentes para a maioria dos casos, mas podem ter **pontos cegos**:

- O Modelo Poisson pode sofrer "drift" com novos dados sem que percebamos rapidamente, levando a predições menos precisas.
- O ValueDetector pode gerar falsos positivos em situações atípicas (por exemplo, jogos com odds suspeitas, mercados ilíquidos, ou eventos extra-esportivos não capturados pelos dados de entrada).
- O sistema, no geral, pode degradar lentamente ou estagnar sem uma intervenção humana regular e inteligente.

O `GeminiValidator` atua como um **revisor inteligente**, focado nos cenários de maior risco/recompensa. Ele complementa a lógica existente, fornecendo validação contextual e insights estratégicos, sem onerar o orçamento (o free tier do Gemini é suficiente para o uso planejado).

---

## 2. Metas

- **Cobertura**: 100% das detecções com Expected Value (EV) > 5% são validadas pela IA antes de serem alertadas ao usuário.
- **Detecção de Anomalias**: Anomalias críticas no comportamento do sistema ou nos dados são identificadas em menos de 24 horas após sua ocorrência.
- **Sugestões Acionáveis**: Cada sugestão de evolução gerada pela IA deve ser específica e ter um caminho claro para implementação (não ser vaga ou genérica).
- **Controle de Custos**: Manter o uso da API Gemini dentro dos limites do free tier (< 80% do limite mensal).
- **Resiliência**: Garantir que 0 alertas sejam perdidos devido a falhas ou indisponibilidade da API Gemini, utilizando estratégias de "graceful degradation".

---

## 3. Não-Metas

- **Substituição da Lógica Determinística**: Este módulo NÃO substitui a lógica determinística do ValueDetector, mas sim a complementa como uma camada de validação adicional.
- **Operações Autônomas de Trade**: NÃO realizará operações de trade automaticamente. A decisão final de aposta e a execução permanecem com o operador humano.
- **Validação Universal**: NÃO consultará a API Gemini para CADA detecção. A validação via IA é reservada apenas para oportunidades de alto EV (> 5%).
- **Bloqueio do Pipeline**: NÃO bloqueará o pipeline principal de detecção e alerta se a API Gemini estiver indisponível ou falhar.
- **Uso do Gemini Pro**: NÃO utilizará o modelo Gemini Pro. O modelo Gemini 2.0 Flash é suficiente para os casos de uso definidos e se encaixa no budget do free tier.

---

## 4. Histórias de Usuário

- [ ] **STORY-04-001**: Setup do cliente Gemini com autenticação via .env
  - **Status**: a fazer | **Estimativa**: 2h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - O cliente `google-generativeai` inicializa corretamente.
    - A API key é lida de `GEMINI_API_KEY` no arquivo `.env` (nunca hardcoded).
    - Um erro claro é emitido se a API key estiver ausente ou for inválida.
    - Uma função `is_available()` testa a conectividade e a validade da chave rapidamente.
    - O modelo configurado é `gemini-2.0-flash-exp`.

- [ ] **STORY-04-002**: Implementar `validate_opportunity()`
  - **Status**: a fazer | **Estimativa**: 4h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - O método recebe um dicionário de oportunidade (`opportunity: Dict`) do ValueDetector (PRD-03).
    - Recebe contexto adicional: `recent_accuracy` (do PoissonModel) e `recent_roi`.
    - Retorna uma estrutura de dicionário contendo:
      ```python
      {
          'is_valid': bool,
          'confidence': float,  # 0.0 a 1.0
          'reasoning': str,     # explicação em PT-BR
          'recommendation': 'place' | 'skip',
          'stake_adjustment': float,  # 0.5 a 1.5
          'tokens_used': int,
          'response_time_ms': int
      }
      ```
    - Registra (`logger.info`) a decisão de validação da IA.

- [ ] **STORY-04-003**: Implementar `detect_anomalies()`
  - **Status**: a fazer | **Estimativa**: 4h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - O método recebe um dicionário de métricas do sistema (ex: ROI 7d/30d, accuracy, total_bets, losing_streak, last_threshold_change).
    - Retorna um dicionário contendo:
      ```python
      {
          'has_anomaly': bool,
          'anomaly_type': 'model_drift' | 'data_error' | 'logic_bug' | 'none',
          'severity': 'critical' | 'warning' | 'info',
          'description': str,
          'suggested_fix': str,
          'action_priority': int  # 1-5
      }
      ```
    - Dispara um alerta automático via Telegram se a `severity` for 'critical'.

- [ ] **STORY-04-004**: Implementar `suggest_evolution()`
  - **Status**: a fazer | **Estimativa**: 4h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - O método recebe estatísticas semanais consolidadas do sistema (ex: total_bets, roi, accuracy_per_league).
    - Retorna uma lista de sugestões de melhoria, cada uma com categoria, impacto esperado e risco.
    - Sugestões com `risk='low'` são sinalizadas para aplicação automática pelo AutoEvolution (PRD-05).
    - Sugestões `risk='medium'` e `risk='high'` requerem aprovação manual do usuário.

- [ ] **STORY-04-005**: Parse robusto de JSON da API Gemini
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Uma função utilitária `_parse_json_response(text: str) -> dict` é implementada.
    - Lida corretamente com os seguintes formatos de resposta da API Gemini:
      - JSON puro (resposta ideal).
      - JSON encapsulado em blocos de código Markdown (ex: ` ```json ... ``` `).
      - JSON com vírgulas pendentes (trailing commas), que o Gemini ocasionalmente gera.
      - Respostas com texto antes ou depois do bloco JSON.
    - Em caso de JSON malformado e irrecuperável, tenta refazer a chamada à API com um prompt mais explícito.
    - Levanta `GeminiParseError` se o JSON permanecer irrecuperável após as tentativas.

- [ ] **STORY-04-006**: Lógica de retry com exponential backoff
  - **Status**: a fazer | **Estimativa**: 2h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Um decorator `@retry_with_backoff(max_retries=3)` é implementado para chamadas à API Gemini.
    - O backoff exponencial segue a sequência: 1s, 2s, 4s entre tentativas.
    - Um timeout de 10 segundos é aplicado por tentativa.
    - Logs estruturados são gerados para cada tentativa (sucesso/falha).
    - Se falhar após o número máximo de retries, retorna um dicionário de fallback (não levanta exceção).

- [ ] **STORY-04-007**: Persistir validações, anomalias e sugestões em DB
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - 3 novas tabelas são criadas no banco de dados: `gemini_validations`, `gemini_anomaly_reports`, `gemini_evolution_suggestions`.
    - Cada registro inclui campos de metadados como `response_raw`, `tokens_used`, `response_time_ms`, `created_at`.
    - Índices apropriados são criados para otimizar queries baseadas em `created_at` e `tokens_used`.

- [ ] **STORY-04-008**: Monitoramento de tokens consumidos
  - **Status**: a fazer | **Estimativa**: 2h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Um tracking cumulativo mensal do uso de tokens é mantido em uma tabela `gemini_token_usage`.
    - Dispara um alerta via Telegram se o uso de tokens atingir 80% do limite mensal do free tier (1.6M tokens).
    - O contador de tokens é resetado automaticamente no início de cada mês.
    - Uma função `get_remaining_budget()` retorna o número de tokens disponíveis no mês corrente.

- [ ] **STORY-04-009**: Cache de validações idênticas (proteção contra duplicatas)
  - **Status**: a fazer | **Estimativa**: 2h | **Prioridade**: média
  - **Critério de Aceitação**:
    - Se a mesma oportunidade (identificada por um hash de `match_id + outcome + bookmaker + odds`) for solicitada para validação dentro de uma janela de 1 hora, o resultado é retornado do cache.
    - O cache é mantido em memória RAM (não há necessidade de persistência em SQLite).
    - O uso do cache deve reduzir significativamente o número de chamadas à API Gemini quando o ValueDetector detecta a mesma oportunidade consecutivamente.

- [ ] **STORY-04-010**: Sanity check do GeminiValidator
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Uma função `sanity_check()` é executada automaticamente na inicialização do sistema.
    - As verificações incluem:
      1. Validade da API key (realiza uma chamada de teste com um prompt mínimo).
      2. Latência da API Gemini < 5 segundos em uma chamada de teste.
      3. O parser de JSON funciona corretamente com 5 respostas sintéticas de teste.
      4. O fallback retorna a estrutura de dados esperada quando a API Gemini falha.
      5. O budget de tokens não está esgotado (uso atual < 95% do limite mensal).
    - Se o `sanity_check` falhar, o módulo `GeminiValidator` é desabilitado temporariamente e um alerta é enviado via Telegram.
    - Neste estado de falha, o `GeminiValidator` opera em modo "always fallback" (sempre retorna o resultado de fallback).

- [ ] **STORY-04-011**: Testes unitários e adversariais
  - **Status**: a fazer | **Estimativa**: 6h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Cobertura de testes > 80% em todas as funções públicas do módulo.
    - Mocks para a API Gemini são utilizados (nenhuma chamada real é feita em testes unitários).
    - **Testes Adversariais OBRIGATÓRIOS** (devem passar):
      ```python
      def test_validate_returns_safe_fallback_on_timeout():
          """Timeout do Gemini não crasha; retorna fallback dict"""
      
      def test_validate_returns_safe_fallback_on_rate_limit():
          """Rate limit retorna fallback com flag SEM_VALIDACAO_IA"""
      
      def test_parse_json_with_markdown_blocks():
          """Resposta '```json {...} ```' parseada corretamente"""
      
      def test_parse_json_with_trailing_commas():
          """JSON com trailing commas é normalizado"""
      
      def test_parse_invalid_json_triggers_retry():
          """JSON malformado dispara retry com prompt mais explícito"""
      
      def test_token_budget_alert_at_80_percent():
          """Atingir 1.6M tokens dispara alert Telegram"""
      
      def test_cache_returns_same_result_for_duplicate_opp():
          """Mesma opp em 1h: retorna do cache, não chama Gemini"""
      
      def test_anomaly_critical_triggers_telegram():
          """severity='critical' envia alert Telegram automaticamente"""
      
      def test_evolution_low_risk_applied_auto():
          """Sugestão risk='low' é flagged para auto-aplicar"""
      
      def test_sanity_check_disables_module_on_failure():
          """Sanity check falha → módulo entra em modo always-fallback"""
      
      def test_retry_with_exponential_backoff():
          """3 tentativas com backoff 1s, 2s, 4s"""
      
      def test_response_truncated_handled_gracefully():
          """Gemini retorna resposta truncada (>max_tokens): não crasha"""
      ```

---

## 5. Especificação Técnica

#### 5.1 Schema de Banco de Dados (4 tabelas)

```sql
-- Validações de oportunidades
CREATE TABLE IF NOT EXISTS gemini_validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detection_id INTEGER NOT NULL,  -- FK para value_detections
    
    -- Resultado da validação
    is_valid BOOLEAN,
    confidence REAL,
    reasoning TEXT,
    recommendation TEXT,  -- 'place' | 'skip'
    stake_adjustment REAL,
    
    -- Metadados
    response_raw TEXT,
    tokens_used INTEGER,
    response_time_ms INTEGER,
    fallback_reason TEXT,  -- preenchido se houve fallback
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (detection_id) REFERENCES value_detections(id)
);

-- Relatórios de anomalias
CREATE TABLE IF NOT EXISTS gemini_anomaly_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    has_anomaly BOOLEAN NOT NULL,
    anomaly_type TEXT,  -- 'model_drift', 'data_error', 'logic_bug', 'none'
    severity TEXT,      -- 'critical', 'warning', 'info'
    description TEXT,
    suggested_fix TEXT,
    action_priority INTEGER,  -- 1-5
    
    -- Métricas que dispararam (JSON)
    metrics_snapshot TEXT,
    
    response_raw TEXT,
    tokens_used INTEGER,
    
    telegram_alerted BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sugestões de evolução semanal
CREATE TABLE IF NOT EXISTS gemini_evolution_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    week_start DATE NOT NULL,
    suggestions_json TEXT NOT NULL,  -- lista de sugestões
    priority_changes_json TEXT,
    
    response_raw TEXT,
    tokens_used INTEGER,
    
    applied_auto BOOLEAN DEFAULT 0,  -- True se sugestões risk='low' aplicadas
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tracking de uso de tokens
CREATE TABLE IF NOT EXISTS gemini_token_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    month_year TEXT NOT NULL,  -- 'YYYY-MM'
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(month_year)
);
```

#### 5.2 Contrato de API (classe GeminiValidator)

```python
from typing import Optional, Dict, List, Literal
import google.generativeai as genai

ValidationResult = Dict[str, any]
AnomalyType = Literal['model_drift', 'data_error', 'logic_bug', 'none']
Severity = Literal['critical', 'warning', 'info']

class GeminiValidator:
    """Camada de IA para validação contextual e detecção de anomalias."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,  # ou via env GEMINI_API_KEY
        model_name: str = "gemini-2.0-flash-exp",
        db_path: str = "edge_hunter.db",
        max_tokens_per_month: int = 1_600_000  # 80% do free tier 2M
    ): ...
    
    async def validate_opportunity(
        self,
        opportunity: Dict,
        recent_accuracy: float,
        recent_roi: float
    ) -> ValidationResult:
        """Valida opp do PRD-03. Inclui graceful degradation."""
    
    async def detect_anomalies(self, metrics: Dict) -> Dict:
        """Detecção diária. Alert Telegram se critical."""
    
    async def suggest_evolution(self, weekly_stats: Dict) -> Dict:
        """Sugestões semanais. Auto-aplica risk='low'."""
    
    def sanity_check(self) -> tuple[bool, List[str]]:
        """Validação no startup."""
    
    def get_remaining_budget(self) -> int:
        """Tokens disponíveis no mês corrente."""
    
    def is_available(self) -> bool:
        """True se Gemini está respondendo e budget OK."""
    
    # Internos
    def _parse_json_response(self, text: str) -> Dict: ...
    async def _call_gemini(self, prompt: str, max_tokens: int = 1000) -> str: ...
    def _track_tokens(self, input_tokens: int, output_tokens: int) -> None: ...
    def _get_cached_validation(self, opp_hash: str) -> Optional[ValidationResult]: ...
```

#### 5.3 Templates de Prompts Gemini (em PT-BR)

**Template Validação de Oportunidade**:
Você é um analista experiente de value betting esportivo.
Avalie se a seguinte oportunidade é REAL ou FALSO POSITIVO do modelo:
Partida: {match}
Liga: {league}
Resultado proposto: {outcome}
Probabilidade implícita Pinnacle: {pinnacle_prob:.1%}
Probabilidade calculada pelo modelo: {model_prob:.1%}
Odds oferecida ({bookmaker}): {offered_odds:.2f}
Expected Value (EV): {ev:.4f} ({ev_percent:.2f}%)
Performance recente do sistema:

Acurácia últimos 7 dias: {accuracy_7d:.1f}%
ROI últimos 30 dias: {roi_30d:.2f}%

Considere:

A probabilidade calculada é realista para esse confronto?
A discrepância de odds tem justificativa de mercado?
O histórico recente do sistema é confiável?

Responda APENAS com JSON válido (sem markdown blocks):
{
"is_valid": true/false,
"confidence": 0.0-1.0,
"reasoning": "breve explicação em PT-BR (max 200 chars)",
"recommendation": "place" ou "skip",
"stake_adjustment": 0.5-1.5
}

**Template Detecção de Anomalia**:
Você é um monitor de qualidade para sistema de value betting.
Analise estas métricas dos últimos dias e identifique BUGS ou PROBLEMAS:
Métricas:
{metrics_json}
Observe especialmente:

Queda anormal de ROI (>10% em 7 dias)
Acurácia do modelo degradando (modelo overfit?)
Mudanças bruscas no comportamento de detecção
Inconsistências entre fontes de dados

Responda APENAS com JSON válido:
{
"has_anomaly": true/false,
"anomaly_type": "model_drift" | "data_error" | "logic_bug" | "none",
"severity": "critical" | "warning" | "info",
"description": "explicação em PT-BR",
"suggested_fix": "ação concreta em PT-BR",
"action_priority": 1-5
}

**Template Sugestões de Evolução**:
Você é um estrategista de evolução para sistema de value betting.
Baseado nestes 30 dias de dados, sugira melhorias práticas:
Performance:
{stats_json}
Restrições do sistema:

Capital inicial: R$50 (Kelly 1/4)
Threshold EV atual: {current_threshold}
Ligas ativas: Brasileirão + Premier League
Custo zero (free tier Gemini)

Responda APENAS com JSON válido:
{
"evolution_suggestions": [
{
"category": "threshold" | "model" | "market" | "betting_strategy",
"suggestion": "descrição em PT-BR",
"expected_impact": "ex: roi_improvement: +0.5-2%",
"implementation": "1-2 linhas técnicas em PT-BR",
"risk": "low" | "medium" | "high"
}
],
"priority_changes": ["item1", "item2"],
"next_review_date": "YYYY-MM-DD"
}

#### 5.4 Pseudocódigo do Graceful Degradation

```python
async def validate_opportunity(self, opp, accuracy, roi):
    # Cache check
    opp_hash = self._hash_opportunity(opp)
    cached = self._get_cached_validation(opp_hash)
    if cached:
        return cached
    
    # Budget check
    if self.get_remaining_budget() < 1000:  # tokens
        return self._build_fallback("BUDGET_EXHAUSTED")
    
    # Sanity check periódico
    if not self._last_sanity_ok:
        return self._build_fallback("SANITY_FAILED")
    
    # Chamada com retry
    try:
        prompt = self._build_validation_prompt(opp, accuracy, roi)
        response = await self._call_gemini(prompt, timeout=10, retries=3)
        result = self._parse_json_response(response)
        self._cache_validation(opp_hash, result)
        return result
    
    except (TimeoutError, asyncio.TimeoutError) as e:
        return self._build_fallback("TIMEOUT", str(e))
    
    except RateLimitError as e:
        return self._build_fallback("RATE_LIMIT", str(e))
    
    except (GeminiParseError, json.JSONDecodeError) as e:
        return self._build_fallback("PARSE_ERROR", str(e))
    
    except Exception as e:
        logger.exception("Erro inesperado no GeminiValidator")
        return self._build_fallback("UNKNOWN", str(e))

def _build_fallback(self, reason: str, detail: str = "") -> dict:
    """Retorna estrutura segura quando Gemini falha."""
    return {
        'is_valid': None,
        'confidence': 0.0,
        'reasoning': f"Validação IA indisponível: {reason}",
        'recommendation': 'place_with_caution',
        'stake_adjustment': 0.5,  # Stake reduzido 50%
        'fallback_reason': f"{reason}: {detail}",
        'flag': 'SEM_VALIDACAO_IA',
        'tokens_used': 0,
        'response_time_ms': 0
    }
```

#### 5.5 Configuração

```python
# Configuração padrão
GEMINI_CONFIG = {
    'model': 'gemini-2.0-flash-exp',
    'temperature': 0.2,  # baixa para respostas consistentes
    'max_tokens': {
        'validation': 500,
        'anomaly': 800,
        'evolution': 1200
    },
    'timeout': 10,  # segundos
    'max_retries': 3,
    'backoff_seconds': [1, 2, 4],  # exponencial
    'cache_ttl_hours': 1,
    'monthly_token_limit': 1_600_000,  # 80% do free tier 2M
    'alert_threshold_pct': 80
}
```

#### 5.6 Requisitos de Performance

| Operação | Alvo | Como Medir |
|---|---|---|
| `validate_opportunity()` (cold) | < 5s p95 | Tempo total incl. API |
| `validate_opportunity()` (cached) | < 5ms | Cache hit |
| `detect_anomalies()` | < 8s p95 | API + parse |
| `suggest_evolution()` | < 10s p95 | API + parse |
| `_parse_json_response()` | < 50ms | Parsing puro |
| `is_available()` | < 2s | Health check rápido |

### 6. Critério de Aceitação (Módulo Completo)

- [ ] Histórias 04-001 a 04-011 todas concluídas.
- [ ] Cobertura de testes > 80% em funções públicas.
- [ ] **Todos os 12 testes adversariais da STORY-04-011 passando.**
- [ ] O `sanity_check` é executado na inicialização.
- [ ] Graceful degradation testado em 4 cenários (timeout, rate limit, parse error, sanity fail).
- [ ] O uso de tokens é < 80% do free tier (validado em 1 mês de operação).
- [ ] Logs estruturados permitem auditoria das decisões da IA.
- [ ] Documentação inline em PT-BR.

---

## 7. Dependências

- **Upstream**:
  - PRD-03 (ValueDetector): fornece oportunidades com EV > 5%.
  - PRD-02 (PoissonModel): fornece acurácia para contexto.
  - APScheduler: dispara `detect_anomalies` diariamente e `suggest_evolution` semanalmente.
  
- **Downstream**:
  - PRD-05 (AutoEvolution): consome anomalias e sugestões.
  - Telegram Bot: recebe alertas de anomalias críticas.

---

## 8. Decisions

### 8.1 Deferred Decisions
- Gemini Pro para validações críticas (EV > 10%): adiado; default v1 usa Gemini Flash para todas as validações.
- Fallback para Claude API se o Gemini ficar offline por mais de 1 hora: adiado; default v1 sem fallback externo, apenas graceful degradation.
- Cache de validações: adiado; default v1 mantém 1 hora.
- Aplicação automática de `risk='medium'`: adiado; default v1 preserva sugestão manual e não auto-aplica.

As decisões deferidas estão consolidadas em [`docs/decisions/deferred_decisions.md`](../decisions/deferred_decisions.md).

---

## 9. Consequências

Este PRD introduz uma camada de IA explicitamente subordinada ao fluxo determinístico do produto, o que muda o código em dois eixos: integração resiliente com um provedor externo e persistência detalhada das respostas para auditoria. O backend passa a precisar de clientes com timeout, retry, parser robusto, fallback seguro e controle de consumo de tokens como parte do comportamento padrão, não como hardening opcional.

No banco e nas integrações, a consequência é a criação de tabelas próprias para validações, anomalias, sugestões e orçamento mensal de tokens. Isso permite que PRD-05 consuma sinais da IA com rastreabilidade, ao mesmo tempo em que impede que falhas do provedor derrubem o pipeline principal de detecção e alerta.

Também fica definido que a IA atua como revisora contextual e mecanismo de observabilidade, não como fonte primária de verdade do sistema. Essa decisão restringe o design do código: toda chamada ao Gemini deve poder falhar sem quebrar contratos downstream e sem remover a capacidade do sistema de continuar operando em modo degradado.

## 10. Referências

- **Interna**:
    - ADR-003: Estratégia híbrida (lógica + IA) — [ADR-003](../architecture/adr_003_hybrid_logic_ai.md).
    - ADR-005: Por que Gemini Flash sobre alternativas — [ADR-005](../architecture/adr_005_llm_choice.md).
- **Externa**:
    - Documentação da Gemini API: `https://ai.google.dev/`.
    - Limites do free tier: `https://ai.google.dev/pricing`.
