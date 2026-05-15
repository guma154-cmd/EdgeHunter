# PRD-05: AutoEvolution

| Metadados | Valor |
|---|---|
| **ID** | PRD-05 |
| **Status** | Rascunho |
| **Responsável** | John (PM) |
| **Pai** | [PRD-00: Pivot de Value Betting](00_value_betting_pivot.md) |
| **Criado em** | 15/05/2026 |

---

## 1. Declaração do Problema

Os módulos anteriores (PRD-01 a 04) constituem a **infraestrutura analítica** do sistema — eles coletam dados, calculam probabilidades, detectam valor e validam com IA. No entanto, sem um **engine operacional** que tome decisões financeiras concretas e gerencie o ciclo de vida do sistema, essa infraestrutura permanece inerte, sem gerar resultados práticos.

O `AutoEvolution` preenche essa lacuna, atuando como o maestro da orquestra:
- Decide **quanto** apostar (usando Kelly Criterion e gerenciando o bankroll).
- Decide **quando** avançar entre as fases do Cold Start.
- Decide **quando** pausar o sistema para proteção (usando o Circuit Breaker).
- Permite **controle humano** e overrides manuais via comandos do Telegram.
- **Aplica sugestões de melhoria** do GeminiValidator automaticamente (se o risco for baixo).

Sem este módulo, o sistema gera insights, mas não possui a governança operacional para transformá-los em um processo de investimento estruturado e auto-otimizado.

---

## 2. Metas

- **Ajuste de Threshold**: O threshold de EV deve se auto-ajustar em menos de 24 horas após uma mudança significativa no ROI.
- **Cálculo de Stake**: O stake calculado pelo Kelly Criterion deve ser sempre correto (usando fração 1/8 ou 1/4, conforme a fase) e nunca exceder 5% do bankroll.
- **Deduplicação de Alertas**: Garantir zero alertas duplicados para a mesma oportunidade.
- **Integração Não-Disruptiva**: Adicionar os 4 novos jobs ao scheduler existente sem quebrar a funcionalidade atual de surebets.
- **Ativação do Circuit Breaker**: O sistema deve ser pausado em menos de 1 minuto após a detecção de 3 perdas consecutivas.
- **Responsividade do Telegram**: Todos os comandos do Telegram devem ter uma resposta em menos de 3 segundos.

---

## 3. Não-Metas

- **Apostas Autônomas**: Este módulo NÃO realizará apostas de forma autônoma. A decisão final de colocar a aposta sempre será do operador humano após receber o alerta.
- **Ajuste de Modelo**: NÃO ajustará os parâmetros internos do `PoissonModel`. O retreinamento do modelo é responsabilidade do PRD-02.
- **Modificação da Detecção**: NÃO modificará a lógica de detecção de valor do `ValueDetector` (PRD-03).
- **Chamadas Desnecessárias à IA**: NÃO chamará o Gemini para cada decisão; o uso será estritamente para anomalias e sugestões de evolução.
- **Substituição do Operador Humano**: NÃO substituirá a decisão humana em cenários críticos (por exemplo, stakes acima de R$10).

---

## 4. Histórias de Usuário

- [ ] **STORY-05-001**: Calcular ROI (7d, 30d, all-time)
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Função `calculate_roi(days: int) -> float`.
    - Considera apenas apostas finalizadas (status 'win', 'loss', 'push').
    - Fórmula: `sum(profit_loss) / sum(stake)`.
    - Retorna `0.0` se não houver apostas no período (não deve retornar NaN ou erro).
    - Performance da query < 100ms.

- [ ] **STORY-05-002**: Regras determinísticas de ajuste de threshold
  - **Status**: a fazer | **Estimativa**: 4h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Lógica implementada:
      - Se ROI 7d < -5%, então `threshold += 0.5%`.
      - Se ROI 7d > 15%, então `threshold -= 0.2%`.
      - Se ROI 30d < 0% E ROI 7d < 0%, então `threshold += 1%`.
    - O valor do threshold é sempre mantido ("clipped") no intervalo [1.5%, 8%].
    - Todas as mudanças são registradas na tabela `evolution_history`.
    - Um alerta é enviado via Telegram sempre que o threshold muda.

- [ ] **STORY-05-003**: Kelly Criterion (frações 1/8 e 1/4)
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Função `kelly_stake(odds, true_prob, bankroll, fraction) -> float`.
    - Usa a fórmula de Kelly: `f* = (b*p - q) / b`, onde `b = odds - 1`, `p = true_prob`, `q = 1 - p`.
    - Aplica a fração correta: 1/8 (Fase 3a) ou 1/4 (Fase 3b).
    - Stake = `bankroll * f* * fraction`.
    - O valor do stake é sempre mantido ("clipped") entre um mínimo de R$2 e um máximo de 3% (Fase 3a) ou 5% (Fase 3b) do bankroll.
    - O stake é 0 se o cálculo de Kelly for negativo.
    - O stake final é randomizado em ±10% para evitar limitação de conta (anti-account-limit).

- [ ] **STORY-05-004**: Bankroll Manager com floor e override manual
  - **Status**: a fazer | **Estimativa**: 4h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Classe `BankrollManager(initial=50.0, floor=30.0)`.
    - Método `update_after_bet(profit_loss)` ajusta o bankroll e aplica a proteção de "floor".
    - Se o bankroll cair abaixo do "floor", um alerta do Telegram é disparado e o sistema é pausado.
    - Método `manual_set(value)` permite override via comando `/bankroll` no Telegram.
    - O estado do bankroll é persistido na tabela `bankroll_state` e pode ser recuperado após um restart.
    - O histórico completo das mudanças é mantido na tabela `bankroll_history`.

- [ ] **STORY-05-005**: Circuit Breaker (proteção contra losing streaks)
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Pausa automaticamente o sistema em 3 cenários: 3 perdas consecutivas, 5 perdas em 7 dias, ou drawdown > 30% do bankroll.
    - "Pausar" significa que nenhum alerta de aposta é enviado, mas as detecções continuam sendo logadas.
    - O operador deve usar o comando `/resume` para reativar o envio de alertas.
    - Um alerta detalhado do Telegram é enviado quando o Circuit Breaker é ativado.

- [ ] **STORY-05-006**: Integração com scheduler (4 novos jobs)
  - **Status**: a fazer | **Estimativa**: 4h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - JOB 1 (a cada 15min, anexado ao `fetch_odds`): `value_betting_cycle()` - o ciclo principal.
    - JOB 2 (diário @ 06:00 UTC): `daily_auto_evolution()` - ajusta threshold e chama Gemini para anomalias.
    - JOB 3 (semanal Dom @ 22:00 UTC): `weekly_evolution_review()` - chama Gemini para sugestões e aplica as de baixo risco.
    - JOB 4 (diário @ 04:30 UTC): `daily_phase_check()` - avalia critérios de avanço entre as fases do Cold Start.
    - A integração não deve quebrar os jobs existentes do scheduler (surebets).

- [ ] **STORY-05-007**: Comandos Telegram /bankroll, /pause, /resume
  - **Status**: a fazer | **Estimativa**: 5h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - `/bankroll <valor>`: define o bankroll manualmente e envia confirmação.
    - `/bankroll` (sem argumento): mostra o valor atual e o ROI.
    - `/pause`: suspende o envio de alertas.
    - `/resume`: reativa o envio de alertas.
    - `/status`: exibe um resumo do estado do sistema (bankroll, fase, ROI, threshold, estado do circuit breaker).
    - Os comandos respondem em menos de 3 segundos.
    - Apenas o `chat_id` configurado no `.env` é autorizado a usar os comandos.

- [ ] **STORY-05-008**: Alerta do Telegram para value detection (formatado)
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - O template do alerta inclui: partida, EV%, odds, stake calculado e validação do Gemini (se houver).
    - Usa emojis visuais: ✅ se validado pelo Gemini, ⚠️ se a validação falhou.
    - Inclui um link clicável para a página do jogo (se disponível).
    - Inclui botões inline: "Apostei" / "Ignorei" (usando `InlineKeyboard`).
    - A flag `alerted` é marcada como `True` na tabela `value_detections` para garantir deduplicação.

- [ ] **STORY-05-009**: Tracking de apostas realizadas (via Telegram)
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - O callback do botão "Apostei" registra a aposta na tabela `placed_bets`.
    - O status inicial da aposta é 'pending'.
    - Após o resultado da partida ser obtido, o status é atualizado para 'win', 'loss' ou 'push'.
    - O campo `profit_loss` é calculado automaticamente.
    - O bankroll é atualizado chamando `update_after_bet`.

- [ ] **STORY-05-010**: Critérios de avanço entre fases (Cold Start)
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Função `check_phase_advancement() -> Optional[str]`.
    - Fase 2 → 3a: `ROI paper >= +2%` E `paper_bets_count >= 20` (últimas 2 semanas).
    - Fase 3a → 3b: `ROI real >= 0%` E `real_bets_count >= 20` (últimos 30 dias).
    - Retrocesso: Se na fase 3a o `ROI < -10%` E `real_bets >= 10`, o sistema volta para a fase 2.
    - Cada mudança de fase gera um log e um alerta no Telegram.

- [ ] **STORY-05-011**: Aplicação automática de sugestões Gemini (risk='low')
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: média
  - **Critério de Aceitação**:
    - Lê sugestões da tabela `gemini_evolution_suggestions`.
    - Filtra apenas por `risk='low'` e que ainda não foram aplicadas.
    - Aplica as mudanças conforme a categoria (ex: `threshold`, `betting_strategy`).
    - Marca a sugestão como `applied_auto=True` na tabela.
    - Envia um alerta detalhado via Telegram com a mudança que foi aplicada.

- [ ] **STORY-05-012**: Resumo semanal automático via Telegram
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: média
  - **Critério de Aceitação**:
    - Todo domingo às 22:00 UTC, envia um resumo da semana.
    - O resumo inclui: ROI 7d, total de apostas, top vitórias/derrotas, mudanças de threshold e fase atual.
    - Sugestões do Gemini com `risk='medium'` ou `risk='high'` são listadas para revisão manual.

- [ ] **STORY-05-013**: Sanity check do AutoEvolution
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Verificações na inicialização:
      1. Bankroll persistido > 0 (carregado do DB).
      2. Fase atual é válida ('1', '2', '3a', '3b').
      3. Os 4 novos jobs do scheduler estão registrados.
      4. O bot do Telegram está responsivo (via mensagem de teste).
      5. `ValueDetector` e `GeminiValidator` estão inicializados.
    - Se falhar, um log crítico é gerado, um alerta é enviado ao Telegram e os jobs são bloqueados.

- [ ] **STORY-05-014**: Testes unitários e adversariais
  - **Status**: a fazer | **Estimativa**: 6h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Cobertura de testes > 85% em funções públicas.
    - **Testes Adversariais OBRIGATÓRIOS** (devem passar):
      ` + "`" + `` + "`" + `` + "`" + `python
      def test_kelly_zero_when_negative_expected_value():
          """Kelly retorna 0 se EV < 0 (não apostar)"""
      
      def test_kelly_clipped_at_max_pct():
          """Kelly nunca excede max% do bankroll"""
      
      def test_kelly_minimum_2_brl():
          """Stake calculado < R$2 é forçado a R$2"""
      
      def test_bankroll_floor_protection():
          """Bankroll < R$30 dispara pause + alert"""
      
      def test_circuit_breaker_3_consecutive_losses():
          """3 losses seguidas: auto-pause"""
      
      def test_circuit_breaker_5_losses_in_7days():
          """5 losses em 7 dias: auto-pause mesmo não consecutivas"""
      
      def test_phase_advancement_requires_min_sample():
          """Fase 2 → 3a: 5 paper bets com ROI 10% NÃO avança (min 20)"""
      
      def test_phase_retrocession_on_severe_loss():
          """Fase 3a com ROI -15% em 15 bets: volta para Fase 2"""
      
      def test_threshold_clipped_at_min_1_5_pct():
          """Threshold nunca < 1.5% mesmo em winning streak"""
      
      def test_threshold_clipped_at_max_8_pct():
          """Threshold nunca > 8% mesmo em losing streak"""
      
      def test_telegram_command_unauthorized_chat_id_rejected():
          """Comando de chat_id não autorizado: ignorado + log warning"""
      
      def test_pause_doesnt_stop_detection():
          """Pause: detecções continuam, apenas alerts pausam"""
      
      def test_resume_doesnt_send_old_alerts():
          """Resume: alerts pendentes da pause não são enviados (dedup)"""
      
      def test_stake_randomization_within_10_pct():
          """Stake randomizado: sempre ±10% do calculado"""
      
      def test_dedup_within_alert_window():
          """Mesmo opp em 1h: apenas 1 alert"""
      ` + "`" + `` + "`" + `` + "`" + `

---

## 5. Especificação Técnica

#### 5.1 Schema de Banco de Dados

` + "`" + `` + "`" + `` + "`" + `sql
-- Apostas realizadas (manual tracking via Telegram callback)
CREATE TABLE IF NOT EXISTS placed_bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detection_id INTEGER NOT NULL,  -- FK para value_detections
    
    match_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    bookmaker TEXT NOT NULL,
    odds REAL NOT NULL,
    stake REAL NOT NULL,
    
    status TEXT DEFAULT 'pending',  -- 'pending', 'win', 'loss', 'push', 'cancelled'
    return_amount REAL,
    profit_loss REAL,  -- (return - stake) ou -stake se loss
    
    phase TEXT NOT NULL,  -- '1', '2', '3a', '3b'
    is_paper_bet BOOLEAN DEFAULT 0,  -- True nas fases 1 e 2
    
    placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    
    FOREIGN KEY (detection_id) REFERENCES value_detections(id)
);

CREATE INDEX IF NOT EXISTS idx_placed_bets_status ON placed_bets(status, placed_at);
CREATE INDEX IF NOT EXISTS idx_placed_bets_phase ON placed_bets(phase, placed_at);

-- Histórico de evolução do sistema
CREATE TABLE IF NOT EXISTS evolution_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    action_type TEXT NOT NULL,  -- 'threshold_change', 'phase_advance', 'phase_retrocede', 'circuit_breaker', 'manual_override'
    action_taken TEXT NOT NULL,
    reason TEXT,
    
    old_value TEXT,  -- JSON
    new_value TEXT,  -- JSON
    
    roi_7d REAL,
    roi_30d REAL,
    gemini_consulted BOOLEAN DEFAULT 0,
    gemini_suggestion_id INTEGER,  -- FK opcional para gemini_evolution_suggestions
    
    triggered_by TEXT,  -- 'auto', 'telegram_user', 'circuit_breaker'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Estado atual do bankroll (1 row apenas, sempre atualizada)
CREATE TABLE IF NOT EXISTS bankroll_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- enforce single row
    current_bankroll REAL NOT NULL,
    floor REAL DEFAULT 30.0,
    initial REAL DEFAULT 50.0,
    
    current_phase TEXT NOT NULL DEFAULT '1',  -- '1', '2', '3a', '3b'
    current_threshold REAL DEFAULT 0.02,
    kelly_fraction REAL DEFAULT 0.25,  -- 1/4 default, 1/8 em 3a
    
    is_paused BOOLEAN DEFAULT 0,
    pause_reason TEXT,
    
    manual_override BOOLEAN DEFAULT 0,
    last_manual_update TIMESTAMP,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Histórico de mudanças de bankroll
CREATE TABLE IF NOT EXISTS bankroll_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    old_value REAL NOT NULL,
    new_value REAL NOT NULL,
    delta REAL NOT NULL,
    
    triggered_by TEXT,  -- 'bet_settled', 'manual_override', 'phase_change'
    related_bet_id INTEGER,  -- FK opcional para placed_bets
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
` + "`" + `` + "`" + `` + "`" + `

#### 5.2 Contrato de API

` + "`" + `` + "`" + `` + "`" + `python
from typing import Optional, Dict, List, Literal
from datetime import datetime

Phase = Literal['1', '2', '3a', '3b']
ActionType = Literal['threshold_change', 'phase_advance', 'phase_retrocede', 
                     'circuit_breaker', 'manual_override']

class AutoEvolutionEngine:
    """Engine de auto-evolução: threshold, phases, circuit breaker."""
    
    def __init__(
        self,
        db_path: str = "edge_hunter.db",
        min_threshold: float = 0.015,
        max_threshold: float = 0.08
    ): ...
    
    def calculate_roi(self, days: int, paper_only: bool = False) -> float:
        """ROI baseado em placed_bets finalizadas."""
    
    async def daily_auto_evolution(self) -> Dict:
        """Roda diariamente @ 06:00 UTC. Ajusta threshold + chama Gemini para anomalies."""
    
    async def weekly_evolution_review(self) -> Dict:
        """Roda Dom @ 22:00 UTC. Chama Gemini para sugestões + auto-aplica risk='low'."""
    
    def check_phase_advancement(self) -> Optional[Phase]:
        """Avalia critérios de avanço. Retorna nova phase ou None."""
    
    def check_circuit_breaker(self) -> Optional[str]:
        """Verifica losing streaks. Retorna razão de pause ou None."""

class BankrollManager:
    """Gerenciador de bankroll com floor e override manual."""
    
    def __init__(self, initial: float = 50.0, floor: float = 30.0): ...
    
    def update_after_bet(self, profit_loss: float, bet_id: int) -> None: ...
    def manual_set(self, value: float, user_id: str) -> None: ...
    def get_current_bankroll(self) -> float: ...
    def get_state(self) -> Dict: ...

class KellyCalculator:
    """Calcula stake via Kelly Criterion."""
    
    @staticmethod
    def kelly_stake(
        odds: float,
        true_prob: float,
        bankroll: float,
        fraction: float = 0.25,  # 1/4 default
        min_stake: float = 2.0,
        max_pct: float = 0.05  # 5% max default
    ) -> float: ...

class TelegramCommands:
    """Handlers para comandos /bankroll, /pause, /resume, /status."""
    
    def __init__(self, bot_token: str, authorized_chat_id: str): ...
    
    async def handle_bankroll(self, message) -> None: ...
    async def handle_pause(self, message) -> None: ...
    async def handle_resume(self, message) -> None: ...
    async def handle_status(self, message) -> None: ...
` + "`" + `` + "`" + `` + "`" + `

#### 5.3 Templates Telegram (PT-BR)

**Alert de Value Detection**:
✅ VALUE DETECTADO {emoji_validacao}
📊 {match} ({league})
{outcome_emoji} {outcome_text}
🏢 {bookmaker} @ {odds}
🎯 EV: +{edge_pct}% (Fonte: {detection_source})
💸 Stake Sugerido: R$ {stake}
💰 Bankroll Atual: R$ {bankroll}
📈 Fase: {phase}
{gemini_section}
⏰ Detectado: {timestamp}

Onde `{gemini_section}` é:
- Se validated: `🤖 Validação IA: {confidence}% confiança — {recommendation}`
- Se fallback: `⚠️ SEM VALIDAÇÃO IA — stake reduzido 50%`

**Alert Circuit Breaker**:
🛑 CIRCUIT BREAKER ATIVADO
Razão: {reason}
Bankroll Atual: R$ {bankroll}
Drawdown: -{drawdown_pct}%
Sistema PAUSADO automaticamente.
Use /resume para reativar após análise.
📊 Estatísticas:

Últimas 7 dias: {wins}W / {losses}L
ROI 7d: {roi_7d}%
ROI 30d: {roi_30d}%


**Alert Mudança de Fase**:
🚀 AVANÇO DE FASE
De: Fase {old_phase}
Para: Fase {new_phase}
✅ Critérios atendidos:

ROI: {roi}%
Total bets: {bets_count}

Novos parâmetros:

Threshold: {new_threshold}%
Kelly: 1/{kelly_denom}
Max stake: {max_pct}% bankroll

Parabéns! 🎉

**Weekly Review**:
📊 RESUMO SEMANAL — {week_range}
💰 Bankroll: R$ {bankroll} ({delta:+.2f})
📈 ROI 7d: {roi_7d}% | ROI 30d: {roi_30d}%
🎯 Fase: {phase} | Threshold: {threshold}%
📌 Apostas:

Total: {total_bets} ({wins}W / {losses}L)
Win rate: {win_rate}%
Top Win: {top_win}
Top Loss: {top_loss}

🔄 Mudanças aplicadas:
{evolution_changes}
🤖 Sugestões Gemini (revisar manualmente):
{gemini_suggestions_medium_high}

#### 5.4 Pseudocódigo do Cycle Principal

` + "`" + `` + "`" + `` + "`" + `python
async def value_betting_cycle():
    """Job principal — roda a cada 15min após fetch_odds."""
    
    # 1. Check circuit breaker
    if bankroll_state.is_paused:
        log.info("Sistema pausado, skip cycle")
        return
    
    # 2. Detectar oportunidades
    opportunities = value_detector.find_value_opportunities(recent_minutes=30)
    
    if not opportunities:
        return
    
    # 3. Para cada opp, processar
    for opp in opportunities:
        # 3a. Dedup
        if value_detector.is_duplicate(...):
            continue
        
        # 3b. Validação Gemini se EV > 5%
        if opp['edge_percent'] > 5.0:
            opp['gemini_validation'] = await gemini.validate_opportunity(opp, ...)
            
            # Se Gemini falhou: stake reduzido 50%
            if opp['gemini_validation'].get('flag') == 'SEM_VALIDACAO_IA':
                stake_multiplier = 0.5
            elif not opp['gemini_validation'].get('is_valid'):
                continue  # Gemini disse skip
            else:
                stake_multiplier = opp['gemini_validation'].get('stake_adjustment', 1.0)
        else:
            stake_multiplier = 1.0  # Sem validação para EV pequeno
        
        # 3c. Calcular stake (Kelly)
        true_prob = max(opp.get('pinnacle_prob') or 0, opp.get('model_prob') or 0)
        stake = KellyCalculator.kelly_stake(
            odds=opp['offered_odds'],
            true_prob=true_prob,
            bankroll=bankroll_manager.get_current_bankroll(),
            fraction=bankroll_state.kelly_fraction
        ) * stake_multiplier
        
        if stake < 2.0:
            continue  # Stake muito pequeno
        
        # 3d. Persistir bet (status='pending') se fase 3a/3b
        if bankroll_state.current_phase in ['3a', '3b']:
            # Bets reais
            bet_id = save_pending_bet(opp, stake)
        else:
            # Paper bet
            bet_id = save_paper_bet(opp, stake)
        
        # 3e. Telegram alert
        await telegram_alerts.send_value_alert(opp, stake, bet_id)
        
        # 3f. Marcar como alerted
        value_detector.mark_as_alerted(opp['detection_id'])
` + "`" + `` + "`" + `` + "`" + `

#### 5.5 Requisitos de Performance

| Operação | Alvo | Como Medir |
|---|---|---|
| `calculate_roi(7d)` | < 100ms | benchmark |
| `kelly_stake()` | < 1ms | função pura |
| `value_betting_cycle()` (10 opps) | < 30s | E2E |
| Comando Telegram | < 3s | resposta usuário |
| `check_phase_advancement()` | < 200ms | query DB |
| `check_circuit_breaker()` | < 100ms | query DB |

---

## 6. Critério de Aceitação (Módulo Completo)

- [ ] Histórias 05-001 a 05-014 todas concluídas.
- [ ] Cobertura de testes > 85% em funções públicas.
- [ ] **Todos os 15 testes adversariais da STORY-05-014 passando.**
- [ ] Sanity check executando no startup.
- [ ] Integração com scheduler existente não quebra surebets.
- [ ] Comandos Telegram autorizados apenas para chat_id do .env.
- [ ] Circuit Breaker testado em 3 cenários reais.
- [ ] Phase advancement testado com paper trading simulado.

---

## 7. Dependências

- **Upstream**: TODOS os PRDs anteriores
  - PRD-01 (OddsHistorian): match_results para calcular outcomes
  - PRD-02 (PoissonModel): accuracy para context
  - PRD-03 (ValueDetector): opportunities + dedup
  - PRD-04 (GeminiValidator): validation + anomalies + suggestions

- **Downstream**: Nenhum (é o módulo final)
  - Operador humano: recebe alerts e toma decisões
  - Telegram Bot: canal único de comunicação

---

## 8. Questões em Aberto

- Multi-bankroll por liga (separar Brasileirão de PL): valeria a pena?
- Backup de bankroll_state em arquivo (proteção contra DB corruption)?
- Comando Telegram /backtest para rodar análise histórica sob demanda?
- Auto-resume após pause? (Ex: pause de 24h vira resume automaticamente)
- Notificações via push (além de Telegram) — futuro?

---

## 9. Referências

- **Interna**: ADR-003: Estratégia híbrida (lógica + IA) — a ser criado.
- **Externa**:
    - Kelly Criterion: Thorp, E. O. "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market"
    - PRD-00 Section 11.1 Gap 5: Bankroll híbrido
    - PRD-04: Interface com GeminiValidator
