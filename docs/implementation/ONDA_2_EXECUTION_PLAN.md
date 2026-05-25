# Plano de Execução da Onda 2 - PoissonModel

## 1. Veredicto

- [x] APROVADO PARA COMEÇAR STORY-02-001
- [ ] APROVADO COM RESSALVAS
- [ ] NÃO APROVADO

O repositório está limpo, a Onda 1 foi encerrada e tagueada em `v0.2-onda1-fundacao-dados`, e os gates documentais e de disciplina transacional continuam passando. O núcleo de dados entregue na Onda 1 já oferece `matches`, `odds_snapshots`, `valid_for_analysis`, `bookmakers_synced`, timestamps e `scraper_health`, o que é suficiente para iniciar o modelo matemático puro da `STORY-02-001`.

O ponto de atenção material não bloqueia o começo da Onda 2, mas bloqueia pular direto para o pipeline de treino real: o código atual ainda não implementa `update_match_result()` nem `get_finished_matches_with_last_odds(valid_only=True)`, apesar de o schema já conter `home_goals`, `away_goals`, `result` e `status`. Isso significa que a Onda 2 pode começar com o algoritmo base e testes sintéticos, mas a integração com dados históricos reais exigirá uma micro-story de suporte antes ou dentro de `STORY-02-002`.

## 2. Stories da Onda 2

| Story | Objetivo | Ordem recomendada | Observação |
|---|---|---:|---|
| `STORY-02-001` | Implementar o algoritmo Poisson MLE e o núcleo matemático reutilizável | 1 | Pode começar agora com dados sintéticos e sem tocar ValueDetector |
| `STORY-02-SUP` | Micro-story de suporte: expor `update_match_result()` e `get_finished_matches_with_last_odds(valid_only=True)` no OddsHistorian | 2 | Não está formalizada no PRD-02, mas é pré-requisito real para `02-002` |
| `STORY-02-002` | Treinar o modelo com dados históricos válidos do OddsHistorian | 3 | Depende do suporte acima e de partidas finalizadas com placar |
| `STORY-02-003` | Salvar e carregar pesos/metadados do modelo | 4 | Existe no PRD aceito, mas ainda não está promovida a story-detail |
| `STORY-02-004` | Implementar `predict_probabilities()` e contrato 1x2 | 5 | Existe no PRD aceito; há arquivo separado em `docs/stories/PoissonModel/`, mas não está no recorte de `stories_detalhadas.md` |
| `STORY-02-007` | Criar testes adversariais e de robustez numérica | 6 | Deve vir depois de treino e inferência mínimas existirem |
| `STORY-02-008` | Implementar sanity check pré-deployment do modelo treinado | 7 | Depende de treino, predição e persistência de pesos |

Observações formais:

- A lista esperada em `IMPLEMENTATION_WAVES.md` para a Onda 2 é `02-001`, `02-002`, `02-003`, `02-004`, `02-007`, `02-008`.
- `docs/stories/stories_detalhadas.md` detalha apenas `02-001`, `02-002`, `02-007` e `02-008`.
- `docs/stories/PoissonModel/` já contém `STORY-02-001.md`, `STORY-02-002.md`, `STORY-02-004.md` e `STORY-02-005.md`.
- `STORY-02-003` permanece apenas no PRD aceito e ainda precisa de promoção explícita para story-detail se for seguir o mesmo rigor documental da Onda 1.
- `STORY-02-005` e `STORY-02-006` existem no PRD-02, mas não fazem parte da Onda 2 declarada em `IMPLEMENTATION_WAVES.md`.

## 3. Dependências da Onda 1

| Dependência | Status | Impacto |
|---|---|---|
| Tabela `matches` | Parcialmente pronta | Existe e já suporta `home_goals`, `away_goals`, `result`, `status`, mas ainda não há API pública para alimentar resultados finais |
| Tabela `odds_snapshots` | Pronta | Oferece snapshots persistidos, timestamps por bookmaker, `max_latency_seconds`, `bookmakers_synced` e `valid_for_analysis` |
| Campo `valid_for_analysis` | Pronto | Permite excluir snapshots inválidos do pipeline de treino |
| Campo `bookmakers_synced` | Pronto | Útil como feature auxiliar ou filtro de qualidade, não como feature principal do modelo v1 |
| Timestamps UTC | Prontos | Fundamentais para consistência e rastreabilidade dos snapshots |
| Tabela `scraper_health` | Pronta | Não é insumo direto do Poisson, mas serve como guarda operacional para qualidade dos dados |
| Backup SQLite | Pronto com ressalva | Protege o histórico, mas não interfere no contrato matemático da Onda 2 |
| `register_match()` | Pronto | Garante identidade determinística para consolidar histórico por partida |
| `store_snapshot()` | Pronto | Persiste odds válidas/ inválidas com rastreabilidade |
| `update_match_result()` | Ausente no código | Gap real para treino com resultados finais |
| `get_finished_matches_with_last_odds(valid_only=True)` | Ausente no código | Gap real para `STORY-02-002` |

Conclusão de dependências:

- A Onda 1 entregou base suficiente para modelagem e testes sintéticos.
- A Onda 1 ainda não entregou a camada de consulta de dados finalizados exigida pelo PRD-02 para treino real.
- O schema atual suporta essa evolução sem refactor estrutural pesado; o gap é de API e fluxo, não de base SQLite.

## 4. Gaps encontrados

### Críticos

- Nenhum bloqueador crítico para iniciar `STORY-02-001`.

### Médios

- `PRD-02` exige treino com `historian.get_finished_matches_with_last_odds(valid_only=True)`, mas essa função ainda não existe no código atual de `src/edgehunter/core/odds_historian.py`.
- O schema tem `home_goals`, `away_goals`, `result` e `status`, mas não há `update_match_result()` implementado para popular partidas finalizadas. Sem isso, não há conjunto real de treino supervisionado.
- `STORY-02-003` não está promovida a story-detail no recorte documental principal. Se a equipe quiser manter o mesmo rito da Onda 1, isso deve ser corrigido antes da implementação dessa story.
- `python -m pytest` total falha fora do escopo da Onda 2 por dependências ausentes no legado (`flask`, `playwright`) e por `remote_test.py` assumir `/app`. Isso não invalida o plano da Onda 2, mas impede usar a suíte global como gate limpo sem isolar o legado.

### Baixos

- `stories_detalhadas.md` ainda não reflete `02-003` e `02-004` como parte detalhada da onda corrente, apesar de `IMPLEMENTATION_WAVES.md` listá-las.
- O PRD-02 cita serialização com JSON, `pickle` ou `joblib` em pontos diferentes; a Onda 2 deve fechar um default simples e auditável por story, sem abrir discussão arquitetural ampla.
- O backup da Onda 1 ainda não está plugado no scheduler legado, mas isso não afeta o início do PoissonModel.

## 5. Plano por Story

### STORY-02-001 - Algoritmo Poisson MLE

- Objetivo:
  Implementar a classe base `PoissonModel` com cálculo de log-verossimilhança negativa, otimização MLE, parâmetros de ataque/defesa por time e vantagem de mando global.
- Dependências:
  Schema e identidade dos times já entregues na Onda 1; não depende ainda de treino com dados reais.
- Arquivos prováveis:
  `src/edgehunter/core/poisson_model.py`
  `tests/unit/core/test_poisson_model.py`
- Testes obrigatórios:
  treino com dados sintéticos conhecidos;
  convergência do otimizador;
  lambdas positivos e finitos;
  probabilidades 1x2 somando 1.0 dentro da tolerância;
  fallback para time não visto usando prior médio da liga.
- Risco principal:
  não convergência ou estouro numérico com dados escassos.
- Critério de pronto:
  `train()` ou equivalente retorna sucesso em dataset sintético controlado;
  `predict_probabilities()` produz distribuição válida;
  zero `NaN`/`inf` em treino e inferência mínima.

### STORY-02-SUP - Micro-story de suporte de dados finalizados

- Objetivo:
  Entregar `update_match_result()` e `get_finished_matches_with_last_odds(valid_only=True)` para conectar o PRD-01 ao PRD-02 sem abrir Onda 3.
- Dependências:
  Usa apenas colunas já existentes em `matches` e `odds_snapshots`.
- Arquivos prováveis:
  `src/edgehunter/core/odds_historian.py`
  `tests/unit/core/test_odds_historian_results.py`
  `tests/unit/core/test_odds_historian_finished_matches_query.py`
- Testes obrigatórios:
  atualização idempotente do resultado;
  cálculo de `result` coerente;
  query trazendo somente partidas `finished`;
  exclusão de snapshots com `valid_for_analysis=False`;
  retorno estruturado compatível com treino.
- Risco principal:
  acoplamento indevido entre Onda 1 e Onda 2 se a equipe tentar puxar scheduler ou integrações externas junto.
- Critério de pronto:
  o `OddsHistorian` consegue fornecer dataset supervisionado de treino sem I/O externo e com filtros de qualidade.

### STORY-02-002 - Treinar com dados do OddsHistorian

- Objetivo:
  Construir o pipeline de treino por liga usando apenas partidas finalizadas com último snapshot válido.
- Dependências:
  `02-001` concluída e `02-SUP` concluída.
- Arquivos prováveis:
  `src/edgehunter/core/poisson_model.py`
  talvez `src/edgehunter/core/odds_historian.py` apenas para contrato de leitura, não para mudança de arquitetura;
  `tests/unit/core/test_poisson_training_pipeline.py`
- Testes obrigatórios:
  ignora partidas sem snapshot válido;
  ignora snapshots com `valid_for_analysis=False`;
  avisa se >20% dos snapshots históricos estiverem inválidos;
  falha cedo se número de partidas por liga ficar abaixo de `min_training_matches`.
- Risco principal:
  assumir que snapshots de odds por si só bastam para treino supervisionado. Não bastam; o treino depende do placar final.
- Critério de pronto:
  pipeline treina por liga com dataset real ou mockado derivado do `OddsHistorian`, sem misturar ligas e sem usar dados inválidos.

### STORY-02-003 - Persistir pesos e metadados do modelo

- Objetivo:
  Salvar e carregar pesos de ataque/defesa, vantagem de mando, data de treino e métricas mínimas.
- Dependências:
  `02-001` concluída; idealmente `02-002` também.
- Arquivos prováveis:
  `src/edgehunter/core/poisson_model.py`
  `tests/unit/core/test_poisson_persistence.py`
- Testes obrigatórios:
  round-trip save/load;
  preservação de floats dentro de tolerância;
  falha controlada para arquivo inexistente ou corrompido.
- Risco principal:
  escolher formato de persistência pesado cedo demais. JSON simples com metadados separados tende a ser a opção mais auditável na v1.
- Critério de pronto:
  pesos e metadados podem ser serializados e restaurados sem drift numérico relevante.

### STORY-02-004 - Predição 1x2

- Objetivo:
  Implementar inferência a partir de lambdas para retornar `home_win`, `draw` e `away_win`.
- Dependências:
  `02-001` concluída; pesos disponíveis por treino ou carga.
- Arquivos prováveis:
  `src/edgehunter/core/poisson_model.py`
  `tests/unit/core/test_poisson_predict.py`
- Testes obrigatórios:
  soma das probabilidades igual a 1;
  sem probabilidades negativas;
  time forte em casa contra time fraco gera `home_win` > `away_win`;
  cold start usa prior médio e não quebra.
- Risco principal:
  truncamento inadequado da matriz de gols ou PMF instável para placares mais altos.
- Critério de pronto:
  inferência determinística, estável e rápida, com contrato 1x2 consistente para consumidores futuros.

### STORY-02-007 - Testes adversariais

- Objetivo:
  Provar robustez numérica e comportamental do modelo antes de qualquer uso downstream.
- Dependências:
  `02-001`, `02-002` e `02-004`.
- Arquivos prováveis:
  `tests/unit/core/test_poisson_adversarial.py`
  possivelmente `tests/unit/core/test_poisson_model.py`
- Testes obrigatórios:
  `team_not_seen_in_training`;
  `extreme_team_strength_disparity`;
  `probabilities_sum_validation`;
  `convergence_with_minimal_data`;
  `handle_team_name_variations`;
  `zero_goal_handling`;
  cenários adicionais para `NaN`, `inf` e underflow.
- Risco principal:
  empurrar estes testes para o fim e descobrir tarde demais que a base matemática não é robusta.
- Critério de pronto:
  suíte adversarial passa de forma reprodutível e documenta o comportamento de fallback.

### STORY-02-008 - Sanity check pré-deployment

- Objetivo:
  Criar a barreira final que invalida modelo ruim antes de qualquer uso operacional.
- Dependências:
  `02-002`, `02-003`, `02-004` e `02-007`.
- Arquivos prováveis:
  `src/edgehunter/core/poisson_model.py`
  `tests/unit/core/test_poisson_sanity_check.py`
- Testes obrigatórios:
  hold-out dos últimos 20%;
  soma de probabilidades para confrontos canário;
  checagem de `result.success` do otimizador;
  rejeição do modelo quando accuracy/log-loss ficarem fora da faixa mínima;
  manutenção da versão anterior ao falhar.
- Risco principal:
  tentar acoplar scheduler, Telegram real ou promoção automática de modelo já nesta story.
- Critério de pronto:
  `sanity_check()` retorna decisão estruturada, impede promoção de modelo ruim e não depende de I/O externo real.

## 6. Estratégia de Testes

Testes mínimos da Onda 2:

- Testes unitários do núcleo matemático:
  PMF/log-likelihood, lambdas, soma de probabilidades, vantagem de mando e fallback de time não visto.
- Testes com dados sintéticos:
  dataset pequeno com parâmetros conhecidos para validar convergência aproximada.
- Testes de edge cases:
  dataset mínimo por liga;
  zeros de gols;
  placares extremos;
  times inéditos;
  nomes equivalentes já normalizados pela identidade determinística.
- Testes adversariais:
  `NaN`, `inf`, overflow, divergência de otimização, dados esparsos e alta disparidade entre equipes.
- Testes de integração local com OddsHistorian:
  nunca treinar com snapshots `valid_for_analysis=False`;
  nunca treinar com partida sem placar final;
  nunca misturar ligas.
- Sanity check do modelo:
  validação hold-out, probabilidades coerentes, latência de predição e flag de convergência do otimizador.

Gates obrigatórios da Onda 2:

- `python scripts/check_transaction_discipline.py`
- `python scripts/check_doc_consistency.py`
- suíte unitária nova focada em `poisson_model`

Status das validações auditadas agora:

- `git status --short` -> limpo
- `git log --oneline -12` -> inclui `14b5f0a` e tag `v0.2-onda1-fundacao-dados`
- `python scripts/check_doc_consistency.py` -> passou
- `python scripts/check_transaction_discipline.py` -> passou
- `python -m pytest` -> falhou fora do escopo por dependências do legado (`flask`, `playwright`) e por `remote_test.py` depender de `/app`

Separação de falha:

- Falha da Onda 2: nenhuma nesta auditoria de planejamento.
- Falha fora do escopo: suíte global do legado não está hermética neste ambiente.

## 7. Plano de Commits

Sugestão de estrutura por story:

- `docs(implementation): planejar execucao da Onda 2`
- `feat(poisson): implementar modelo base mle`
- `feat(oddshistorian): expor resultados finalizados para treino poisson`
- `feat(poisson): treinar com dados historicos validos`
- `feat(poisson): persistir pesos e metadados`
- `feat(poisson): implementar previsao 1x2`
- `test(poisson): adicionar testes adversariais`
- `test(poisson): adicionar sanity check pre-deployment`

Regra operacional:

- um commit por grupo lógico;
- validar imediatamente após cada story;
- não misturar PoissonModel com ValueDetector, GeminiValidator ou AutoEvolution.

## 8. Primeiro prompt de implementação recomendado

```md
use bmad-agent-dev

# Tarefa: Implementar STORY-02-001 - Algoritmo Poisson MLE

## Objetivo

Implementar apenas o núcleo do `PoissonModel` com:

- classe `PoissonModel`
- treinamento MLE com `scipy.optimize.minimize`
- parâmetros de ataque/defesa por time
- vantagem de mando global
- `predict_probabilities()` retornando `home_win`, `draw`, `away_win`
- fallback para time não visto com prior médio da liga

## Regras

- não implementar ValueDetector
- não implementar scheduler
- não implementar Telegram real
- não implementar execução financeira
- não treinar com dados reais do OddsHistorian ainda
- usar apenas dados sintéticos/controlados nesta story
- manter tudo fora de transação SQLite; esta story é matemática, não de persistência

## Arquivos esperados

- `src/edgehunter/core/poisson_model.py`
- `tests/unit/core/test_poisson_model.py`

## Validação obrigatória

```bash
python -m pytest tests/unit/core/test_poisson_model.py
python scripts/check_transaction_discipline.py
python scripts/check_doc_consistency.py
```
```

## 9. Decisão para Rafael

- [x] Pode iniciar STORY-02-001
- [ ] Pode iniciar com ressalvas
- [ ] Não deve iniciar ainda

Motivo:

O repositório está limpo, a Onda 1 foi concluída e os gates documentais e transacionais permanecem íntegros. A `STORY-02-001` pode começar sem depender ainda de resultados reais, desde que use dataset sintético e mantenha o escopo estritamente no núcleo matemático do Poisson.

O que não está autorizado é pular diretamente para `STORY-02-002` como se o `OddsHistorian` já oferecesse o dataset supervisionado completo do PRD-02. Antes disso, será necessário implementar a micro-story de suporte para resultados finalizados e query `valid_only=True`, ou incorporar esse suporte explicitamente ao plano da `02-002`.
