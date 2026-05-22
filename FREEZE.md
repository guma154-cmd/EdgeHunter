# Document Freeze — EdgeHunter v0.1

**Status**: [ ] PENDENTE / [ ] APROVADO

## Executor do freeze

Verificado por: Codex + Claude
Aprovado por: Rafael [assina via commit]

## Como aprovar

Rafael faz commit com mensagem:
`docs: freeze v0.1 - autoriza inicio da implementacao`

## Checklist de critérios materiais (todos obrigatórios)

### Consistência arquitetural
- [ ] Nenhuma story menciona tecnologia fora do stack do ADR-004
- [ ] Nenhuma story menciona PostgreSQL/pg_dump/PL-pgSQL/S3/MLflow
- [ ] Cross-references entre PRDs/ADRs/Stories usam nomes de arquivo corretos

### Prontidão documental
- [ ] Todos os 6 PRDs com status "Accepted" (não Draft/Rascunho)
- [ ] Todas as questões em aberto: resolvidas ou deferidas com default
- [ ] Markdown sem corrupção de fence
- [ ] Links internos funcionando (script `check_doc_consistency.py` valida)

### Decisões formais
- [ ] SQLite validado contra workload real de concorrência
- [ ] Recorte MVP 20/54 declarado explicitamente
- [ ] Ondas de implementação definidas (`IMPLEMENTATION_WAVES.md`)
- [ ] Decisões deferidas com defaults em `deferred_decisions.md`

### Validação automática
- [ ] `python scripts/check_doc_consistency.py` retorna exit code 0
- [ ] `python scripts/check_transaction_discipline.py` retorna exit code 0
- [ ] `python -m pytest tests/unit/scripts/` passa 100%

### Governança
- [ ] Este arquivo (`FREEZE.md`) preenchido e revisado
- [ ] Commit hash do freeze: [preencher no sign-off]
- [ ] Data do freeze: [preencher no sign-off]

## O que o freeze autoriza

- Início da implementação Onda 1
- Codex pode gerar código baseado nos documentos acima

## O que o freeze NÃO cobre

- Stories das Ondas 2-5 (serão detalhadas no início de cada onda)
- Questões deferidas (serão decididas conforme gatilhos em `deferred_decisions.md`)
- Atualizações de ADR por mudança de stack (requerem novo ciclo de revisão)
