# Politica de Transacoes SQLite no EdgeHunter

## Regra de ouro

Nenhuma I/O de rede ou operacao lenta dentro de uma transacao SQLite.

Em pratica:

- dentro da transacao: apenas SQL local e mutacoes em memoria estritamente necessarias
- fora da transacao: Telegram, HTTP, scraping, retries, serializacao pesada, qualquer espera

## Risco que esta politica evita

No benchmark de contencao do projeto, uma transacao que segurou o lock por ~5505ms fez 5 de 6 escritores falharem por timeout com `busy_timeout=5000ms`.

SQLite com WAL continua permitindo apenas um writer por vez. O que protege o projeto nao e o tamanho do banco; e a disciplina de transacao curta.

## Padrao correto

```python
# 1. Persistencia curta e local
pending_alerts = _persist_confirmed_opportunities(opportunities, bankroll_manager)

# 2. I/O de rede fora da transacao
for surebet_id, opp in pending_alerts:
    _enqueue_surebet_alert(app, surebet_id, opp)
```

## Padrao proibido

```python
db.session.add(entity)
send_surebet_alert(opp)  # proibido antes do commit
db.session.commit()
```

## Validacao

- funcoes de transacao curta devem usar `@SHORT_TX(max_duration_ms=100)`
- `python scripts/check_transaction_discipline.py` falha se funcoes `@SHORT_TX` chamarem Telegram ou `requests.post`
- qualquer novo writer deve documentar por que nao aumenta o risco de contencao

## Auditoria inicial

Auditado neste refactor:

- `backend/app/data/scheduler.py::_fetch_odds_task()` -> corrigido
- `backend/app/data/scheduler.py::_check_results_task()` -> escreve no banco, sem Telegram na mesma transacao
- `backend/app/engine/autotuner.py::_log_experiment()` -> escreve no banco, sem I/O de rede na mesma transacao
- `backend/app/models/surebet.py::SurebetStat.update_stats()` -> commit local, sem I/O de rede

Buscas adicionais por `send_message`, `send_surebet_alert` e `requests.post` nao encontraram outro caso equivalente de Telegram dentro da mesma transacao de escrita SQLite principal do scheduler.

Outros caminhos de escrita devem continuar sendo revisados conforme PRD-05 for implementado.
