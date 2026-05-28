# Relatorio de Encerramento - Onda 3 EdgeHunter

## 1. Veredicto Executivo

- [ ] APROVADA PARA CHECKPOINT
- [x] APROVADA COM RESSALVAS
- [ ] NAO APROVADA

A Onda 3 esta tecnicamente concluida como pipeline local, simulado e de paper trading do ValueDetector. Os gates focados passaram, os guardrails de seguranca foram preservados e a STORY-03-008 API REST foi explicitamente adiada para uma onda futura de exposicao/consulta.

A aprovacao nao autoriza producao, aposta real, execucao financeira, Telegram operacional, scheduler, API publica, stake, Kelly ou bankroll.

## 2. Status por Entrega

| Entrega | Status | Evidencia | Observacao |
|---|---|---|---|
| Calculo puro de EV | Concluido | `calculate_ev()` em `src/edgehunter/core/value_detector.py`; 27 testes em `test_value_detector_ev.py` | Funcao pura, sem banco, rede, Telegram ou scheduler. |
| Contrato de oportunidade simulada | Concluido | `SimulatedValueOpportunity` em `src/edgehunter/core/value_detector.py`; 41 testes em `test_value_detector_opportunity.py` | Contrato explicitamente simulado e nao acionavel. |
| Flags de seguranca | Concluido | `is_simulated=True`, `paper_trading=True`, `actionable=False`, `bet_placed=False`, `alerted=False` | Validados no dataclass, na persistencia e no sanity check. |
| Query local de snapshots recentes validos | Concluido | `OddsHistorian.get_recent_valid_snapshots()`; 13 testes em `test_odds_historian_recent_snapshots.py` | Filtra `valid_for_analysis=True`, janela temporal e liga opcional. |
| Deteccao simulada vs Pinnacle | Concluido com ressalva | `detect_value_vs_pinnacle()`; 18 testes em `test_value_detector_pinnacle.py` | Usa `1 / pinnacle_odds`; overround ainda nao normalizado. |
| Deteccao simulada vs PoissonModel | Concluido | `detect_value_vs_poisson()`; 20 testes em `test_value_detector_poisson.py` | Respeita modelo treinado, sanity e fallback. |
| Modo consenso | Concluido | `detect_value_consensus()`; 15 testes em `test_value_detector_consensus.py` | Retorna apenas quando Pinnacle e Poisson concordam. |
| Deduplicacao local | Concluido | `deduplicate_opportunities()`; 19 testes em `test_value_detector_deduplication.py` | Usa chave logica e janela temporal, sem persistencia. |
| Persistencia local paper trading | Concluido com ressalva | `persist_simulated_opportunities()` e tabela `value_detections`; 16 testes em `test_value_detector_persistence.py` | Persistencia apenas tecnica; sem FK para `odds_snapshots` ainda. |
| Testes adversariais | Concluido | 36 testes em `test_value_detector_adversarial.py` | Cobre NaN/inf, snapshots malformados, guardrails, persistencia e consenso. |
| Sanity check local | Concluido | `sanity_check_value_detector()`; 6 testes em `test_value_detector_sanity.py` | Local, estruturado e sem Telegram/scheduler/API. |
| API REST | Adiada | Auditoria da STORY-03-008 | Fora do encerramento da Onda 3 por risco de exposicao operacional. |
| Ausencia de Telegram | Aprovado | Guardrails nos testes de EV, oportunidade, Pinnacle, Poisson, consenso, deduplicacao, persistencia, adversarial e sanity | Sem Telegram operacional. |
| Ausencia de scheduler | Aprovado | Guardrails nos testes focados | Sem scheduler de deteccao. |
| Ausencia de stake/Kelly/bankroll | Aprovado | Guardrails e ausencia de campos no contrato | Sem sizing ou gestao financeira. |
| Ausencia de aposta real | Aprovado | Flags `actionable=False`, `bet_placed=False` e guardrails | Nenhum comando de aposta. |
| Ausencia de execucao financeira | Aprovado | Escopo simulado/paper trading | Nenhuma integracao financeira. |

## 3. Commits Auditados

| Commit | Finalidade | Status |
|---|---|---|
| `c3344fa` | Planejar execucao da Onda 3 | Aprovado |
| `0128e68` | Implementar calculo puro de EV | Aprovado |
| `21c3db8` | Definir contrato de oportunidade simulada | Aprovado |
| `c75eb9a` | Expor snapshots recentes validos no OddsHistorian | Aprovado |
| `0c74043` | Detectar valor simulado vs Pinnacle | Aprovado com ressalva de overround v1 |
| `5c78dc3` | Detectar valor simulado vs Poisson | Aprovado |
| `e69e4be` | Implementar modo consenso simulado | Aprovado |
| `e4ba75c` | Deduplicar oportunidades simuladas | Aprovado |
| `e4314c0` | Persistir oportunidades simuladas | Aprovado com ressalva de FK futura |
| `eff3824` | Adicionar testes adversariais | Aprovado |
| `b089fde` | Adicionar sanity check local | Aprovado |

## 4. Testes Executados

| Comando | Exit Code | Resultado | Observacao |
|---|---:|---|---|
| `git status --short` | 0 | Passou | Worktree limpo antes do relatorio. |
| `python -m pytest tests/unit/core/test_value_detector_ev.py` | 0 | 27 passed | EV puro validado. |
| `python -m pytest tests/unit/core/test_value_detector_opportunity.py` | 0 | 41 passed | Contrato simulado validado. |
| `python -m pytest tests/unit/core/test_value_detector_pinnacle.py` | 0 | 18 passed | Benchmark Pinnacle v1 validado. |
| `python -m pytest tests/unit/core/test_value_detector_poisson.py` | 0 | 20 passed | PoissonModel validado no detector. |
| `python -m pytest tests/unit/core/test_value_detector_consensus.py` | 0 | 15 passed | Consenso validado. |
| `python -m pytest tests/unit/core/test_value_detector_deduplication.py` | 0 | 19 passed | Deduplicacao validada. |
| `python -m pytest tests/unit/core/test_value_detector_persistence.py` | 0 | 16 passed | Persistencia paper trading validada. |
| `python -m pytest tests/unit/core/test_value_detector_adversarial.py` | 0 | 36 passed | Suite adversarial validada. |
| `python -m pytest tests/unit/core/test_value_detector_sanity.py` | 0 | 6 passed | Sanity check local validado. |
| `python -m pytest tests/unit/core/test_odds_historian_recent_snapshots.py` | 0 | 13 passed | Query recente valida validada. |
| `python -m pytest tests/unit/database/test_schema.py` | 0 | 12 passed | Schema e tabela `value_detections` validados. |
| `python scripts/check_doc_consistency.py` | 0 | Passou | 0 erros, 0 findings. |
| `python scripts/check_transaction_discipline.py` | 0 | Passou | `transaction-discipline: ok`. |
| `git diff --check` | 0 | Passou | Sem whitespace errors antes do relatorio. |
| `python -m pytest` | 1 | Falhou na coleta | Falha de legado/ambiente: falta `flask`, falta `playwright`, e `remote_test.py` assume `/app` no Windows. Nao foi classificada como falha do nucleo da Onda 3. |

## 5. Criterios Tecnicos

| Criterio | Status | Evidencia |
|---|---|---|
| Calculo de EV finito e validado | Aprovado | `calculate_ev()` rejeita NaN/inf e odds/probabilidades invalidas. |
| Oportunidade sempre simulada | Aprovado | `SimulatedValueOpportunity.__post_init__()` exige `is_simulated=True`. |
| Paper trading obrigatorio | Aprovado | `paper_trading=True` exigido no contrato e na persistencia. |
| Oportunidade nao acionavel | Aprovado | `actionable=False` exigido no contrato, deduplicacao e persistencia. |
| Nenhuma aposta marcada | Aprovado | `bet_placed=False` exigido. |
| Nenhum alerta emitido | Aprovado | `alerted=False` exigido; sem Telegram operacional. |
| Snapshots recentes validos | Aprovado | `get_recent_valid_snapshots(minutes, league, now)` filtra janela e `valid_for_analysis=True`. |
| Pinnacle como benchmark v1 | Aprovado com ressalva | Probabilidade verdadeira v1 = `1 / pinnacle_odds`; sem remocao de overround. |
| PoissonModel como fonte simulada | Aprovado | Detector retorna vazio para modelo nao treinado, sanity falho ou fallback. |
| Consenso conservador | Aprovado | O consenso exige mesma partida, mercado, selecao e bookmaker-alvo nas duas fontes. |
| Deduplicacao local | Aprovado | Chave logica por partida, mercado, selecao, source e detection method; janela temporal. |
| Persistencia idempotente | Aprovado | `INSERT OR IGNORE` por `opportunity_id`; retorna novas insercoes. |
| Disciplina transacional | Aprovado | `check_transaction_discipline.py` passou. |
| API REST ausente | Aprovado com ressalva | STORY-03-008 adiada conscientemente. |
| Suite global | Ressalva | Falha por dependencias/artefatos legados fora do escopo da Onda 3. |

## 6. Decisao sobre STORY-03-008 API REST

STORY-03-008 foi adiada.

Motivo: API REST exige contrato publico seguro, auth/authz, paginacao, filtros, performance, OpenAPI e decisao de exposicao. A API pode aumentar risco de interpretacao operacional porque exporia oportunidades simuladas fora do contexto estritamente tecnico/local.

A Onda 3 fecha como pipeline tecnico/local/paper trading. A API deve virar onda futura de exposicao/consulta, com contrato que retorne apenas dados simulados e preserve linguagem explicita como `simulated`, `paper_trading`, `not_actionable`, `actionable=False`, `bet_placed=False` e `alerted=False`.

## 7. Ressalvas Oficiais

- Sem API REST nesta Onda.
- Sem Telegram operacional.
- Sem scheduler.
- Sem execucao financeira.
- Sem stake/Kelly/bankroll.
- Sem aposta real.
- Persistencia e apenas paper trading.
- `value_detections` ainda nao tem FK para `odds_snapshots` porque `SimulatedValueOpportunity` ainda nao carrega `snapshot_id`.
- Overround Pinnacle ainda nao foi normalizado.
- Performance API/p95 nao se aplica porque API foi adiada.
- Suite global pode continuar falhando por legado/ambiente.

## 8. Dividas Tecnicas

### Criticas

Nenhuma divida critica bloqueia o checkpoint tecnico da Onda 3.

### Medias

- API REST em onda futura.
- Auth/authz da API.
- OpenAPI/Swagger.
- Paginacao, filtros e performance p95.
- `snapshot_id` no contrato de oportunidade.
- FK para `odds_snapshots`.
- Remocao de overround Pinnacle.
- Permitir reabertura por mudanca material de odds/EV.
- Backtest para medir falso positivo.
- Suite global/ambiente legado.

### Baixas

- Enriquecer metricas do sanity check local.
- Adicionar relatorios de consulta local para leitura humana antes da API.
- Documentar exemplos de payload paper trading para futura especificacao de API.
- Revisar nomes de campos publicos para reduzir ambiguidades operacionais.

## 9. Decisao Sobre Producao

Isto NAO autoriza operacao real.

Isto NAO autoriza aposta real.

Isto NAO autoriza execucao financeira.

Isto NAO autoriza alerta operacional.

Isto NAO autoriza Telegram.

Isto NAO autoriza scheduler.

Isto NAO autoriza API publica.

Isto autoriza apenas checkpoint tecnico local/paper trading.

## 10. Proximo Passo Recomendado

- [x] Criar tag/checkpoint da Onda 3.
- [ ] Corrigir pendencias antes do checkpoint.
- [ ] Preparar proxima onda antes do checkpoint.
- [ ] Auditar PRD seguinte antes do checkpoint.

Recomendacao: criar tag/checkpoint da Onda 3 com ressalvas registradas neste relatorio. Em seguida, planejar uma onda futura de exposicao/consulta para a API REST, separada do nucleo analitico local.

## 11. Decisao para Rafael

- [ ] Pode criar tag/checkpoint.
- [x] Pode criar com ressalvas.
- [ ] Nao deve criar ainda.

Justificativa tecnica: os gates focados da Onda 3 passaram e nao ha divida critica no nucleo entregue. As ressalvas sao relevantes, mas estao isoladas: API REST foi adiada por decisao de risco, overround/FK/snapshot_id sao melhorias futuras, e a falha da suite global foi classificada como legado/ambiente, nao como regressao do ValueDetector.
