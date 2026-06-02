# Teste Ponta a Ponta Controlado — EdgeHunter

## Objetivo

Validar o ciclo completo do EdgeHunter em ambiente local controlado, com
todas as integrações externas substituídas por mocks. Sem rede real, sem
execução financeira, sem AutoEvolution.

## Arquivo de teste

`tests/integration/test_live_controlled_runtime.py`

## Cenários cobertos

| # | Cenário | Resultado esperado |
|---|---------|-------------------|
| 1 | Config carrega corretamente | `enabled=true`, `max_cycles=1` |
| 2 | API sobe via TestClient | `GET /health` retorna 200 |
| 3 | Scraper mock sem rede real | Nenhuma conexão socket aberta |
| 4 | Gemini desabilitado usa fallback | `fallback_reason=gemini_disabled` |
| 5 | Telegram mock recebe mensagem | `sent=true`, conteúdo técnico |
| 6 | Runtime executa 1 ciclo completo | `cycles_executed=1`, `actionable=false` |
| 7 | API readiness responde sem crash | Status 200, 401 ou 403 |
| 8 | Sem rede real no E2E completo | Nenhuma conexão socket aberta |
| 9 | Sem execução financeira | Todos os ciclos com `actionable=false` |
| 10 | Sem AutoEvolution | Termo ausente no código |

## Guardrails verificados

- `actionable=false` em todos os resultados
- `not_operational_advice=true` em todos os resultados
- `is_simulated=true` em todos os resultados
- Nenhuma conexão socket real durante o E2E
- Nenhum termo proibido no código verificado

## Como rodar

```bash
python -m pytest tests/integration/test_live_controlled_runtime.py -v
```

## Resultado esperado

```
10 passed in X.XXs
```

## Notas

- O teste usa `EDGEHUNTER_RUNTIME_DRY_RUN=false` com scraper mock injetado
  para exercitar todos os passos do ciclo sem rede real.
- O Gemini permanece desabilitado (`GEMINI_ENABLED=false`), garantindo fallback.
- O Telegram usa `_mock_send` para capturar mensagens sem envio real.
