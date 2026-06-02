# EdgeHunter — Guia de Deploy em Servidor 24/7

## Visão geral

Este guia documenta como implantar o EdgeHunter em um servidor Linux para
operação contínua (24/7) em modo local controlado.

O sistema opera **em dry-run por padrão**. Nenhuma integração externa é
ativada sem flag explícita no `.env`.

---

## Pré-requisitos

- Python 3.11+ instalado
- Git instalado
- Systemd disponível (Linux)
- Acesso ao servidor via SSH
- Usuário sem privilégios de root

---

## 1. Configurar o `.env`

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Edite com as configurações do ambiente:

```dotenv
# --- OBRIGATÓRIO ---
EDGEHUNTER_READ_ONLY_MODE=true

# --- RUNTIME (desabilitado por padrão) ---
EDGEHUNTER_RUNTIME_ENABLED=false
EDGEHUNTER_RUNTIME_DRY_RUN=true
EDGEHUNTER_RUNTIME_MAX_CYCLES=
EDGEHUNTER_RUNTIME_INTERVAL_SECONDS=300

# --- GEMINI (desabilitado por padrão) ---
GEMINI_ENABLED=false
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TIMEOUT_SECONDS=5
GEMINI_MAX_TOKENS=1024

# --- SCRAPER (desabilitado por padrão) ---
SCRAPER_ENABLED=false
SCRAPER_SOURCE_URL=
SCRAPER_TIMEOUT_SECONDS=10
SCRAPER_RATE_LIMIT_SECONDS=5
SCRAPER_USER_AGENT=EdgeHunterLocalResearch/1.0

# --- TELEGRAM (desabilitado por padrão) ---
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_TIMEOUT_SECONDS=5
```

> **Atenção**: Nunca commite o `.env` com segredos reais.

---

## 2. Iniciar a API

```bash
python -m uvicorn src.edgehunter.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

Verificar:

```bash
curl http://localhost:8000/health
```

---

## 3. Iniciar o Runtime

```bash
python scripts/run_runtime.py
```

O runtime inicia em **dry-run** por padrão e executa indefinidamente.
Para limitar ciclos (útil em testes):

```bash
EDGEHUNTER_RUNTIME_MAX_CYCLES=5 python scripts/run_runtime.py
```

---

## 4. Rodar smoke test

```bash
python scripts/smoke_test_local.py
```

---

## 5. Ativar systemd

```bash
# Copiar o arquivo de exemplo
cp deploy/systemd/edgehunter.service.example /etc/systemd/system/edgehunter.service

# Revisar e ajustar WorkingDirectory e User
nano /etc/systemd/system/edgehunter.service

# Recarregar e habilitar
sudo systemctl daemon-reload
sudo systemctl enable edgehunter
sudo systemctl start edgehunter
```

---

## 6. Ver logs

```bash
# Logs do runtime via journald
sudo journalctl -u edgehunter -f

# Logs da API (se rodando em processo separado)
tail -f logs/api.log
```

---

## 7. Reiniciar o serviço

```bash
sudo systemctl restart edgehunter
```

---

## 8. Backup e Restore

Criar backup:

```bash
python scripts/backup_db.py
```

Restaurar:

```bash
python scripts/restore_db.py --backup-file backups/edgehunter_YYYYMMDD_HHMMSS.db
```

---

## 9. Validar release

```bash
python scripts/release_check.py
python scripts/clean_install_check.py
python -m pytest
```

---

## Flags de integração

| Flag | Padrão | Descrição |
|------|--------|-----------|
| `GEMINI_ENABLED` | `false` | Ativa Gemini real |
| `SCRAPER_ENABLED` | `false` | Ativa scraper |
| `TELEGRAM_ENABLED` | `false` | Ativa Telegram |
| `EDGEHUNTER_RUNTIME_ENABLED` | `false` | Ativa runtime |
| `EDGEHUNTER_RUNTIME_DRY_RUN` | `true` | Modo dry-run |

---

## Guardrails permanentes

- Sem execução financeira automática.
- Sem stake, Kelly, bankroll.
- Sem autoaplicação de threshold.
- Sem Telegram operacional.
- Sem loop infinito em testes.
- Sem segredos em código ou repositório.
