# Release Checklist - EdgeHunter

## 1. Verificações Prévias
- [ ] O código passou pelos linters e verificadores de disciplina (`python scripts/check_doc_consistency.py`, `python scripts/check_transaction_discipline.py`).
- [ ] O `pytest` passou com 100% de cobertura dos testes unitários e adversariais (`python -m pytest`).
- [ ] O branch ou working tree atual está limpo (`git status --short` vazio).

## 2. Configurações Locais
- [ ] O arquivo `.env.example` existe, não possui credenciais produtivas ou integrações não-locais.
- [ ] O ambiente local foi validado (`python scripts/run_local_api.py` inicializa corretamente).
- [ ] O modo "Read-Only" e "Simulado" é atestado como ativo na inicialização.

## 3. Resiliência Operacional (Health & Smoke)
- [ ] O `smoke_test_local.py` roda sem falhas, validando todas as rotas core sem abrir porta desnecessária no teste.
- [ ] O `release_check.py` aprova o empacotamento com "Status: READY".

## 4. Banco e Persistência
- [ ] O status das migrações do banco SQLite foi validado. Nenhuma pendência corrompe a estrutura.
- [ ] A ferramenta de backup local é comprovadamente capaz de salvar e restaurar (`DRY_RUN` incluso).

## 5. Manuais
- [ ] `OPERATIONS_MANUAL.md` foi atualizado.
- [ ] `LOCAL_DEPLOYMENT.md` foi atualizado e atesta a ausência de rede para funcionamento principal.
- [ ] `BACKUP_RESTORE.md` ensina como lidar com os dumps em `.bak`.
