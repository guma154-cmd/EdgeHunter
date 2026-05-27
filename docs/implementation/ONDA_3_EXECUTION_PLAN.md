# Plano de Execução da Onda 3 — Após PoissonModel

## 1. Veredicto

**APROVADO COM RESSALVAS**

A próxima onda correta é a **Onda 3 — Detecção de Valor**, baseada no **PRD-03: Value Detector**. A documentação de ondas define explicitamente que a Onda 3 cobre `STORY-03-001` a `STORY-03-010`, e o PRD-03 está aceito como próximo módulo analítico depois de OddsHistorian e PoissonModel.

As ressalvas são materiais: a Onda 3 pode começar pela camada pura e simulada de cálculo/representação de oportunidades, mas não deve começar por alerta, scheduler, API operacional ou persistência de detecções acionáveis. O sistema permanece em modo técnico, simulado e paper trading. Nada nesta onda autoriza aposta real, execução financeira, integração com casa de aposta para execução ou qualquer função que pareça mandar apostar.

## 2. Próximo PRD/Onda

O próximo PRD é o **PRD-03: Value Detector**.

Motivos:

- `docs/implementation/IMPLEMENTATION_WAVES.md` define a Onda 3 como "Detecção de Valor" e lista `STORY-03-001` a `STORY-03-010`.
- `docs/prd/03_value_detector.md` está com status `Accepted`.
- `docs/prd/02_poisson_model.md` declara que o PRD-03 consumirá as probabilidades geradas pelo PoissonModel.
- `docs/prd/01_odds_historian.md` declara que o PRD-03 consome snapshots válidos do OddsHistorian.
- `docs/implementation/ONDA_2_CLOSURE_REPORT.md` autoriza apenas avanço técnico controlado após a Onda 2, não operação real.

## 3. Stories propostas

| Story | Objetivo | Ordem recomendada | Observação |
|---|---|---:|---|
| `STORY-03-001` | Implementar cálculo de EV como função pura | 1 | Primeira story segura. Sem banco, rede, Telegram, scheduler ou aposta. |
| `STORY-03-SUP-001` | Definir modelos/contratos de oportunidade simulada | 2 | Micro-story recomendada antes de detecção integrada para evitar objeto informal ou acionável. |
| `STORY-03-SUP-002` | Expor query local de snapshots recentes válidos no OddsHistorian | 3 | Necessária porque o código atual expõe snapshots por partida finalizada, mas não `get_recent_snapshots(minutes=30, league=None)`. |
| `STORY-03-002` | Query de snapshots recentes válidos | 4 | Deve permanecer local e filtrada por `valid_for_analysis=True`. |
| `STORY-03-003` | Detectar valor vs benchmark Pinnacle | 5 | Depende de snapshots recentes com Pinnacle e odds-alvo. Resultado deve ser oportunidade simulada, não alerta. |
| `STORY-03-004` | Detectar valor vs Modelo Poisson | 6 | Depende de `PoissonModel.predict_probabilities()` e deve respeitar `trained=False` e fallback/baixa confiança. |
| `STORY-03-005` | Modo consenso | 7 | Recomendado como default conservador para reduzir falso positivo. |
| `STORY-03-006` | Deduplicação de detecções | 8 | Deve usar hash determinístico e janela de 1h. |
| `STORY-03-007` | Persistência local de oportunidades simuladas | 9 | Permitida apenas como log técnico/paper trading com `alerted=False` e `bet_placed=False`. |
| `STORY-03-010` | Testes adversariais do ValueDetector | 10 | Pode ser antecipada parcialmente junto das stories 03-001/03-003/03-004. |
| `STORY-03-009` | Sanity check do detector | 11 | Telegram e scheduler reais devem ser substituídos por retorno estruturado/desabilitação em memória nesta onda. |
| `STORY-03-008` | API REST para frontend consultar detecções | 12 | Deixar por último; depende de schema, filtros, performance e decisão de exposição. |

## 4. Dependências satisfeitas

| Dependência | Status | Evidência |
|---|---|---|
| Onda 1 concluída e tagueada | Satisfeita | `docs/implementation/ONDA_1_CLOSURE_REPORT.md` e tag `v0.2-onda1-fundacao-dados`. |
| Onda 2 concluída e tagueada | Satisfeita | `docs/implementation/ONDA_2_CLOSURE_REPORT.md` e tag `v0.4-onda2-poissonmodel`. |
| OddsHistorian registra partidas e snapshots | Satisfeita | `src/edgehunter/core/odds_historian.py`, `store_snapshot()`, `register_match()`. |
| OddsHistorian valida odds e timestamps | Satisfeita | `tests/unit/core/test_odds_historian_store_snapshot.py`; Onda 1 aprovou validação. |
| OddsHistorian possui `valid_for_analysis` | Satisfeita | `store_snapshot()` e testes de Onda 1/Onda 2. |
| OddsHistorian expõe resultados finalizados | Satisfeita | `update_match_result()` e `get_finished_matches_with_last_odds(valid_only=True)`. |
| PoissonModel gera probabilidades 1X2 | Satisfeita | `predict_probabilities()` e testes unitários. |
| PoissonModel pode ser treinado e persistido | Satisfeita | `fit()`, `save()`, `load()`, sanity e deployment decision. |
| PoissonModel não acopla rede, SQLite, Telegram ou scrapers | Satisfeita | Guardrails em testes da Onda 2. |
| Decisão pré-deployment do PoissonModel | Satisfeita | `DeploymentDecision` e `evaluate_deployment_candidate()`. |

## 5. Gaps encontrados

### Críticos

Nenhum gap crítico bloqueia iniciar a Onda 3 pela `STORY-03-001` como função pura.

Bloqueia, porém, começar por detecção integrada, alerta ou persistência operacional:

- Não existe ainda `ValueDetector`.
- Não existe query `get_recent_snapshots(minutes=30, league=None)` no `OddsHistorian`.
- Não existe schema/tabela `value_detections` implementado e validado.
- Não existe backtest do ValueDetector nem taxa de falso positivo medida.
- Não existe camada de oportunidade simulada com semântica explicitamente não operacional.

### Médios

- O `PoissonModel` retorna probabilidades suficientes para cálculo 1X2, mas o PRD-03 ainda fala em tratar `None`; a implementação atual usa fallback neutro e `used_fallback` em `predict_match()`, enquanto `predict_probabilities()` retorna probabilidades. A Onda 3 precisa decidir se fallback deve ser aceito, rebaixado ou tratado como skip.
- O OddsHistorian armazena Pinnacle, Bet365 e Betano, mas falta método dedicado para buscar snapshots recentes válidos para análise de valor.
- O PRD-03 menciona remoção de overround em story-detail, enquanto a story de PRD simplifica Pinnacle como `1 / pinnacle_odds`. A Onda 3 deve documentar uma decisão v1 consistente.
- A persistência em `value_detections` precisa ser desenhada como paper trading/simulação, com flags que impeçam interpretação operacional.
- A deduplicação deve existir antes de qualquer exposição de relatório ou API para evitar falso positivo repetido.

### Baixos

- API REST pode aguardar até o final da onda.
- Performance p95 pode começar com benchmark local sintético antes de carga real.
- Métricas de qualidade podem iniciar com contadores e logs estruturados antes de dashboards.
- Canários e sanity do detector podem começar em memória antes de scheduler.

## 6. Guardrails obrigatórios

O plano da Onda 3 deve proibir explicitamente:

- aposta real;
- execução financeira;
- integração com casa de aposta para execução;
- envio Telegram operacional de alerta acionável;
- automação de entrada;
- uso de dados reais para decisão financeira sem validação;
- qualquer função, nome ou fluxo que pareça "mandar apostar";
- cálculo de stake, Kelly, sizing ou bankroll;
- alteração de estado operacional externo;
- scheduler real de detecção ou promoção;
- API pública que pareça recomendação de aposta.

O escopo permitido é:

- cálculo estatístico de EV;
- simulação;
- paper trading;
- backtest;
- avaliação de qualidade;
- geração de relatório técnico;
- persistência local de oportunidades simuladas, quando prevista e protegida por flags;
- retorno estruturado com `is_simulated=True`, `paper_trading=True` ou equivalente;
- logs/auditoria local sem ação operacional.

## 7. Estratégia de testes

Testes mínimos para a próxima onda:

- `calculate_ev(0.6, 2.0) == 0.2`.
- Rejeição de probabilidade fora de `[0, 1]`.
- Rejeição de odds `< 1.01`, `0`, negativa, `NaN` e `inf`.
- EV abaixo do threshold não gera oportunidade simulada.
- Snapshot sem Pinnacle não gera oportunidade em modo Pinnacle.
- Snapshot com `valid_for_analysis=False` não entra na análise.
- PoissonModel `trained=False` não gera detecção baseada no modelo.
- Modelo com fallback/baixa confiança deve ser tratado explicitamente: skip ou marcação de risco, mas nunca alerta acionável.
- Consensus mode só detecta se Pinnacle e modelo passarem o threshold.
- Deduplicação bloqueia mesma oportunidade em janela de 1h.
- Deduplicação permite nova oportunidade se odds mudarem acima do threshold definido.
- Overround anômalo não deve virar falso positivo silencioso.
- Persistência local deve manter `alerted=False`, `bet_placed=False`, `is_simulated=True` ou equivalente.
- Testes de guardrail devem provar ausência de Telegram operacional, rede de execução, stake, bankroll, AutoEvolution, GeminiValidator e envio para casa de aposta.

Gates mínimos por story:

- `python scripts/check_doc_consistency.py`
- `python scripts/check_transaction_discipline.py`
- testes unitários novos do ValueDetector;
- suíte focada da Onda 2 quando a story tocar PoissonModel ou OddsHistorian;
- `git diff --check`.

## 8. Primeiro prompt recomendado

```text
use bmad-agent-dev

# Tarefa: Implementar STORY-03-001 — cálculo de EV puro do ValueDetector

Contexto:
A Onda 2 foi encerrada em v0.4-onda2-poissonmodel. A Onda 3 começa pelo PRD-03 / ValueDetector, mas o projeto permanece em modo técnico/simulado/paper trading.

Objetivo:
Criar a menor base segura do ValueDetector: uma função pura `calculate_ev(true_prob, offered_odds)` e testes unitários/adversariais.

Escopo permitido:
- cálculo estatístico puro;
- sem banco;
- sem rede;
- sem Telegram;
- sem scheduler;
- sem ValueDetector integrado ainda;
- sem persistência;
- sem alerta;
- sem aposta real;
- sem stake/Kelly/bankroll;
- sem execução financeira.

Requisitos:
- `EV = (true_prob * offered_odds) - 1`;
- validar `true_prob` em `[0, 1]`;
- validar `offered_odds >= 1.01`;
- rejeitar `NaN` e `inf`;
- retornar float finito;
- testes para casos positivos, zero/negativo, threshold futuro, odds inválidas e probabilidades inválidas;
- testes de guardrail confirmando ausência de Telegram/rede/scheduler/aposta/stake.

Validação:
- rodar testes novos;
- rodar `python scripts/check_doc_consistency.py`;
- rodar `python scripts/check_transaction_discipline.py`;
- rodar `git diff --check`.

Não implementar detecção integrada, persistência, API, scheduler, Telegram, GeminiValidator, AutoEvolution ou qualquer fluxo operacional.
```

## 9. Decisão para Rafael

**Pode iniciar com ressalvas.**

Justificativa técnica: a documentação confirma PRD-03 / ValueDetector como próxima onda, e as dependências analíticas principais da Onda 1 e Onda 2 estão satisfeitas para começar pela função pura de EV. As ressalvas impedem pular direto para detecção integrada ou exposição operacional: antes disso, é preciso criar contrato de oportunidade simulada, query recente válida, deduplicação, persistência paper trading e testes adversariais contra falso positivo.
