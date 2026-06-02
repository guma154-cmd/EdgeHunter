# ONDA 11 EXECUTION PLAN

## 1. Veredicto da Onda 11
A Onda 11 está aprovada em modo autônomo controlado para construir um engine seguro e governado de migrações versionadas. A abordagem continuará aderindo rigorosamente às diretrizes de operação simulada, sem ações financeiras e sem execuções externas.

## 2. Objetivo Técnico
Criar um engine controlado de migrações versionadas para o banco SQLite do EdgeHunter, transformando o registro lógico existente numa infraestrutura real de governança de schema.

## 3. Escopo Permitido
- Criar a tabela `schema_migrations`.
- Registrar migrações aplicadas.
- Aplicar migrações idempotentes e seguras.
- Executar dry-run planejado (sem alterar base).
- Validar schema antes/depois da migração.
- Bloquear proativamente migrações perigosas.
- Expor status via API read-only.
- Implementar testes unitários e adversariais.
- Produzir relatórios técnicos de encerramento.

## 4. Escopo Proibido
- Qualquer execução financeira (stake, bankroll, Kelly).
- Modificações destrutivas sem bloqueio (DROP TABLE, DROP COLUMN, DELETE arbitrário).
- Execução de SQL arbitrário ou dinâmico oriundo de input externo.
- Ações automatizadas externas (Telegram, AutoEvolution).
- Consultas a LLM (Gemini) na execução principal de migração.
- Chamadas de rede externas e Auto-apply de limites.

## 5. Estratégia de Migração
Migrações serão concebidas como contratos determinísticos e seguros. Cada migração possuirá metadados rigorosos atestando que é segura. O engine somente executará migrações marcadas explicitamente como "SAFE".

## 6. Estratégia de Dry-Run
O `migration_planner` examinará o status da base atual comparando o schema de introspection com os metadados do journal. A operação base será o *dry-run*, produzindo um `MigrationPlan` para auditoria que detalha as ações pendentes sem executar nenhuma alteração.

## 7. Estratégia de Journal
O histórico ficará registrado na tabela interna `schema_migrations`, gravando version, status (APPLIED, SKIPPED, BLOCKED), checksum e detalhes técnicos da execução.

## 8. Estratégia de Rollback Lógico
Rollback nativo destrutivo não será suportado inicialmente nesta onda. O rollback limitará-se a ações lógicas (pular migração falha) e falha transacional rápida. 

## 9. Stories Propostas
- STORY-11-001: Plano formal da Onda 11
- STORY-11-002: Contratos de Migração Versionada
- STORY-11-003: Journal de Migrações Aplicadas
- STORY-11-004: Planejador Dry-run de Migrações
- STORY-11-005: Aplicador Controlado de Migrações
- STORY-11-006: API Read-only de Status de Migrações
- STORY-11-007: Testes Adversariais de Migração
- STORY-11-008: Encerramento da Onda 11

## 10. Estratégia de Testes
TDD cobrindo: sucesso, cenários determinísticos, mock de transações, injeção de SQL arbitrário (bloqueio garantido), e validações contratuais de linguajar seguro (is_simulated=True). Validador adversarial deverá cobrir DROP/DELETE/ALTER e falhas transacionais.

## 11. Guardrails
As migrações seguem isoladas das lógicas analíticas. Todo contrato e retorno de API será filtrado por termos operacionais. Nenhuma migração pode ser aplicada sem `allow_apply=True` restrito.

## 12. Critérios de Encerramento
100% de passagem nos testes da suíte (`pytest`), clean `git diff`, scripts validadores de transação (`check_transaction_discipline.py`) e consistência (`check_doc_consistency.py`) em verde. Criação de relatório de conclusão.

## 13. Tag Alvo
`v1.4-onda11-migration-engine`
