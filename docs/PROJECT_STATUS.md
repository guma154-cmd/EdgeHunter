# Status Final do Projeto — EdgeHunter

## Situação atual

```
Status  : Versão robusta local entregue
Release : v2.0-local-robust-release
Commit  : cc9e680
Modo    : local, simulado, read-only analítico
```

---

## O que o sistema faz

O EdgeHunter é um sistema de **observabilidade técnica e analítica local**, estritamente simulado e sem ações externas. Suas capacidades são:

| Capacidade | Descrição |
|------------|-----------|
| Classificação GREEN_SIM / RED_SIM | Avalia se a probabilidade implícita de um mercado simula valor técnico positivo ou negativo, com base no modelo Poisson local. |
| Ingestão de Outcomes | Recebe arquivos CSV/JSON com resultados históricos e os registra na base local. |
| Calibração Histórica | Calcula métricas de precisão, tendências e sugestões técnicas de threshold ao longo do tempo. |
| Score de Confiabilidade | Atribui score técnico a cada classificação com base em histórico e consenso de modelos. |
| Dashboard Visual Local | Interface read-only para visualização de classificações, outcomes e métricas de calibração. |
| Migrações Versionadas | Engine de migrações SQLite com journaling, planner e rollback controlado. |
| Backup/Restore | Utilitário de cópia segura do banco SQLite com validação de integridade e proteção contra path traversal. |
| Smoke Test | Testa rotas internas via `TestClient` sem abrir porta externa. |
| Release Check | Valida se o ambiente local está pronto para uso laboratorial. |
| Validação de Ambiente | Verifica Python, dependências e variáveis de configuração obrigatórias. |

---

## O que o sistema NÃO faz

| Restrição | Detalhe |
|-----------|---------|
| Não chama Gemini real | O validador Gemini opera em modo simulado/offline. |
| Não usa rede externa | Nenhuma chamada HTTP é feita durante operação normal. |
| Não faz scraping | Nenhum dado externo é capturado automaticamente. |
| Não executa ação financeira | O sistema não envia, movimenta ou simula movimentação de recursos. |
| Não envia mensagens externas | Sem integração com sistemas de mensageria (ex: Telegram). |
| Não usa agendamento operacional | Não há scheduler que execute ações automaticamente. |
| Não autoaplica threshold | Sugestões de threshold são exibidas como relatório estático — nunca aplicadas automaticamente. |

---

## Como rodar localmente

### 1. Instalar dependências

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar ambiente

```bash
cp .env.example .env
# Editar .env conforme necessário (manter READ_ONLY_MODE=true e ACTIONABLE=false)
```

### 3. Iniciar API local

```bash
python scripts/run_local_api.py
```

### 4. Acessar dashboard

Abrir no navegador: [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)

---

## Como validar

```bash
python -m pytest                              # suíte completa
python scripts/smoke_test_local.py           # smoke test das rotas
python scripts/release_check.py             # checklist de release
python scripts/check_doc_consistency.py     # consistência de docs
python scripts/check_transaction_discipline.py  # disciplina transacional
```

---

## Como interpretar o dashboard

- **GREEN_SIM**: classificação técnica positiva (probabilidade implícita abaixo do modelo Poisson). Dado estritamente analítico.
- **RED_SIM**: classificação técnica negativa. Dado estritamente analítico.
- **POSITIVE_OBSERVED / NEGATIVE_OBSERVED**: outcome registrado localmente após processamento de arquivo de resultados.
- **Calibração**: percentual de acerto histórico e tendência do modelo ao longo do tempo.
- Nenhum dado exibido constitui conselho ou recomendação de qualquer natureza.

---

## Como fazer backup e restore

```python
from src.edgehunter.ops.backup_restore import create_local_backup, restore_local_backup

# Backup
create_local_backup("data/edgehunter.db", "backups/")

# Restore (dry_run primeiro para validar)
restore_local_backup("backups/arquivo.bak", "data/edgehunter.db", dry_run=True)

# Restore efetivo
restore_local_backup("backups/arquivo.bak", "data/edgehunter.db", dry_run=False)
```

Ver: [docs/BACKUP_RESTORE.md](BACKUP_RESTORE.md)

---

## Limites conhecidos

- O sistema não possui autenticação robusta para múltiplos usuários (foi projetado para uso local individual).
- O banco SQLite não foi otimizado para volumes acima de centenas de milhares de registros.
- Os dashboards visuais são estáticos (sem atualização em tempo real via WebSocket).
- O `release_check.py` requer variáveis de ambiente configuradas para retornar status READY completo.

---

## Guardrails ativos

| Guardrail | Mecanismo |
|-----------|-----------|
| Read-only mode | Variável `EDGEHUNTER_READ_ONLY_MODE=true` validada na inicialização. |
| Modo não acionável | Variável `EDGEHUNTER_ACTIONABLE=false` validada. Qualquer violação gera exceção. |
| Linguagem proibida | Testes adversariais bloqueiam termos proibidos em documentos e scripts. |
| Path traversal | Backup/restore valida que o caminho de destino está dentro do diretório base. |
| Sem rede | Smoke test e release check operam via `TestClient` sem abertura de porta. |
