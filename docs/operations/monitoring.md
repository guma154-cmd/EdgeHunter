# Monitoramento Operacional Minimo

## Objetivo

Este runbook cobre a observabilidade minima necessaria para operar o EdgeHunter em producao com o stack real atual.

## Escopo real atual

Hoje o repositorio mistura dois estilos de logging:

- runtime principal: `logging` da biblioteca padrao Python, emitido para `stdout`
- scripts de schema e inicializacao SQLite em `src/edgehunter/database/*.py` e `scripts/init_db.py`: `loguru`

Nao existe configuracao de arquivo de log com rotacao dentro do runtime principal do backend.

Em producao com Docker Compose, a fonte primaria de logs e o container `edgehunter-backend`.

## Onde ficam os logs

### Backend em Docker Compose

Ver logs ao vivo:

```bash
cd /home/telematica/EdgeHunter
docker compose logs -f backend
```

Ultimas 200 linhas:

```bash
cd /home/telematica/EdgeHunter
docker compose logs --tail=200 backend
```

### Formato atual do log do runtime

Configurado em `backend/run.py`:

```text
[YYYY-MM-DD HH:MM:SS,mmm] logger_name — LEVEL: mensagem
```

Exemplo esperado:

```text
[2026-05-22 03:00:01,234] root — INFO: [OK] Scheduler: 7 jobs ativos
```

### Rotacao atual

- runtime principal: nenhuma rotacao definida no codigo
- retencao e rotacao ficam a cargo do Docker daemon ou da plataforma de execucao
- `loguru` existe apenas em scripts pontuais de banco, nao no loop principal do backend

Implicacao operacional:

- nao procure arquivos `app.log` ou equivalente no repositorio
- se precisar retencao por arquivo, isso deve ser configurado fora do app

## Como verificar se o sistema esta ativo

## Metodo 1: health HTTP

```bash
curl -fsS http://127.0.0.1:5000/api/health
```

Esperado:

```json
{"status":"ok","version":"1.0.0"}
```

## Metodo 2: status do container

```bash
cd /home/telematica/EdgeHunter
docker compose ps
```

Esperado:

- container `edgehunter-backend` em `Up`
- healthcheck `healthy` quando a imagem suportar o comando de health

## Metodo 3: heartbeat Telegram

O scheduler envia heartbeat a cada 2 horas. Mensagens de heartbeat confirmam:

- scheduler ativo
- IA ativa ou inativa
- surebets do dia
- status de banca por casa

Se o heartbeat desaparecer, trate como sinal de degradacao.

## Comando Telegram `/status`

O PRD-05 especifica um comando `/status`, mas ele nao esta implementado no runtime atual do repositorio.

Operacao hoje:

- nao dependa de `/status` como checagem real
- use `curl /api/health`, `docker compose ps`, logs e heartbeat Telegram

Quando esse comando existir, ele podera virar a checagem manual primaria.

## Alertas Telegram implementados hoje

Os alertas abaixo existem no codigo atual:

- startup do sistema: `EdgeHunter iniciado no servidor Ubuntu 24/7`
- heartbeat a cada 2 horas
- resumo diario
- alerta de surebet enviada
- banca baixa por casa (`BankrollManager`)
- aviso de quota em `RapidAPI`
- aviso de quota em `API-Football`
- concept drift detectado
- promocao de novo modelo
- ciclo do `AutoTuner`

## Alertas que estao no PRD mas nao no runtime atual

Nao trate como implementados ainda:

- Circuit Breaker
- bankroll floor com pausa automatica
- comando `/status`
- alerta formal de falha de backup
- alerta formal de `scraper_health = critical`

Se um incidente depender desses itens, a resposta operacional hoje precisa usar logs e consultas manuais.

## Health check de scraper

## Estado atual

O schema SQLite ja possui a tabela `scraper_health`:

- `scraper_name`
- `check_time`
- `status`
- `consecutive_failures`
- `odds_stale`
- `divergence_detected`
- `error_message`

Mas o scheduler atual nao persiste verificacoes periodicas nessa tabela.

Portanto:

- a tabela existe
- o monitoramento automatico de scrapers ainda nao esta ligado no runtime atual

## Consulta manual

Descubra o banco ativo primeiro. Depois:

```bash
export DB_PATH="/home/telematica/EdgeHunter/database/edgehunter.db"
python - <<'PY'
import os
import sqlite3

conn = sqlite3.connect(os.environ["DB_PATH"])
rows = conn.execute("""
SELECT scraper_name, check_time, status, consecutive_failures, odds_stale,
       divergence_detected, COALESCE(error_message, '')
FROM scraper_health
ORDER BY check_time DESC
LIMIT 20
""").fetchall()

for row in rows:
    print(row)

conn.close()
PY
```

Se nao houver linhas, isso significa ausencia de coleta de health persistida, nao necessariamente saude boa.

## Metricas minimas

## 1. ROI 7d e 30d

Fonte operacional preferida:

- API: `/api/bets/stats?days=7`
- API: `/api/bets/stats?days=30`

Exemplos:

```bash
curl -fsS "http://127.0.0.1:5000/api/bets/stats?days=7"
curl -fsS "http://127.0.0.1:5000/api/bets/stats?days=30"
```

Campos-chave:

- `settled`
- `wins`
- `losses`
- `total_profit`
- `roi_total`
- `avg_edge`

## 2. Taxa de deteccao

O runtime atual nao persiste um denominador completo de "jogos analisados por ciclo". Portanto, use o proxy abaixo:

- oportunidades geradas por periodo
- percentual dessas oportunidades com alerta efetivamente enviado

Consulta SQL:

```bash
export DB_PATH="/home/telematica/EdgeHunter/database/edgehunter.db"
python - <<'PY'
import os
import sqlite3

conn = sqlite3.connect(os.environ["DB_PATH"])
for days in (7, 30):
    row = conn.execute(f"""
    SELECT
        COUNT(*) AS total_surebets,
        SUM(CASE WHEN alert_sent = 1 THEN 1 ELSE 0 END) AS alertadas
    FROM surebets
    WHERE created_at >= datetime('now', '-{days} days')
    """).fetchone()
    total = row[0] or 0
    sent = row[1] or 0
    rate = (sent / total * 100.0) if total else 0.0
    print({"days": days, "total_surebets": total, "alert_sent": sent, "delivery_rate_pct": round(rate, 2)})

conn.close()
PY
```

Interpretacao:

- `total_surebets` baixo pode ser mercado ruim ou falha silenciosa de scraping
- `delivery_rate_pct < 100` aponta falha entre deteccao e envio Telegram

## 3. Uptime

Como o app nao persiste uptime em tabela propria, use o processo/container.

```bash
cd /home/telematica/EdgeHunter
docker compose ps
docker inspect --format='{{.State.Status}} {{.State.StartedAt}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' edgehunter-backend
```

Verifique:

- status `running`
- data de inicio coerente com o ultimo deploy conhecido
- health `healthy`, se presente

## Sinais de sistema saudavel

- `GET /api/health` responde `200`
- container `backend` permanece `Up`
- heartbeat Telegram continua chegando
- logs mostram ciclos `[Odds]`, `[Results]`, `[Metrics]`, `[AutoTuner]` sem erro repetitivo
- ROI 7d/30d responde via API
- nao ha repeticao de `database is locked`

## Sinais de degradacao

- `docker compose ps` mostra restart loop
- `curl /api/health` falha
- heartbeat some por mais de 2 horas
- logs mostram falhas repetidas nas fontes de odds
- `delivery_rate_pct` cai
- quota de API chega aos avisos de 80 ou bloqueios de 95

## Consultas uteis de triagem

### Erros recentes do backend

```bash
cd /home/telematica/EdgeHunter
docker compose logs --tail=300 backend | grep -E "ERROR|FALHOU|Traceback|database is locked"
```

### Ultimas surebets

```bash
export DB_PATH="/home/telematica/EdgeHunter/database/edgehunter.db"
python - <<'PY'
import os
import sqlite3

conn = sqlite3.connect(os.environ["DB_PATH"])
rows = conn.execute("""
SELECT id, bookmaker_A, bookmaker_B, profit_pct, alert_sent, status, created_at
FROM surebets
ORDER BY created_at DESC
LIMIT 20
""").fetchall()
for row in rows:
    print(row)
conn.close()
PY
```

### Ultimas apostas liquidadas

```bash
curl -fsS "http://127.0.0.1:5000/api/bets?result=won&days=30&limit=20"
curl -fsS "http://127.0.0.1:5000/api/bets?result=lost&days=30&limit=20"
```

## Disciplina de transacao

Ao investigar incidentes de contencao SQLite, siga obrigatoriamente a politica em:

- `docs/architecture/transaction-discipline.md`

Regra operacional:

- nunca introduza Telegram, HTTP, scraping ou qualquer I/O lenta dentro de transacoes SQLite
- se aparecer `database is locked`, valide primeiro se algum caminho novo violou a disciplina de transacao curta

## Checklist rapido

- `curl /api/health` responde
- `docker compose ps` mostra `backend` ativo
- heartbeat Telegram recente
- ROI 7d e 30d consultaveis
- logs sem loop de erro
- nenhuma confusao entre item implementado e item apenas previsto em PRD
