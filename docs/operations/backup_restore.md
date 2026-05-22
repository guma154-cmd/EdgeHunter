# Backup e Restore do SQLite

## Objetivo

Este runbook permite operar backup e restore do banco SQLite do EdgeHunter sem depender de contexto externo.

O EdgeHunter usa SQLite com WAL. Isso muda o procedimento:

- o arquivo principal `.db` nao e suficiente sozinho enquanto houver WAL pendente
- antes de copiar, execute checkpoint do WAL
- o backup operacional deve considerar `.db`, `.db-wal` e `.db-shm`

## Antes de comecar

### Descobrir o banco ativo

Existe inconsistencia historica no repositorio:

- `backend/app/config.py` usa por padrao `database/edgehunter.db`
- `README.md` e `.env.example` mencionam `edge_hunter.db`

Nao assuma. Descubra o caminho ativo primeiro.

No host do projeto:

```bash
cd /home/telematica/EdgeHunter
python - <<'PY'
import os
from backend.app.config import Config
print(Config.SQLALCHEMY_DATABASE_URI)
PY
```

Se a saida comecar com `sqlite:///`, remova esse prefixo e use o caminho resultante como `DB_PATH`.

Exemplo de caminho padrao atual:

```text
/home/telematica/EdgeHunter/database/edgehunter.db
```

### Pre-requisitos

- acesso shell ao host
- Python 3 disponivel
- permissao de escrita no diretorio de backup
- processo do EdgeHunter identificado para stop/start controlado, se o restore for necessario

### Diretorio de backup

Este runbook assume:

```text
/home/telematica/EdgeHunter/backups
```

Crie uma vez, se nao existir:

```bash
mkdir -p /home/telematica/EdgeHunter/backups
```

## Backup manual

### Passo 1: exportar variaveis

```bash
cd /home/telematica/EdgeHunter
export DB_PATH="/home/telematica/EdgeHunter/database/edgehunter.db"
export BACKUP_DIR="/home/telematica/EdgeHunter/backups"
mkdir -p "$BACKUP_DIR"
```

### Passo 2: executar WAL checkpoint antes da copia

Use `wal_checkpoint(FULL)` no banco ativo:

```bash
python - <<'PY'
import os
import sqlite3

db_path = os.environ["DB_PATH"]
conn = sqlite3.connect(db_path, timeout=30)
row = conn.execute("PRAGMA wal_checkpoint(FULL);").fetchone()
print({"busy": row[0], "log_frames": row[1], "checkpointed_frames": row[2]})
conn.close()
PY
```

Resultado esperado:

- `busy = 0`
- `checkpointed_frames` proximo de `log_frames`

Se `busy != 0`, repita o comando. Se continuar ocupado, investigue writer preso antes de prosseguir.

### Passo 3: gerar snapshot consistente com `sqlite3.backup()`

Este passo cria um snapshot `.db` consistente:

```bash
export SNAPSHOT_DB="$(python - <<'PY'
import os
import sqlite3
from datetime import datetime, timezone

db_path = os.environ["DB_PATH"]
backup_dir = os.environ["BACKUP_DIR"]
ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
snapshot_path = os.path.join(backup_dir, f"edgehunter_{ts}.db")

src = sqlite3.connect(db_path, timeout=30)
dst = sqlite3.connect(snapshot_path)
src.backup(dst)
dst.close()
src.close()

print(snapshot_path)
PY
)"
echo "$SNAPSHOT_DB"
```

### Passo 4: copiar os auxiliares `.db-wal` e `.db-shm`

Depois do checkpoint e do snapshot, copie os auxiliares se existirem:

```bash
[ -f "${DB_PATH}-wal" ] && cp -f "${DB_PATH}-wal" "${SNAPSHOT_DB}-wal"
[ -f "${DB_PATH}-shm" ] && cp -f "${DB_PATH}-shm" "${SNAPSHOT_DB}-shm"
```

Observacoes:

- o arquivo principal confiavel para restore e o criado por `sqlite3.backup()`
- os arquivos `-wal` e `-shm` sao guardados por exigencia operacional do PRD-01 e para analise forense se necessario
- se o checkpoint drenou totalmente o WAL, esses auxiliares podem estar vazios ou nem existir

### Passo 5: validar integridade do snapshot

```bash
python - <<'PY'
import os
import sqlite3

snapshot_db = os.environ["SNAPSHOT_DB"]
conn = sqlite3.connect(snapshot_db)
result = conn.execute("PRAGMA integrity_check;").fetchone()[0]
print(result)
conn.close()
PY
```

Resultado esperado:

```text
ok
```

Se nao retornar `ok`, descarte o backup e refaca o processo.

## Backup diario

## Politica operacional

- horario: `03:00 UTC`
- retencao: `7` backups
- destino: `backups/`
- validacao obrigatoria: `wal_checkpoint(FULL)` antes da copia e `PRAGMA integrity_check` no snapshot

## Script operacional minimo

Enquanto o job dedicado de backup nao existir no codigo da aplicacao, use o script abaixo como referencia operacional. Salve no host como `scripts/daily_sqlite_backup.sh` se precisar automatizar.

```bash
#!/usr/bin/env bash
set -euo pipefail

cd /home/telematica/EdgeHunter
export DB_PATH="/home/telematica/EdgeHunter/database/edgehunter.db"
export BACKUP_DIR="/home/telematica/EdgeHunter/backups"
mkdir -p "$BACKUP_DIR"

SNAPSHOT_DB="$(python - <<'PY'
import os
import sqlite3
from datetime import datetime, timezone

db_path = os.environ["DB_PATH"]
backup_dir = os.environ["BACKUP_DIR"]
ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
snapshot_path = os.path.join(backup_dir, f"edgehunter_{ts}.db")

conn = sqlite3.connect(db_path, timeout=30)
conn.execute("PRAGMA wal_checkpoint(FULL);").fetchone()
dst = sqlite3.connect(snapshot_path)
conn.backup(dst)
dst.close()
conn.close()
print(snapshot_path)
PY
)"
export SNAPSHOT_DB

python - <<'PY'
import os
import sqlite3

snapshot_db = os.environ["SNAPSHOT_DB"]
conn = sqlite3.connect(snapshot_db)
result = conn.execute("PRAGMA integrity_check;").fetchone()[0]
conn.close()
if result != "ok":
    raise SystemExit(f"integrity_check falhou: {result}")
print("integrity_check=ok")
PY

[ -f "${DB_PATH}-wal" ] && cp -f "${DB_PATH}-wal" "${SNAPSHOT_DB}-wal"
[ -f "${DB_PATH}-shm" ] && cp -f "${DB_PATH}-shm" "${SNAPSHOT_DB}-shm"
gzip -f "$SNAPSHOT_DB"

ls -1t "$BACKUP_DIR"/edgehunter_*.db.gz | tail -n +8 | xargs -r rm -f
ls -1t "$BACKUP_DIR"/edgehunter_*.db-wal 2>/dev/null | tail -n +8 | xargs -r rm -f
ls -1t "$BACKUP_DIR"/edgehunter_*.db-shm 2>/dev/null | tail -n +8 | xargs -r rm -f
```

## Cron

Exemplo de agendamento diario as `03:00 UTC`:

```cron
0 3 * * * /home/telematica/EdgeHunter/scripts/daily_sqlite_backup.sh >> /home/telematica/EdgeHunter/backups/backup.log 2>&1
```

## Restore

### Quando usar

- corrupcao do banco ativo
- deploy ou migracao que deixou o banco inconsistente
- rollback operacional para ultimo backup integro

### Passo a passo

### Passo 1: identificar o backup a restaurar

Liste os candidatos:

```bash
ls -lh /home/telematica/EdgeHunter/backups
```

Escolha um `.db.gz` validado. Exemplo:

```text
/home/telematica/EdgeHunter/backups/edgehunter_20260522T030000Z.db.gz
```

### Passo 2: parar o processo do EdgeHunter

Se voce abriu um shell novo desde o backup, reexporte `DB_PATH` antes de continuar:

```bash
export DB_PATH="/home/telematica/EdgeHunter/database/edgehunter.db"
```

Se estiver em Docker Compose:

```bash
cd /home/telematica/EdgeHunter
docker compose stop backend
```

Se o host usar `docker-compose` legado:

```bash
cd /home/telematica/EdgeHunter
docker-compose stop backend
```

Nao faca restore com writer ativo.

### Passo 3: proteger o banco atual antes de sobrescrever

```bash
cp -f "$DB_PATH" "${DB_PATH}.pre_restore.$(date -u +%Y%m%dT%H%M%SZ)"
[ -f "${DB_PATH}-wal" ] && cp -f "${DB_PATH}-wal" "${DB_PATH}-wal.pre_restore.$(date -u +%Y%m%dT%H%M%SZ)"
[ -f "${DB_PATH}-shm" ] && cp -f "${DB_PATH}-shm" "${DB_PATH}-shm.pre_restore.$(date -u +%Y%m%dT%H%M%SZ)"
```

### Passo 4: descompactar o backup escolhido

```bash
gzip -dc /home/telematica/EdgeHunter/backups/edgehunter_20260522T030000Z.db.gz > /tmp/edgehunter_restore.db
```

### Passo 5: validar o arquivo antes de promover

```bash
python - <<'PY'
import sqlite3
conn = sqlite3.connect("/tmp/edgehunter_restore.db")
print(conn.execute("PRAGMA integrity_check;").fetchone()[0])
conn.close()
PY
```

So continue se o retorno for `ok`.

### Passo 6: substituir o banco ativo

```bash
cp -f /tmp/edgehunter_restore.db "$DB_PATH"
rm -f "${DB_PATH}-wal" "${DB_PATH}-shm"
```

Remover `-wal` e `-shm` antigos evita reuso de artefatos de outra geracao.

### Passo 7: subir o processo novamente

Docker Compose v2:

```bash
cd /home/telematica/EdgeHunter
docker compose up -d backend
```

Docker Compose v1:

```bash
cd /home/telematica/EdgeHunter
docker-compose up -d backend
```

## Verificacao pos-restore

### 1. Integridade do banco ativo

```bash
python - <<'PY'
import os
import sqlite3
db_path = os.environ["DB_PATH"]
conn = sqlite3.connect(db_path)
print(conn.execute("PRAGMA integrity_check;").fetchone()[0])
conn.close()
PY
```

Esperado: `ok`.

### 2. Health HTTP da aplicacao

```bash
curl -fsS http://127.0.0.1:5000/api/health
```

Esperado:

```json
{"status":"ok","version":"1.0.0"}
```

### 3. Logs do container

```bash
cd /home/telematica/EdgeHunter
docker compose logs --tail=100 backend
```

Verifique:

- ausencia de `sqlite3.OperationalError`
- ausencia de `database is locked` em loop
- heartbeat ou startup Telegram voltando ao normal

## Falha de restore

Se a aplicacao nao subir apos o restore:

1. pare o processo novamente
2. restaure o snapshot `pre_restore`
3. repita `PRAGMA integrity_check`
4. so volte a subir o servico depois que o banco estiver integro

## Checklist rapido

- caminho do banco ativo confirmado
- `wal_checkpoint(FULL)` executado antes do backup
- snapshot criado com `sqlite3.backup()`
- `PRAGMA integrity_check = ok`
- rotacao mantida em 7 copias
- restore sempre com writer parado
