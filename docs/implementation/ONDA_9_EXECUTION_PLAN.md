# Plano de Execução — Onda 9 EdgeHunter

## 1. Veredicto da Onda 9

* [x] APROVADA PARA INICIAR
* [ ] APROVADA COM RESSALVAS
* [ ] NÃO APROVADA

A Onda 9 pode iniciar a partir do checkpoint `v1.1-onda8-outcome-feedback-loop`. A rota escolhida é dashboard read-only com hardening leve de schema porque ela aumenta observabilidade sem ampliar risco operacional, sem integrar rede externa e sem alterar automaticamente thresholds.

## 2. Objetivo Técnico

Criar uma camada read-only de observabilidade analítica para consolidar:

* classificações `GREEN_SIM` e `RED_SIM`;
* outcomes simulados observados;
* métricas de confirmação, não confirmação e rejeição técnica;
* snapshot de calibração;
* snapshot de sugestão técnica de threshold;
* status de integridade do schema;
* readiness do sistema analítico.

## 3. Escopo Permitido

* Contratos puros para dashboard read-only.
* Agregador puro de dashboard summary.
* Endpoints `GET` protegidos por API key.
* Introspecção read-only de schema.
* Testes unitários, API e adversariais.
* Relatório oficial de encerramento da Onda 9.

## 4. Escopo Proibido

Não implementar:

* ação financeira real;
* execução financeira;
* cálculo financeiro operacional;
* Telegram operacional;
* scheduler operacional;
* AutoEvolution;
* alerta acionável;
* integração com casa externa;
* comando operacional;
* chamada real ao Gemini;
* dependência Google/Gemini;
* rede externa;
* `POST`, `PUT`, `PATCH` ou `DELETE` operacional;
* alteração automática de threshold;
* auto-apply de sugestão;
* qualquer ação financeira.

## 5. Stories Propostas

| Ordem | Story | Objetivo | Commit esperado |
| ----: | ----- | -------- | --------------- |
| 1 | STORY-09-001 | Plano formal da Onda 9 | `docs(implementation): planejar Onda 9 dashboard readonly` |
| 2 | STORY-09-002 | Contratos de Dashboard Read-only | `feat(dashboard): definir contratos readonly` |
| 3 | STORY-09-003 | Agregador de Dashboard Summary | `feat(dashboard): gerar resumo readonly` |
| 4 | STORY-09-004 | API Read-only do Dashboard | `feat(api): expor dashboard readonly` |
| 5 | STORY-09-005 | Hardening Leve de Schema/Migrações | `feat(database): adicionar introspeccao leve de schema` |
| 6 | STORY-09-006 | Testes Adversariais do Dashboard | `test(api): adicionar testes adversariais do dashboard` |
| 7 | STORY-09-007 | Encerramento da Onda 9 | `docs(implementation): registrar encerramento da Onda 9` |

## 6. Estratégia de Testes

* Testes unitários para contratos puros e agregador.
* Testes de API para autenticação, envelope seguro, filtros e read-only.
* Testes adversariais para payloads corrompidos, linguagem proibida e ausência de escrita.
* Testes de banco para introspecção read-only de schema.
* Suíte global `python -m pytest` ao fim de cada story com código.
* Gates globais ao fim de cada story:
  * `python scripts/check_doc_consistency.py`
  * `python scripts/check_transaction_discipline.py`
  * `git diff --check`

## 7. Guardrails

Toda entrega da Onda 9 deve preservar:

* `is_simulated=True`;
* `paper_trading=True`;
* `learning_mode=True`;
* `actionable=False`;
* `bet_placed=False`;
* `alerted=False`;
* `not_operational_advice=True`;
* `auto_apply=False` quando houver sugestão técnica de threshold.

Nenhum endpoint pode escrever dados, criar outcome, criar classificação, alterar threshold ou disparar integração externa.

## 8. Endpoints Previstos

* `GET /api/dashboard/summary`
* `GET /api/calibration/summary`

Ambos devem:

* exigir `X-API-Key`;
* retornar resposta envelopada por `build_safe_api_response()`;
* expor somente dados técnicos simulados;
* preservar flags globais seguras.

## 9. Hardening de Migrações

A Onda 9 não substitui `ensure_schema()` e não cria framework completo de migração. O hardening previsto é uma camada leve de introspecção read-only para:

* listar tabelas existentes;
* listar colunas de tabela;
* validar tabelas e colunas esperadas;
* reportar ausências sem alterar o banco;
* apoiar decisão futura sobre migrações versionadas.

## 10. Riscos e Dívidas

### Riscos

* Dashboard pode mascarar dados incompletos se não separar ausência de outcome de `UNRESOLVED`.
* API pode deixar de ser read-only se reutilizar helpers de persistência no endpoint.
* Introspecção de schema pode virar migração implícita se chamar `ensure_schema()` durante validação.
* Linguagem operacional pode vazar em payload público se rationale ou docs de API forem reaproveitados sem filtro.

### Dívidas aceitas

* Migrações versionadas continuam fora de escopo.
* Dashboard visual de frontend não entra nesta onda; a entrega é API/read models.
* Gemini real continua fora de escopo.
* Coleta automática de outcomes continua fora de escopo.

## 11. Critérios de Encerramento

A Onda 9 só pode ser encerrada quando:

* todas as 7 stories estiverem commitadas em escopo separado;
* `python -m pytest` passar;
* `python scripts/check_doc_consistency.py` passar;
* `python scripts/check_transaction_discipline.py` passar;
* `git diff --check` passar;
* o relatório `docs/implementation/ONDA_9_CLOSURE_REPORT.md` estiver criado;
* não houver violação de guardrails;
* a tag for criada somente após confirmação de gates verdes.

## 12. Tag Alvo

Tag alvo ao final da onda:

```text
v1.2-onda9-dashboard-readonly
```
