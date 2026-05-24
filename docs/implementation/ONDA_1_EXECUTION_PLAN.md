# Plano de Execucao da Onda 1

## Escopo

Este plano cobre a Onda 1 definida em `docs/implementation/IMPLEMENTATION_WAVES.md`:

- `STORY-01-002`: Schema SQL idempotente
- `STORY-01-003`: Registrar match novo detectado pelos scrapers
- `STORY-01-004`: Armazenar snapshot validado com sincronia
- `STORY-01-007`: Health check de scrapers
- `STORY-01-010`: Backup automatico do SQLite

Premissas obrigatorias:

- `FREEZE.md` esta aprovado.
- `docs/prd/01_odds_historian.md` e a fonte primaria de requisitos.
- SQLite permanece com `WAL + busy_timeout=5000ms + transacoes curtas`.
- Nenhuma implementacao desta onda deve introduzir I/O de rede dentro de transacao aberta.
- Toda automacao operacional deve permanecer em modo tecnico/simulado durante desenvolvimento e testes locais.

## Verificacao inicial

Base documental usada neste plano:

- `FREEZE.md`
- `docs/implementation/IMPLEMENTATION_WAVES.md`
- `docs/prd/01_odds_historian.md`
- `docs/stories/stories_detalhadas.md`
- `docs/architecture/transaction-discipline.md`
- `docs/decisions/sqlite_concurrency_validation.md`

Estado atual relevante do repositorio:

- Ja existe base de schema em `src/edgehunter/database/schema.py`.
- Ja existe observabilidade SQLite em `src/edgehunter/database/sqlite_observability.py`.
- `src/edgehunter/core/odds_historian.py` ainda esta vazio.
- O ponto natural de integracao operacional e `backend/app/data/scheduler.py`.

## Divergencias que afetam o planejamento

### 1. `STORY-01-003` depende de `STORY-01-001`

O PRD exige que `register_match()` use `generate_match_id()`, mas `STORY-01-001` nao esta na Onda 1.

Decisao de planejamento:

- `STORY-01-003` deve ser quebrada em subtarefas.
- A primeira subtarefa precisa entregar o minimo viavel de `match_id` como prerequisito interno da propria `01-003`, sem abrir nova frente arquitetural.

### 2. `STORY-01-007` esta desalinhada entre PRD e story detalhada

O PRD aceito define `01-007` como health check de scrapers com persistencia em `scraper_health`, deteccao de stale odds, divergencia e alerta Telegram.

Ja `docs/stories/stories_detalhadas.md` descreve um endpoint HTTP `/health`, que e outra entrega.

Decisao de planejamento:

- Para `01-007`, a fonte de verdade sera o PRD aceito.
- Antes de implementar `01-007`, o time deve gerar um story-detail corrigido e alinhado ao PRD.
- O endpoint `/health` nao entra nesta story enquanto nao houver nova decisao formal.

### 3. `STORY-01-010` tambem tem drift entre PRD e story detalhada

O PRD aceito fala em:

- backup as `03:00 UTC`
- retencao de `7` backups
- `wal_checkpoint(FULL)`
- `.db`, `.db-wal`, `.db-shm`
- restore documentado

Ja a story detalhada menciona retencao de `14 dias` e `docs/runbooks/db_restore.md`, enquanto o repositorio hoje ja tem `docs/operations/backup_restore.md`.

Decisao de planejamento:

- Para `01-010`, a fonte de verdade sera o PRD aceito e o runbook operacional existente.
- Antes de implementar `01-010`, o story-detail deve ser reemitido alinhado a `7` rotacoes e ao caminho documental atual.

## Ordem recomendada da Onda 1

1. `STORY-01-002`
2. `STORY-01-003`
3. `STORY-01-004`
4. `STORY-01-007`
5. `STORY-01-010`

Justificativa:

- `01-002` cria a base persistente e valida a configuracao SQLite obrigatoria.
- `01-003` depende do schema e estabelece a identidade estavel dos jogos.
- `01-004` depende de `register_match()` e fecha o contrato de ingestao historica.
- `01-007` depende de dados e timestamps persistidos por `01-003/01-004`.
- `01-010` depende do banco e do fluxo de dados ja estabilizados para validar backup de um estado realista.

Observacao:

- `01-010` e critica operacionalmente e deve entrar cedo na onda, mas nao antes de `01-004`, porque o valor do backup e menor se o pipeline historico ainda nao estiver produzindo dados de forma consistente.

## Plano por story

### STORY-01-002 — Schema SQL idempotente

Objetivo:

- Consolidar um schema SQLite idempotente para `matches`, `odds_snapshots` e `scraper_health`, com PRAGMAs de concorrencia e indices alinhados ao PRD.

Arquivos que provavelmente serao alterados:

- `src/edgehunter/database/schema.py`
- `src/edgehunter/core/odds_historian.py`
- `scripts/init_db.py`
- `tests/unit/database/test_schema.py`
- possivelmente `tests/integration/` para smoke test de inicializacao

Testes obrigatorios:

- primeira execucao em banco vazio
- reexecucao sem erro nem drift
- verificacao dos PRAGMAs `journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON`
- verificacao de tabelas, colunas e indices exigidos pelo PRD
- teste de compatibilidade com o caminho real de banco configurado no projeto

Riscos:

- o schema atual em `src/edgehunter/database/schema.py` nao bate 100% com o PRD aceito
- drift entre nomes de colunas (`scheduled_time` vs `match_date`, `bookmakers_synced` inteiro vs JSON/texto)
- risco de criar schema valido tecnicamente, mas incompatível com consumidores futuros

Mitigacao:

- usar o PRD-01 como contrato de nomes e tipos
- revisar `test_schema.py` para validar colunas exatas, nao apenas existencia de tabelas
- manter configuracao SQLite no modulo de schema, nao espalhada em varios pontos

Criterio de pronto:

- schema aplicado idempotentemente
- colunas e indices compatíveis com PRD-01
- testes unitarios de schema passando
- nenhum write path novo viola a politica de transacao

Subtarefas:

1. reconciliar schema atual com o PRD aceito
2. expor inicializacao reutilizavel para `OddsHistorian`
3. fortalecer testes de idempotencia e colunas

### STORY-01-003 — Registrar match novo detectado pelos scrapers

Objetivo:

- introduzir `register_match()` idempotente com validacao de timezone e identidade deterministica de partida.

Arquivos que provavelmente serao alterados:

- `src/edgehunter/core/odds_historian.py`
- `backend/app/utils/match_id.py` ou `src/edgehunter/core/` equivalente consolidado
- `backend/app/data/scheduler.py`
- `tests/unit/core/` com novo teste de `match_id`
- `tests/unit/data/` para integracao leve com scheduler

Testes obrigatorios:

- `generate_match_id()` deterministico para inputs identicos
- rejeicao de `datetime` naive
- `register_match()` sem duplicacao ao reenviar o mesmo jogo
- deteccao de colisao logica improvavel
- teste de integracao leve com payload vindo dos scrapers

Riscos:

- dependencia escondida da `STORY-01-001`
- normalizacao de nomes de time pode colapsar entidades distintas se for agressiva demais
- timezone inconsistente entre scrapers atuais

Mitigacao:

- quebrar a story em subtarefas e entregar primeiro o utilitario minimo de `match_id`
- validar casos criticos do PRD (`Manchester United` vs `Manchester City`, etc.)
- falhar cedo para timestamps naive

Criterio de pronto:

- `register_match()` retorna `match_id` estavel
- mesma partida nao duplica
- payload sem timezone e rejeitado
- testes de `match_id` cobrindo casos reais e colisoes semanticas

Subtarefas:

1. utilitario minimo de `match_id`
2. persistencia idempotente em `matches`
3. hook de integracao no fluxo de coleta

### STORY-01-004 — Armazenar snapshot validado com sincronia

Objetivo:

- implementar `store_snapshot()` com validacao de odds, timestamps, `max_latency_seconds`, `bookmakers_synced` e `valid_for_analysis`.

Arquivos que provavelmente serao alterados:

- `src/edgehunter/core/odds_historian.py`
- `src/edgehunter/database/schema.py`
- `backend/app/data/scheduler.py`
- possivelmente adaptadores em `backend/app/data/direct_scrapers.py`, `odds_api.py`, `oddsportal_scraper.py`, `bet365_scraper.py`
- `tests/unit/core/` com nova suite de `OddsHistorian`
- `tests/unit/data/test_scheduler.py`
- `tests/integration/` para payload mockado fim a fim

Testes obrigatorios:

- odds fora do range `1.01` a `100.0` falham
- timestamp naive falha
- `max_latency_seconds` calculado corretamente
- `latency == 120s` e `latency > 120s`
- snapshot invalido por latencia ainda e persistido com `valid_for_analysis=False`
- `match_id` inexistente falha

Riscos:

- scrapers atuais podem nao expor timestamps UTC no formato esperado
- divergencia entre story detalhada e PRD sobre `failed_snapshots`
- risco de alongar transacao se validacao, serializacao ou logging pesados ficarem dentro do write path

Mitigacao:

- tratar o PRD aceito como contrato principal
- limitar a transacao a insert local
- normalizar payload antes de abrir a escrita SQLite

Criterio de pronto:

- snapshots validos e invalidos persistem conforme regra do PRD
- `valid_for_analysis` e `max_latency_seconds` confiaveis
- integracao com `register_match()` funcionando
- testes de borda cobrindo sincronia e ranges

Subtarefas:

1. contrato de payload canonical
2. validacao pura em memoria
3. persistencia curta
4. adaptacao do scheduler para chamar `store_snapshot()`

### STORY-01-007 — Health check de scrapers

Objetivo:

- implementar monitoramento de saude dos scrapers baseado em dados persistidos, com status `healthy/warning/critical`, escrita em `scraper_health` e gatilho de alerta.

Arquivos que provavelmente serao alterados:

- `src/edgehunter/core/odds_historian.py`
- `backend/app/data/scheduler.py`
- `backend/app/alerts/telegram_bot.py`
- `tests/unit/data/test_scheduler.py`
- novos testes unitarios de `scraper_health`

Testes obrigatorios:

- scraper sem dados por 2 ciclos vira `warning` ou `critical` conforme regra definida
- stale odds em 1h
- divergencia > 10% entre Pinnacle e OddsPortal
- persistencia correta em `scraper_health`
- alerta disparado de forma desacoplada da transacao de escrita

Riscos:

- drift documental: a story detalhada atual descreve `/health`, nao scraper health
- alertas Telegram podem reintroduzir o anti-padrao de I/O dentro de transacao
- regras de severidade podem ficar ambiguas sem matriz simples de status

Mitigacao:

- nao implementar a partir da story detalhada atual; primeiro reemitir story alinhada ao PRD
- manter escrita e alerta desacoplados
- definir tabela de decisao simples para status e gatilhos

Criterio de pronto:

- `scraper_health` alimentada por job dedicado
- criterios de stale/no_data/divergence cobertos por teste
- alerta emitido fora da transacao
- `check_transaction_discipline.py` continua passando

Subtarefas:

1. alinhar detalhe da story ao PRD
2. calcular status de saude
3. persistir resultados
4. acoplar alerta assíncrono/adiado sem violar disciplina de transacao

### STORY-01-010 — Backup automatico do SQLite

Objetivo:

- automatizar backup tecnico do SQLite com `sqlite3.backup()`, `wal_checkpoint(FULL)`, gzip, rotacao de 7 backups, validacao de integridade e alerta em falha.

Arquivos que provavelmente serao alterados:

- `backend/app/data/db_backup.py` ou equivalente em `src/edgehunter/database/`
- `backend/app/data/scheduler.py`
- `scripts/init_db.py` se houver consolidacao de utilitarios de caminho do banco
- `tests/unit/data/` e `tests/unit/database/`
- `docs/operations/backup_restore.md` apenas se surgirem ajustes estritamente necessarios de implementacao

Testes obrigatorios:

- job registra execucao prevista as `03:00 UTC`
- `wal_checkpoint(FULL)` executado antes do snapshot
- backup via `sqlite3.backup()`
- compressao gzip
- rotacao mantendo `7` backups
- copia de `-wal` e `-shm` quando existirem
- `PRAGMA integrity_check` no artefato gerado
- falha de escrita gera alerta sem fazer operacao real externa em testes

Riscos:

- drift documental entre story detalhada e PRD sobre retencao e caminho do runbook
- risco de backup tocar o banco ativo com transacao longa
- risco de testes criarem dependencia em filesystem real ou cron real

Mitigacao:

- usar PRD aceito e runbook operacional atual como contrato
- encapsular backup em funcao testavel sem cron real
- usar testes com diretórios temporarios e banco temporario

Criterio de pronto:

- backup simulado e reproduzivel por teste
- retencao de `7` backups aplicada
- integridade validada
- scheduler apenas registra o job; nao executa operacao real em planejamento/teste local

Subtarefas:

1. alinhar detalhe da story ao PRD e ao runbook atual
2. implementar pipeline de backup puro
3. integrar job no scheduler
4. testar rotacao e integridade

## Riscos transversais da Onda 1

| Risco | Impacto | Mitigacao |
|---|---|---|
| Drift entre PRD aceito e stories detalhadas | Implementacao do requisito errado | PRD-01 e a fonte de verdade; reemitir story-detail antes de `01-007` e `01-010` |
| Dependencia oculta de `STORY-01-001` | Bloqueio em `01-003` | Tratar `match_id` como subtarefa obrigatoria de `01-003` |
| Reintroducao de transacoes longas | Lock contention e regressao arquitetural | Validar toda escrita nova contra `docs/architecture/transaction-discipline.md` |
| Payload heterogeneo dos scrapers | Falhas de integracao em `01-003/01-004` | Criar contrato canonical antes de persistir |
| Schema divergente do PRD | Downstream quebrado em PRD-02/03 | Validar nomes de colunas por teste e revisar antes de integrar |

## Estrategia de testes da Onda 1

Minimo obrigatorio por story:

- unitarios do modulo alterado
- teste de integracao leve do caminho scheduler -> historian quando aplicavel
- reexecucao de `python scripts/check_transaction_discipline.py` apos qualquer mudanca que toque writers

Suite recomendada por marco:

1. apos `01-002`
   - `pytest tests/unit/database/test_schema.py`
2. apos `01-003`
   - testes de `match_id`
   - teste de idempotencia de `register_match()`
3. apos `01-004`
   - testes de payload/latencia/range
   - teste de integracao de persistencia
4. apos `01-007`
   - testes de severidade e persistencia em `scraper_health`
   - `python scripts/check_transaction_discipline.py`
5. apos `01-010`
   - testes de backup/rotacao/integridade
   - smoke da suite unitaria relevante

## Primeiro prompt de implementacao recomendado

Comecar por `STORY-01-002`, porque ela:

- nao depende do `match_id`
- nao depende de story-detail em conflito
- reduz risco estrutural para todas as demais

Prompt recomendado:

```text
use bmad-agent-dev

# Tarefa: Implementar STORY-01-002 — Schema SQL idempotente

Contexto:
- Seguir `docs/implementation/ONDA_1_EXECUTION_PLAN.md`
- Fonte primaria: `docs/prd/01_odds_historian.md`
- Respeitar `docs/architecture/transaction-discipline.md`
- Nao implementar operacao real externa

Objetivo:
- alinhar `src/edgehunter/database/schema.py` ao schema aceito do PRD-01
- manter WAL, busy_timeout=5000ms, foreign_keys=ON
- garantir idempotencia real e testes fortes de colunas/indices

Validacao minima:
- pytest tests/unit/database/test_schema.py
- python scripts/check_transaction_discipline.py
```

## Veredicto

**APROVADO PARA COMECAR STORY-01-002**

Condicoes:

- `01-002` pode iniciar imediatamente.
- `01-003` pode iniciar em seguida, desde que seja quebrada para incluir o prerequisito minimo de `match_id`.
- `01-007` e `01-010` nao devem ser implementadas diretamente a partir do texto atual de `docs/stories/stories_detalhadas.md`; antes, seus story-details precisam ser realinhados ao PRD aceito.
