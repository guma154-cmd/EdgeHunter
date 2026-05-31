# Auditoria da Proxima Onda - EdgeHunter

## 1. Veredicto

- [x] INICIAR ONDA DE BACKTEST/PAPER TRADING
- [ ] INICIAR ONDA DE EXPOSICAO/API
- [ ] INICIAR PRD-04 / GEMINIVALIDATOR
- [ ] CORRIGIR DIVIDAS ANTES DE AVANCAR
- [ ] NAO APROVADO

A proxima onda mais segura e uma onda tecnica de Backtest/Paper Trading. A Onda 3 criou o nucleo local do ValueDetector, mas ainda nao mediu falso positivo, nao validou performance historica, nao fechou contrato com `snapshot_id`, nao tem FK para `odds_snapshots` em `value_detections` e adiou a API REST por risco de exposicao operacional.

API, GeminiValidator e AutoEvolution devem ficar depois. Eles aumentam superficie publica, uso de API externa, alertas, ou risco de parecer recomendacao de aposta antes de o detector ter metricas historicas confiaveis.

## 2. Opcoes Avaliadas

| Opcao | Beneficio | Risco | Veredicto |
|---|---|---|---|
| Onda de Backtest/Paper Trading | Mede falso positivo, ROI simulado, estabilidade do consenso e qualidade do sinal antes de exposicao | Baixo, se mantida local e sem stake/Kelly/bankroll | Recomendada agora |
| Onda de Exposicao/API | Permite consulta por frontend e contratos externos | Alto: exige auth/authz, OpenAPI, paginacao, performance e linguagem nao acionavel | Adiar |
| PRD-04 / GeminiValidator | Adiciona revisao contextual por IA | Alto: depende de API externa, prompt, custo, parse, fallback e risco de alerta | Adiar ate backtest provar qualidade minima |
| PRD-05 / AutoEvolution | Fecha ciclo de otimizacao e operacao futura | Critico: PRD inclui stake, Kelly, bankroll, alertas e automacao | Somente analise futura, nao iniciar |
| Corrigir todas as dividas antes de avancar | Reduz ruido tecnico global | Medio: pode travar produto por dividas nao bloqueantes | Corrigir apenas dividas que afetem backtest |

## 3. Proxima Onda Recomendada

Nome da onda: Onda 4A - Backtest e Paper Trading do ValueDetector.

Objetivo: medir historicamente a qualidade do ValueDetector em modo local, simulado e nao acionavel, produzindo metricas de falso positivo, cobertura, EV simulado, resultados por fonte e relatorios tecnicos para decidir se o detector esta maduro para API segura ou GeminiValidator.

Por que vem agora:

- O PRD-03 define precisao como falso positivo abaixo de 20% e criterio de aceite com falso positivo abaixo de 25% em backtest.
- A Onda 3 entregou deteccao, deduplicacao, persistencia e sanity local, mas nao entregou medicao historica de qualidade.
- Expor API antes de medir falso positivo aumenta risco de leitura operacional.
- Chamar Gemini antes de medir a base estatistica pode mascarar defeitos do detector com uma camada cara e externa.
- AutoEvolution/PRD-05 depende de sinais confiaveis; sem backtest, qualquer ajuste dinamico seria prematuro.

Por que as outras opcoes ficam depois:

- API fica depois porque exige contrato publico seguro, auth/authz, filtros, paginacao, performance p95, OpenAPI e linguagem explicitamente simulada.
- GeminiValidator fica depois porque envolve API externa, prompts, parse robusto, budget e potencial alerta; deve consumir apenas sinais ja medidos.
- AutoEvolution fica depois porque toca stake/Kelly/bankroll/alertas e e operacionalmente sensivel.
- Dividas globais de ambiente ficam registradas, mas nao bloqueiam uma onda local de backtest se os gates focados seguirem verdes.

## 4. Dependencias Satisfeitas

| Dependencia | Status | Evidencia |
|---|---|---|
| Onda 1 concluida | Satisfeita | `docs/implementation/ONDA_1_CLOSURE_REPORT.md`; fundacao de dados aprovada com ressalvas. |
| Onda 2 concluida | Satisfeita | `docs/implementation/ONDA_2_CLOSURE_REPORT.md`; PoissonModel local aprovado com ressalvas. |
| Onda 3 concluida e tagueada | Satisfeita | `docs/implementation/ONDA_3_CLOSURE_REPORT.md`; tag `v0.5-onda3-valuedetector`. |
| OddsHistorian armazena snapshots validos | Satisfeita | `OddsHistorian.store_snapshot()` e `get_recent_valid_snapshots()`. |
| Resultados de partidas existem para treino/avaliacao | Satisfeita | `OddsHistorian.update_match_result()` e `get_finished_matches_with_last_odds()`. |
| PoissonModel prediz probabilidades 1X2 | Satisfeita | `PoissonModel.predict_probabilities()` e sanity do modelo. |
| ValueDetector gera oportunidades simuladas | Satisfeita | `detect_value_vs_pinnacle()`, `detect_value_vs_poisson()` e `detect_value_consensus()`. |
| Persistencia paper trading existe | Satisfeita com ressalva | `value_detections` e `persist_simulated_opportunities()`; falta `snapshot_id` e FK. |
| Guardrails de seguranca | Satisfeita | Tests focados validam ausencia de Telegram, scheduler, rede, stake, Kelly, bankroll e aposta real. |
| API REST | Nao requerida | STORY-03-008 adiada conscientemente no encerramento da Onda 3. |

## 5. Gaps e Dividas

### Criticas

Nenhuma divida critica bloqueia iniciar uma onda local de Backtest/Paper Trading.

Bloqueiam, porem, qualquer avancar para API publica, GeminiValidator operacional, AutoEvolution, alerta acionavel, stake, Kelly, bankroll, scheduler ou aposta real:

- Falso positivo do ValueDetector ainda nao medido em backtest.
- API REST ainda sem auth/authz e contrato publico seguro.
- PRD-04 e PRD-05 ainda contem comportamentos que podem gerar alerta ou ajuste operacional se implementados sem recorte tecnico.

### Medias

- Backtest para medir falso positivo, cobertura e metricas por fonte.
- Contrato de oportunidade com `snapshot_id`.
- FK de `value_detections.snapshot_id` para `odds_snapshots.id`.
- Remocao/normalizacao de overround Pinnacle.
- Reabertura de oportunidade por mudanca material de odds/EV.
- Relatorio local de paper trading antes de API.
- API REST em onda futura.
- Auth/authz da API.
- OpenAPI/Swagger.
- Paginacao, filtros e performance p95 da API.
- Suite global/ambiente legado: `flask`, `playwright` e `remote_test.py` com `/app`.

### Baixas

- Melhorar exemplos de payloads simulados.
- Criar glossario de nomes publicos nao acionaveis.
- Expandir metricas do sanity check do ValueDetector.
- Adicionar fixtures historicas sinteticas mais ricas para smoke tests.
- Documentar criterios de aceitacao para API somente leitura.

## 6. Stories Propostas para a Proxima Onda

| Ordem | Story | Objetivo | Observacao |
|---:|---|---|---|
| 1 | STORY-04A-001 - Contrato de Backtest/Paper Trading | Definir dataclasses/resultado estruturado de backtest local, sem persistencia operacional | Primeira story de menor risco; pura e testavel. |
| 2 | STORY-04A-002 - Dataset historico local para backtest | Consultar partidas finalizadas com snapshots validos e resultados reais | Reusar OddsHistorian; sem rede. |
| 3 | STORY-04A-003 - Executor puro de backtest do ValueDetector | Rodar Pinnacle, Poisson e consenso sobre historico | Sem stake/Kelly/bankroll. |
| 4 | STORY-04A-004 - Metricas de qualidade | Calcular falso positivo, cobertura, hit rate, EV simulado e resultados por fonte | Metricas tecnicas, nao recomendacao. |
| 5 | STORY-04A-005 - Relatorio local de paper trading | Gerar resumo estruturado em dict/Markdown local | Sem API e sem Telegram. |
| 6 | STORY-04A-006 - Backtest adversarial | Testar overround anomalo, odds extremas, dados incompletos e modelos instaveis | Mantem guardrails. |
| 7 | STORY-04A-007 - Auditoria de prontidao para API/Gemini | Decidir se o detector passa para onda de exposicao ou PRD-04 | Gate final da onda. |

## 7. Guardrails Obrigatorios

- Nao implementar aposta real.
- Nao implementar execucao financeira.
- Nao implementar stake.
- Nao implementar Kelly.
- Nao implementar bankroll.
- Nao implementar Telegram operacional.
- Nao implementar scheduler operacional.
- Nao implementar automacao de entrada.
- Nao integrar com casa de aposta para execucao.
- Nao emitir alerta acionavel.
- Nao criar mensagem, endpoint ou relatorio que pareca mandar apostar.
- Manter `is_simulated=True`.
- Manter `paper_trading=True`.
- Manter `actionable=False`.
- Manter `bet_placed=False`.
- Manter `alerted=False`.
- Usar apenas dados locais ja persistidos ou fixtures de teste.
- Se houver API futura, deve ser somente leitura, autenticada, paginada, documentada e explicitamente nao acionavel.

## 8. Estrategia de Testes

Testes minimos da proxima onda:

- Testes unitarios para contrato de resultado de backtest.
- Testes de consulta local usando banco SQLite temporario.
- Testes de executor de backtest com fixtures deterministicas.
- Testes de metricas: falso positivo, cobertura, hit rate, EV medio, agrupamento por fonte e por liga.
- Testes de dados insuficientes: sem resultado, sem odds, sem Pinnacle, snapshot invalido, Poisson untrained, sanity falho.
- Testes adversariais: NaN/inf, odds extremas, overround anomalo, datas naive, janelas vazias.
- Guardrails por inspecao: sem Telegram, scheduler, rede, API, stake, Kelly, bankroll, aposta real ou execucao financeira.
- Gates recorrentes: `check_doc_consistency.py`, `check_transaction_discipline.py`, suites focadas de ValueDetector, PoissonModel/OddsHistorian quando tocados.

Resultado da validacao desta auditoria:

| Comando | Exit Code | Classificacao |
|---|---:|---|
| `git status --short` | 0 | Limpo antes da criacao deste relatorio |
| `python scripts/check_doc_consistency.py` | 0 | Documental ok |
| `python scripts/check_transaction_discipline.py` | 0 | Transacional ok |
| `python -m pytest tests/unit/core/test_value_detector_ev.py` | 0 | Onda 3 ok |
| `python -m pytest tests/unit/core/test_value_detector_opportunity.py` | 0 | Onda 3 ok |
| `python -m pytest tests/unit/core/test_value_detector_pinnacle.py` | 0 | Onda 3 ok |
| `python -m pytest tests/unit/core/test_value_detector_poisson.py` | 0 | Onda 3 ok |
| `python -m pytest tests/unit/core/test_value_detector_consensus.py` | 0 | Onda 3 ok |
| `python -m pytest tests/unit/core/test_value_detector_deduplication.py` | 0 | Onda 3 ok |
| `python -m pytest tests/unit/core/test_value_detector_persistence.py` | 0 | Onda 3 ok |
| `python -m pytest tests/unit/core/test_value_detector_adversarial.py` | 0 | Onda 3 ok |
| `python -m pytest tests/unit/core/test_value_detector_sanity.py` | 0 | Onda 3 ok |
| `python -m pytest tests/unit/database/test_schema.py` | 0 | Schema ok |
| `git diff --check` | 0 | Sem whitespace errors antes deste relatorio |
| `python -m pytest` | 1 | Falha de ambiente/legado: falta `flask`, falta `playwright`, e `remote_test.py` assume `/app` no Windows |

## 9. Primeiro Prompt Recomendado

```text
use bmad-agent-dev

# Tarefa: Implementar STORY-04A-001 - Contrato de Backtest/Paper Trading do ValueDetector

## Contexto

A Onda 3 foi concluida e tagueada em v0.5-onda3-valuedetector.
O proximo caminho aprovado e a Onda 4A - Backtest e Paper Trading.

O projeto continua em modo tecnico/simulado/paper trading.

Nao implementar:
- aposta real;
- execucao financeira;
- stake;
- Kelly;
- bankroll;
- Telegram;
- scheduler;
- API REST;
- GeminiValidator;
- AutoEvolution;
- alerta acionavel;
- integracao com casa de aposta.

## Objetivo

Criar um contrato puro e local para resultados de backtest/paper trading do ValueDetector.
A entrega deve permitir representar metricas de uma execucao historica simulada sem executar o backtest completo ainda.

## Documentos obrigatorios

Leia:
- docs/implementation/NEXT_WAVE_AUDIT.md
- docs/implementation/ONDA_3_CLOSURE_REPORT.md
- docs/prd/03_value_detector.md
- docs/prd/02_poisson_model.md
- docs/prd/01_odds_historian.md

## Codigo obrigatorio para inspecao

Revisar:
- src/edgehunter/core/value_detector.py
- src/edgehunter/core/value_detector_persistence.py
- src/edgehunter/core/value_detector_sanity.py
- src/edgehunter/core/odds_historian.py
- src/edgehunter/core/poisson_model.py
- src/edgehunter/database/schema.py

## Escopo esperado

Criar modulo puro, por exemplo:
- src/edgehunter/core/value_detector_backtest.py

Criar testes:
- tests/unit/core/test_value_detector_backtest_contract.py

Implementar dataclass/estrutura equivalente a:
- BacktestSelectionResult
- BacktestRunResult
- BacktestMetrics

Requisitos:
- resultado estruturado;
- modo simulado/paper trading explicito;
- metricas sem stake/Kelly/bankroll;
- campos para total analisado, oportunidades, acertos/erros, falso positivo, cobertura, EV simulado;
- `to_dict()` deterministico;
- validacao de NaN/inf;
- timestamps timezone-aware;
- sem SQLite nesta story;
- sem rede;
- sem Telegram;
- sem scheduler;
- sem API.

## Validacao obrigatoria

Rodar:
- python -m pytest tests/unit/core/test_value_detector_backtest_contract.py
- python -m pytest tests/unit/core/test_value_detector_ev.py
- python -m pytest tests/unit/core/test_value_detector_opportunity.py
- python scripts/check_doc_consistency.py
- python scripts/check_transaction_discipline.py
- git diff --check

## Output obrigatorio

Gerar relatorio final com:
- story implementada;
- arquivos criados/modificados;
- assinatura das estruturas;
- metricas suportadas;
- confirmacao de guardrails;
- resultado dos testes;
- veredicto: STORY-04A-001 CONCLUIDA / CONCLUIDA COM RESSALVAS / NAO CONCLUIDA.
```

## 10. Decisao para Rafael

- [ ] Pode iniciar proxima onda.
- [x] Pode iniciar com ressalvas.
- [ ] Nao deve iniciar ainda.

Justificativa tecnica: os gates focados atuais passam e a Onda 3 deixou um nucleo local suficiente para backtest. As ressalvas nao bloqueiam uma onda local de metricas, mas bloqueiam API publica, GeminiValidator operacional, AutoEvolution, alertas, scheduler, stake, Kelly, bankroll, aposta real e execucao financeira.

## 11. Etapas restantes estimadas

A proxima onda deve ter 7 stories.

Etapas/stories estimadas:

1. Contrato de Backtest/Paper Trading.
2. Dataset historico local para backtest.
3. Executor puro de backtest do ValueDetector.
4. Metricas de qualidade e falso positivo.
5. Relatorio local de paper trading.
6. Backtest adversarial.
7. Auditoria de prontidao para API/Gemini.

Apos a primeira story, faltam 6 etapas.
