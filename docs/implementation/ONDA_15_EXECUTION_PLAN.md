# Onda 15 — Integração Real Controlada + Deploy 24/7

## Objetivo

Transformar o EdgeHunter em runtime controlado 24/7 com:

1. Gemini real controlado (por trás de flag explícita).
2. Scraping controlado (por trás de flag explícita).
3. Telegram técnico controlado (por trás de flag explícita).
4. Orquestrador runtime com ciclos seguros.
5. Deploy documentado para servidor 24/7.
6. Teste ponta a ponta com mocks.
7. Encerramento e tag `v2.1-live-controlled-runtime`.

---

## Escopo

| Incluído | Excluído |
|---------|---------|
| Gemini real via flag | Execução financeira automática |
| Scraping controlado via flag | stake / Kelly / bankroll |
| Telegram técnico via flag | AutoEvolution livre |
| Runtime com dry-run padrão | bypass de captcha |
| Deploy com systemd de exemplo | scraping agressivo |
| Teste E2E com mocks | Telegram com comando operacional |
| Tag v2.1-live-controlled-runtime | POST/PUT/PATCH/DELETE operacional |

---

## Guardrails obrigatórios

- `GEMINI_ENABLED=false` por padrão.
- `SCRAPER_ENABLED=false` por padrão.
- `TELEGRAM_ENABLED=false` por padrão.
- `EDGEHUNTER_RUNTIME_ENABLED=false` por padrão.
- `EDGEHUNTER_RUNTIME_DRY_RUN=true` por padrão.
- Toda integração real depende de flag explícita no `.env`.
- Nenhum teste usa rede real.
- Nenhum teste inicia loop infinito.
- Linguagem proibida bloqueia resposta e notificação.
- Fallback offline obrigatório quando flag ausente.

---

## Variáveis de ambiente previstas

```dotenv
# Gemini
GEMINI_ENABLED=false
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TIMEOUT_SECONDS=5
GEMINI_MAX_TOKENS=1024

# Scraper
SCRAPER_ENABLED=false
SCRAPER_SOURCE_URL=
SCRAPER_TIMEOUT_SECONDS=10
SCRAPER_RATE_LIMIT_SECONDS=5
SCRAPER_USER_AGENT=EdgeHunterLocalResearch/1.0

# Telegram
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_TIMEOUT_SECONDS=5

# Runtime
EDGEHUNTER_RUNTIME_ENABLED=false
EDGEHUNTER_RUNTIME_INTERVAL_SECONDS=300
EDGEHUNTER_RUNTIME_MAX_CYCLES=
EDGEHUNTER_RUNTIME_DRY_RUN=true
```

---

## Estratégia — Gemini Real Controlado

- Interface `GeminiClient` com método `validate(prompt) -> dict`.
- Se `GEMINI_ENABLED=false`: retorna `FakeGeminiClient` (fallback offline).
- Se `GEMINI_ENABLED=true` e `GEMINI_API_KEY` ausente: raise `ValueError` controlado.
- Timeout via `GEMINI_TIMEOUT_SECONDS`.
- Limite de tokens via `GEMINI_MAX_TOKENS`.
- Parser seguro existente reutilizado.
- Resposta com linguagem proibida → fallback seguro.
- Nunca retorna payload acionável.
- Registra `provider`, `model`, `tokens_used` no resultado.

---

## Estratégia — Scraping Controlado

- `fetch_source_snapshot(url, config) -> dict` com rate limit e timeout.
- `parse_source_snapshot(raw) -> dict` determinístico.
- `run_scraper_once(config) -> dict` com dry-run e mock.
- Se `SCRAPER_ENABLED=false`: retorna snapshot vazio seguro.
- Rate limit via `SCRAPER_RATE_LIMIT_SECONDS`.
- User-Agent via `SCRAPER_USER_AGENT`.
- Sem bypass, captcha, login ou JavaScript remoto.

---

## Estratégia — Telegram Técnico Controlado

- `build_telegram_message(event_type, data) -> str`.
- `send_telegram_message(token, chat_id, text, config) -> dict` com mock.
- `notify_runtime_status(...)` e `notify_signal_summary(...)`.
- Se `TELEGRAM_ENABLED=false`: log local, sem envio.
- Token/chat_id ausentes → falha controlada.
- Mensagens com linguagem proibida → bloqueio antes do envio.

---

## Estratégia — Runtime / Orquestrador

- Ciclo: validar ambiente → scraper → dados → classificação → Gemini → resumo → Telegram → logs.
- `EDGEHUNTER_RUNTIME_DRY_RUN=true` por padrão.
- `max_cycles` encerra o loop após N iterações.
- Erro por etapa não derruba o runtime (tratamento individual).
- Shutdown limpo via `KeyboardInterrupt`.
- Nenhuma ação financeira, nenhuma autoaplicação de threshold.

---

## Estratégia — Deploy Servidor 24/7

- `deploy/systemd/edgehunter.service.example`: arquivo de exemplo sem segredos.
- `deploy/README_SERVER.md`: guia completo de configuração.
- `scripts/run_runtime.py`: ponto de entrada do runtime.
- Runtime desabilitado por padrão, requer flag explícita.

---

## Estratégia — Teste Ponta a Ponta

- `tests/integration/test_live_controlled_runtime.py` com mocks completos.
- Valida ciclo completo: API → scraper → Gemini fallback → Telegram mock → runtime 1 ciclo.
- Sem rede real, sem execução financeira, sem AutoEvolution.

---

## Lista de Stories

| Story | Objetivo | Commit |
|-------|---------|--------|
| STORY-15-001 | Plano formal da Onda 15 | `docs(implementation): planejar Onda 15 runtime controlado` |
| STORY-15-002 | Gemini real controlado | `feat(integrations): adicionar Gemini real controlado` |
| STORY-15-003 | Scraping controlado | `feat(integrations): adicionar scraping controlado` |
| STORY-15-004 | Telegram técnico controlado | `feat(integrations): adicionar Telegram tecnico controlado` |
| STORY-15-005 | Orquestrador 24/7 | `feat(runtime): adicionar orquestrador controlado` |
| STORY-15-006 | Deploy servidor 24/7 | `feat(deploy): adicionar deploy servidor 24x7 controlado` |
| STORY-15-007 | Teste ponta a ponta | `test(runtime): adicionar teste ponta a ponta controlado` |
| STORY-15-008 | Encerramento e tag | `docs(implementation): registrar encerramento da Onda 15` |

---

## Política de commit

- Commitar apenas com suíte global verde.
- Working tree limpa antes de avançar.
- `git diff --check` sem erros de whitespace.
- `check_doc_consistency.py` com 0 erros.
- `check_transaction_discipline.py` aprovado.

---

## Tag alvo

```
v2.1-live-controlled-runtime
```

Criar apenas na STORY-15-008, após todos os gates passarem.
