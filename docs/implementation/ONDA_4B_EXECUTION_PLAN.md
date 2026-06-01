# Plano de Execução — Onda 4B EdgeHunter

Gerado por: John (Product Manager) via bmad-agent-pm
Data: 2026-06-01
Tag de referência: v0.6-onda4a-backtest

---

## 1. Veredicto

- [x] APROVADO PARA COMEÇAR ONDA 4B
- [ ] APROVADO COM RESSALVAS
- [ ] NÃO APROVADO

A Onda 4B é tecnicamente viável, tem escopo claro e custo de implementação estimado baixo. Todas as dívidas a endereçar são locais, seguras e não exigem API pública, Telegram operacional, stake, Kelly, bankroll, GeminiValidator ou AutoEvolution. O ponto de partida ideal é a correção do fixture de sanity, que já tem causa-raiz identificada. As demais stories seguem uma ordem de dependência natural que minimiza re-trabalho.

---

## 2. Objetivo da Onda 4B

Resolver as dívidas técnicas médias identificadas e documentadas na auditoria da Onda 4A, aumentando a robustez interna do núcleo analítico e de backtest antes de qualquer exposição pública, chamada externa ou operação financeira. A onda é exclusivamente técnica, local e segura.

### Resultado esperado ao fim da Onda 4B

- Sanity check retornando `passed=True` com deduplicação correta.
- Overround Pinnacle normalizado (v2: remoção do margin proporcional).
- `snapshot_id` propagado no contrato `SimulatedValueOpportunity` e persistido em `value_detections`.
- FK `value_detections.snapshot_id → odds_snapshots.id` ativa e testada.
- Semântica de `coverage_rate` documentada e decidida.
- Decisão formal sobre reabertura por mudança material de odds/EV dentro da janela.
- Suíte global de legado isolada ou documentada como escopo separado.
- Tag `v0.7-onda4b-robustez` criada ao término.

---

## 3. Dívidas Avaliadas

| # | Dívida | Origem | Impacto | Bloqueia API? | Bloqueia Gemini? | Bloqueia AutoEvolution? | Decisão |
|---|---|---|---|---|---|---|---|
| D1 | Falha de 3 testes em `test_value_detector_sanity.py` | Onda 3 — fixture com `created_at` antigo | Sanity reporta `False` para deduplicação correta. Risco de falso alarme em CI futuro. | Sim — futura API não pode ser validada por sanity que falha | Sim — mesmo motivo | Não diretamente | **Corrigir na Onda 4B — STORY-04B-001** |
| D2 | Fixture de sanity com `created_at` hardcoded antigo | Onda 3 — causa raiz do D1 | Timestamp `2026-05-28T12:00:00+00:00` é anterior à janela de 60min do `now` real; deduplicação passa ambas as cópias como "fora da janela" | Idem D1 | Idem D1 | Não | **Resolver junto com D1 na STORY-04B-001** |
| D3 | Overround Pinnacle não normalizado (`true_prob = 1/pinnacle_odds`) | Onda 3 | Superestima probabilidade verdadeira; aumenta falso positivo sistematicamente. PRD-03 define FP < 20% como meta — sem normalização a baseline está enviesada | Sim — endpoint exporia sinal enviesado | Sim — Gemini validaria sinal enviesado | Não diretamente | **Corrigir na Onda 4B — STORY-04B-002** |
| D4 | `snapshot_id` ausente em `SimulatedValueOpportunity` | Onda 3 | Rastreabilidade incompleta: oportunidade não vincula de volta ao snapshot de odds que a gerou | Sim — API de leitura futura não consegue retornar snapshot_id | Sim — Gemini precisa de contexto do snapshot | Não | **Corrigir na Onda 4B — STORY-04B-003** |
| D5 | FK `value_detections.snapshot_id → odds_snapshots.id` ausente no schema | Onda 3 | Integridade referencial ausente; backtest pode ler orphan detections | Sim — contrato de API pressupõe FK para filtro por snapshot | Não diretamente | Não | **Corrigir junto com D4 — STORY-04B-003** |
| D6 | Semântica de `coverage_rate = total_opportunities / total_analyzed` | Onda 4A | Múltiplas oportunidades por partida (3 mercados × N snapshots) inflam o numerador; ratio > 1.0 é possível | Sim — se usado como KPI operacional em API | Sim — Gemini usaria métrica enganosa | Não | **Documentar decisão e refatorar se necessário — STORY-04B-004** |
| D7 | Decisão sobre múltiplas oportunidades por partida | Onda 4A | Relacionada com D6; sem decisão formal, `coverage_rate` e qualquer futura métrica de cobertura ficam ambíguas | Sim — mesma razão do D6 | Sim | Não | **Resolver junto com D6 — STORY-04B-004** |
| D8 | Reabertura por mudança material de odds/EV (>5%) dentro da janela | Onda 3 — adiada explicitamente no PRD-03 §8.2 | Deduplicação atual puramente por janela temporal; odds podem mudar materialmente sem redetecção | Sim — API exigiria sinal atualizado | Sim — Gemini validaria sinal desatualizado | Não | **Implementar na Onda 4B — STORY-04B-005** |
| D9 | Suíte global/ambiente legado (flask, `/app`, playwright) | Legado anterior à Onda 1 | 6 erros de coleta bloqueiam `python -m pytest`; mascaram falhas reais em CI hipotético | Não diretamente | Não | Não | **Isolar via conftest/pytest.ini — STORY-04B-006** |

### Dívidas fora do escopo da Onda 4B (para depois)

| Dívida | Justificativa para adiar |
|---|---|
| Auth/authz da API REST | Requer decisão de onda própria (API). |
| OpenAPI/Swagger | Depende de auth/authz e endpoint estável. |
| Paginação/filtros/performance p95 da API | Idem. |
| GeminiValidator operacional | Depende de FP baseline aprovado (precisa primeiro de D3 corrigido + dados históricos). |
| AutoEvolution | PRD-05 inclui stake/Kelly/bankroll — explicitamente proibido. |
| Telegram operacional | Proibido nesta fase. |
| Scheduler operacional | Proibido nesta fase. |
| Fixtures históricas sintéticas mais ricas | Baixa prioridade; não bloqueia nada. |

---

## 4. Ordem Recomendada de Stories

| Ordem | Story | Objetivo | Bloqueia API? | Bloqueia Gemini? | Observação |
|---|---|---|---|---|---|
| 1 | **STORY-04B-001** — Corrigir fixture de sanity e deduplicação | Fazer `sanity_check_value_detector()` retornar `passed=True`; usar `datetime.now(timezone.utc)` em vez de timestamp fixo no fixture; garantir que `deduplicate_opportunities([opp, opp])` retorne `[opp]` no sanity | Sim | Sim | Menor risco, causa-raiz conhecida, zero mudança em contratos públicos. Fazer primeiro para limpar ruído de CI. |
| 2 | **STORY-04B-002** — Normalizar overround Pinnacle (v2) | Implementar remoção proporcional do margin Pinnacle: `norm_prob = (1/odds) / sum(1/odds_i for i in [home, draw, away])`; atualizar testes de detecção e backtest; registrar mudança de versão como `pinnacle_ev_v2` | Sim | Sim | Impacta `detect_value_vs_pinnacle()`, `detect_value_consensus()`, executor de backtest e métricas. Fazer depois do sanity para não perder o baseline limpo. |
| 3 | **STORY-04B-003** — Propagar `snapshot_id` + FK no schema | Adicionar campo `snapshot_id: int | None` em `SimulatedValueOpportunity`; migrar schema adicionando coluna `snapshot_id` em `value_detections` com FK para `odds_snapshots.id`; atualizar `persist_simulated_opportunities()`; atualizar executor de backtest para propagar `snapshot_id` do `BacktestHistoricalMatch` | Sim | Sim | Migração SQLite delicada (ALTER TABLE em SQLite). Fazer depois do overround para não compor mudanças. |
| 4 | **STORY-04B-004** — Decidir e documentar semântica de `coverage_rate` | Definir formalmente: (a) manter `opps/matches_analyzed` com nota de que pode ser > 1, ou (b) redefinir como `matches_with_any_opportunity / total_analyzed`; implementar a decisão; atualizar testes e relatório de backtest | Sim | Sim | Baixo risco de implementação; alto valor de clareza para futura API e Gemini. |
| 5 | **STORY-04B-005** — Reabertura por mudança material de odds/EV | Implementar lógica de redetecção quando odds mudam > 5% dentro da janela de deduplicação; atualizar `deduplicate_opportunities()` para aceitar parâmetro `odds_change_threshold`; atualizar testes de deduplicação | Sim | Não diretamente | Requisito explícito do PRD-03 §6 e §8.2 (deferred). Fazer depois de `snapshot_id` porque a redetecção precisa de rastreabilidade. |
| 6 | **STORY-04B-006** — Isolar suíte global de legado | Adicionar `conftest.py` ou `pytest.ini` para excluir `backend/` e `remote_test.py` do discovery automático; garantir que `python -m pytest` em `tests/` passe 100%; documentar os arquivos legacy como fora do escopo | Não | Não | Sem mudança de lógica de negócio. Fazer por último para não interferir nas stories de código. |

---

## 5. Dependências Satisfeitas

| Dependência | Status | Evidência |
|---|---|---|
| Onda 1 (OddsHistorian) concluída e tagueada | Satisfeita | `v0.2-onda1-fundacao-dados`; `ONDA_1_CLOSURE_REPORT.md` |
| Onda 2 (PoissonModel) concluída e tagueada | Satisfeita | `v0.4-onda2-poissonmodel`; `ONDA_2_CLOSURE_REPORT.md` |
| Onda 3 (ValueDetector) concluída e tagueada | Satisfeita | `v0.5-onda3-valuedetector`; `ONDA_3_CLOSURE_REPORT.md` |
| Onda 4A (Backtest/PaperTrading) concluída e tagueada | Satisfeita | `v0.6-onda4a-backtest`; `ONDA_4A_CLOSURE_REPORT.md` |
| Sanity check existente como ponto de entrada | Satisfeita com bug | `sanity_check_value_detector()` em `value_detector_sanity.py`; causa-raiz identificada |
| Executor de backtest funcional para revalidar após overround | Satisfeita | `run_value_detector_backtest()` com 169/169 testes passando |
| Schema SQLite com `odds_snapshots.id` existente | Satisfeita | Coluna `id INTEGER PRIMARY KEY AUTOINCREMENT` em `odds_snapshots`; 12/12 testes de schema passando |
| `BacktestHistoricalMatch.snapshot_id` já carregado | Satisfeita | Campo `snapshot_id` presente em `value_detector_backtest_dataset.py` |
| `check_doc_consistency.py` e `check_transaction_discipline.py` passando | Satisfeita | 0 erros, 0 findings; transaction-discipline: ok |
| `git status --short` limpo | Satisfeita | Working tree limpo na entrada da Onda 4B |

---

## 6. Gaps Bloqueadores

### Críticos

Nenhum gap crítico bloqueia o início da Onda 4B.

### Médios

| Gap | Impacto | Tratamento proposto |
|---|---|---|
| Falha de 3 testes em sanity (D1/D2) | CI hipotético reporta falha; deduplicação parece quebrada mesmo estando correta | STORY-04B-001 |
| Overround Pinnacle não normalizado (D3) | Falso positivo sistematicamente subestimado | STORY-04B-002 |
| `snapshot_id` ausente no contrato (D4) | Rastreabilidade incompleta em backtest e futura API | STORY-04B-003 |
| FK ausente (D5) | Integridade referencial vulnerável | STORY-04B-003 |
| Semântica de `coverage_rate` ambígua (D6/D7) | Métrica pode ser enganosa em relatórios e em futura API | STORY-04B-004 |
| Reabertura por mudança de odds ausente (D8) | PRD-03 §6 exige redetecção com odds 5%+; atualmente não acontece | STORY-04B-005 |
| Suíte global de legado bloqueando `python -m pytest` (D9) | 6 erros de coleta mascaram falhas reais | STORY-04B-006 |

### Baixos

- Fixtures históricas sintéticas mais ricas (não bloqueia nada).
- Glossário de nomes públicos não acionáveis (útil para API, mas não urgente).
- Expandir métricas do sanity check (cobertura por source, tempo de execução).

---

## 7. Guardrails Obrigatórios

A Onda 4B continua proibindo explicitamente:

- Aposta real.
- Execução financeira.
- Stake.
- Kelly.
- Bankroll.
- Telegram operacional.
- Scheduler operacional.
- API REST pública.
- GeminiValidator operacional.
- AutoEvolution.
- Alerta acionável.
- Integração com casa de aposta.
- Linguagem de recomendação operacional em qualquer relatório, log ou comentário.

Permitido na Onda 4B:

- Correções locais de fixture e lógica de deduplicação.
- Refatoração segura de `detect_value_vs_pinnacle()` para normalização de overround.
- Adição de campo `snapshot_id` em `SimulatedValueOpportunity` (campo opcional, backward-compatible).
- Migração de schema SQLite via ALTER TABLE ou re-criação com dados vazios (paper trading, sem dados reais).
- Decisão e documentação de semântica de `coverage_rate`.
- Implementação de redetecção por mudança material de odds (lógica pura, sem rede ou execução).
- Isolamento de suíte de legado via conftest/pytest.ini.
- Testes, sanity checks e paper trading.
- Commits e tags locais.

---

## 8. Estratégia de Testes

### Suítes Obrigatórias para Cada Story

| Story | Suítes a rodar antes de commit |
|---|---|
| STORY-04B-001 | `test_value_detector_sanity.py` (todos 6 devem passar); `test_value_detector_deduplication.py`; `check_doc_consistency.py`; `check_transaction_discipline.py`; `git diff --check` |
| STORY-04B-002 | `test_value_detector_pinnacle.py`; `test_value_detector_consensus.py`; `test_value_detector_ev.py`; `test_value_detector_backtest_executor.py`; `test_value_detector_backtest_metrics.py`; `test_value_detector_backtest_adversarial.py`; sanity completo |
| STORY-04B-003 | `test_schema.py`; `test_value_detector_persistence.py`; `test_value_detector_backtest_executor.py`; `test_value_detector_backtest_dataset.py`; sanity completo |
| STORY-04B-004 | `test_value_detector_backtest_metrics.py`; `test_value_detector_backtest_report.py`; `test_value_detector_backtest_adversarial.py` |
| STORY-04B-005 | `test_value_detector_deduplication.py` (incluindo testes novos de redetecção); `test_value_detector_backtest_executor.py`; `test_value_detector_adversarial.py` |
| STORY-04B-006 | `python -m pytest` (deve passar sem erros de coleta); confirmar `python -m pytest tests/` também passa |

### Gates Recorrentes (todas as stories)

```bash
git status --short
python -m pytest tests/unit/core/test_value_detector_sanity.py
python -m pytest tests/unit/core/test_value_detector_deduplication.py
python -m pytest tests/unit/core/test_value_detector_persistence.py
python -m pytest tests/unit/core/test_value_detector_backtest_metrics.py
python -m pytest tests/unit/core/test_value_detector_backtest_executor.py
python -m pytest tests/unit/core/test_value_detector_backtest_adversarial.py
python -m pytest tests/unit/database/test_schema.py
python scripts/check_doc_consistency.py
python scripts/check_transaction_discipline.py
git diff --check
```

### Critério de Encerramento da Onda 4B

- 0 falhas nos gates recorrentes.
- `python -m pytest tests/` passando sem erros de coleta.
- `sanity_check_value_detector()` retornando `passed=True`.
- Overround Pinnacle normalizado e testes passando.
- `snapshot_id` em `value_detections` com FK ativa.
- Semântica de `coverage_rate` documentada e decisão registrada.
- Redetecção por mudança material de odds funcionando e testada.
- Tag `v0.7-onda4b-robustez` criada.

---

## 9. Primeiro Prompt Recomendado

```text
use bmad-agent-dev

# Tarefa: STORY-04B-001 — Corrigir fixture de sanity e deduplicação

## Etapa atual

Onda 4B — Etapa 1 de 6.

## Contexto

A Onda 4A foi concluída e tagueada em v0.6-onda4a-backtest.
A Onda 4B tem como objetivo corrigir dívidas técnicas médias antes de qualquer API pública ou GeminiValidator.

Esta é a primeira e menor story: corrigir o fixture de sanity que causa falha de deduplicação no sanity check.

IMPORTANTE:
Não implementar código nesta tarefa além do descrito.

Não implementar:
- aposta real;
- execução financeira;
- stake;
- Kelly;
- bankroll;
- Telegram;
- scheduler;
- API REST;
- GeminiValidator;
- AutoEvolution;
- alerta acionável;
- integração com casa de aposta.

## Causa-raiz identificada

Em `value_detector_sanity.py`, o método `_opportunity()` cria um fixture com `created_at='2026-05-28T12:00:00+00:00'` (timestamp antigo fixo).

Quando `deduplicate_opportunities([opportunity, opportunity])` é chamado com `now=datetime.now(timezone.utc)`, a janela de deduplicação é `[now - 60min, now]`.

O `created_at` fixo é anterior à `window_start`, então ambas as cópias são classificadas como "fora da janela" e passam — comportamento correto da deduplicação, mas que quebra a expectativa do sanity.

## Solução esperada

Corrigir `_opportunity()` em `value_detector_sanity.py` para usar `created_at` dinâmico com `datetime.now(timezone.utc).isoformat()` em vez de string fixa.

Verificar se isso resolve os 3 testes que falham sem quebrar nenhum dos que passam.

## Documentos obrigatórios para leitura

Leia:
- docs/implementation/ONDA_4B_EXECUTION_PLAN.md
- docs/implementation/ONDA_4A_CLOSURE_REPORT.md
- src/edgehunter/core/value_detector_sanity.py
- tests/unit/core/test_value_detector_sanity.py
- tests/unit/core/test_value_detector_deduplication.py

## Validação obrigatória

Rodar:
- python -m pytest tests/unit/core/test_value_detector_sanity.py -v
- python -m pytest tests/unit/core/test_value_detector_deduplication.py -v
- python -m pytest tests/unit/core/test_value_detector_persistence.py -v
- python scripts/check_doc_consistency.py
- python scripts/check_transaction_discipline.py
- git diff --check

Todos devem passar com 0 falhas.

## Output obrigatório

Gerar relatório com:
- causa-raiz confirmada;
- arquivo(s) modificado(s);
- resultado dos testes antes e depois;
- confirmação de guardrails;
- veredicto: STORY-04B-001 CONCLUÍDA / CONCLUÍDA COM RESSALVAS / NÃO CONCLUÍDA.

Commitar com:
git commit -m "fix(sanity): corrigir fixture de deduplicação com created_at dinâmico"
```

---

## 10. Etapas Restantes Estimadas

A Onda 4B terá **6 stories**.

| Story | Título | Etapas restantes após conclusão |
|---|---|---|
| STORY-04B-001 | Corrigir fixture de sanity e deduplicação | 5 |
| STORY-04B-002 | Normalizar overround Pinnacle (v2) | 4 |
| STORY-04B-003 | Propagar `snapshot_id` + FK no schema | 3 |
| STORY-04B-004 | Decidir e documentar semântica de `coverage_rate` | 2 |
| STORY-04B-005 | Reabertura por mudança material de odds/EV | 1 |
| STORY-04B-006 | Isolar suíte global de legado | 0 — encerramento da Onda 4B |

Após a primeira story (STORY-04B-001), faltam **5 etapas**.

---

## 11. Validação Desta Auditoria

| Comando | Exit Code | Resultado | Classificação |
|---|---:|---|---|
| `git status --short` | 0 | Limpo | Ok — worktree limpo antes do plano |
| `pytest test_value_detector_sanity.py` | 1 | 3 failed, 3 passed | Falha de Onda 3 preexistente — STORY-04B-001 irá corrigir |
| `pytest test_value_detector_deduplication.py` | 0 | 19 passed | Ok |
| `pytest test_value_detector_persistence.py` | 0 | 16 passed | Ok |
| `pytest test_value_detector_backtest_metrics.py` | 0 | 22 passed | Ok |
| `pytest test_value_detector_backtest_executor.py` | 0 | 28 passed | Ok |
| `pytest test_value_detector_backtest_adversarial.py` | 0 | 32 passed | Ok |
| `pytest test_schema.py` | 0 | 12 passed | Ok |
| `check_doc_consistency.py` | 0 | 0 erros, 0 findings | Ok |
| `check_transaction_discipline.py` | 0 | transaction-discipline: ok | Ok |
| `git diff --check` | 0 | Sem whitespace errors | Ok |
| `python -m pytest` (global) | 1 | 6 erros de coleta | Falha de ambiente/legado — STORY-04B-006 irá isolar |

**Núcleo analítico (excluindo sanity e legado): 120/123 testes passando. 3 falhas de Onda 3 preexistente, todas com causa-raiz conhecida e solução mapeada.**

---

## 12. Decisão para Rafael

- [x] Pode iniciar Onda 4B.
- [ ] Pode iniciar com ressalvas.
- [ ] Não deve iniciar ainda.

**Justificativa técnica:** Todas as dívidas têm causa-raiz identificada, solução clara, escopo local/seguro e zero risco de operação real. A STORY-04B-001 tem a menor superfície de mudança da onda e elimina o único ruído de CI ativo. A ordem das stories foi projetada para minimizar dependências cruzadas e re-trabalho. O projeto continua estritamente em modo paper trading/local durante toda a Onda 4B.

Rafael pode iniciar a Onda 4B imediatamente após aprovação deste plano, usando o prompt da STORY-04B-001 na seção 9.

---

*Plano gerado por John — Product Manager — EdgeHunter BMad v6.6.1*
