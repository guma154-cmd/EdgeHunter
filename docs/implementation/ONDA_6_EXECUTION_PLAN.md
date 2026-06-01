# Plano de Execução — Onda 6 EdgeHunter

## 1. Veredicto

* [ ] APROVADO PARA COMEÇAR ONDA 6
* [x] APROVADO COM RESSALVAS
* [ ] NÃO APROVADO

A Onda 6 pode começar se o escopo for explicitamente redefinido como **GeminiValidator Seguro / Validação IA Não Operacional**. A implementação deve começar por contrato, prompt minimizado, parser, cliente fake/offline e persistência auditável de relatório técnico. Chamada real ao Gemini, Telegram, scheduler, stake, Kelly, bankroll e qualquer recomendação operacional ficam fora desta onda inicial.

## 2. Objetivo da Onda 6

Criar uma camada de validação por IA que funcione como **revisor técnico simulado** das oportunidades já produzidas pelo ValueDetector, sem alterar decisão, execução, alerta ou sizing. O resultado esperado é um registro auditável e consultável de análise qualitativa, com confiança técnica, fatores de risco e justificativa curta, sempre marcado como simulado, paper trading e não acionável.

A onda deve preservar as garantias conquistadas nas Ondas 3, 4A, 4B e 5:

- ValueDetector permanece determinístico, local e não operacional.
- Backtest e relatórios continuam paper trading e sem recomendação de aposta real.
- API continua somente leitura, protegida por `X-API-Key` e sem campos financeiros.
- Qualquer IA falha fechado: se parser, cliente ou resposta falhar, o sistema retorna validação indisponível/rejeitada tecnicamente, sem derrubar o fluxo principal.

## 3. Decisão de rota

Rota recomendada: **implementar GeminiValidator seguro e offline antes de qualquer chamada externa real**. A persistência formal de backtests continua como dívida média, mas não bloqueia o contrato seguro da IA porque a Onda 6 pode consumir detecções existentes e produzir relatórios próprios.

| # | Pergunta obrigatória | Decisão |
|---|---|---|
| 1 | GeminiValidator agora ou persistência formal de backtests primeiro? | Começar GeminiValidator agora, mas apenas como contrato seguro, fake client e relatório local. Persistência formal de backtests segue dívida média separada. |
| 2 | Consumir API segura ou SQLite direto? | Consumidores devem usar a API segura. O backend pode usar repositórios internos explícitos para persistir/ler relatórios IA, mas a lógica do validator não deve fazer queries SQLite soltas. |
| 3 | O que a IA pode receber? | Contexto mínimo: `opportunity_id`, `match_id` opaco, liga, mercado, seleção, odds oferecida, probabilidade técnica, EV, edge, fonte, método de detecção, idade do snapshot, métricas agregadas recentes e flags de simulação. |
| 4 | O que a IA nunca pode receber? | Bankroll, stake, Kelly, valor monetário, credenciais, API keys, tokens Telegram, dados pessoais, instruções de execução, links de aposta, estado financeiro real e comandos operacionais. |
| 5 | Score/confidence é permitido? | Sim, como confiança técnica `0.0..1.0`, calibrada e não operacional. Não pode significar autorização de aposta. |
| 6 | Texto explicativo é permitido? | Sim, curto e técnico, sem linguagem de aconselhamento financeiro ou imperativo operacional. |
| 7 | A IA pode reprovar uma oportunidade? | Sim. `technical_verdict="reject"` é permitido e desejável como revisão defensiva. |
| 8 | A IA pode aprovar uma oportunidade? | Não no sentido operacional. Usar `technical_verdict="pass"` ou `"review"` apenas como avaliação técnica, sempre com `actionable=false`. |
| 9 | Como impedir conselho de aposta? | Prompt de sistema, schema sem campos operacionais, parser/sanitizer, lista de frases proibidas, testes adversariais e wrapper de resposta com disclaimer. |
| 10 | Como garantir ausência de Kelly/stake/bankroll? | Não incluir esses campos em input, output, schema, prompt, persistência ou API. Adicionar testes de inspeção de fonte e payload. |
| 11 | Deve persistir resultado de validação? | Sim. Criar relatório local auditável, idempotente por oportunidade/modelo/prompt hash, com raw response redigida ou opcionalmente ausente. |
| 12 | Offline, síncrono ou assíncrono? | Offline e síncrono primeiro. Assíncrono e provedor real ficam para uma etapa futura após auditoria. |
| 13 | Deve chamar Gemini real nesta Onda 6? | Não na primeira sequência. A chamada real só pode entrar depois de cliente fake, parser, persistência e testes adversariais estarem fechados. |
| 14 | Como testar sem rede? | Fake client determinístico, fixtures de resposta, monkeypatch contra rede/imports externos e testes que falham se houver chamada HTTP real. |
| 15 | Quais stories compõem a onda? | Sete stories: contrato, prompt seguro, parser/sanitizer, cliente fake, persistência, API read-only de validações e auditoria de prontidão para Gemini real. |

## 4. Escopo permitido

- Criar módulo local `GeminiValidator` ou equivalente com tipos puros.
- Criar contrato de entrada sanitizada para oportunidades de value detection.
- Criar contrato de saída com veredicto técnico, confiança, fatores de risco e rationale.
- Criar prompt builder determinístico, minimizado e explicitamente não operacional.
- Criar parser robusto para JSON ou blocos JSON em texto.
- Criar fake client determinístico para testes e fluxo offline.
- Persistir relatório técnico simulado em SQLite.
- Expor consulta read-only via API segura depois da persistência local.
- Criar testes unitários, adversariais, de API e de inspeção estática.

## 5. Escopo proibido

- Não adicionar chamada real ao Gemini como primeiro passo.
- Não adicionar dependência Google/Gemini em `pyproject.toml` sem uma story e gate próprios.
- Não implementar Telegram, scheduler, alertas, comandos, callbacks ou notificações.
- Não implementar stake, Kelly, bankroll, bet amount, wager, placed bets ou tracking financeiro.
- Não gerar frases como "apostar", "entrar", "colocar aposta", "recomendado apostar" ou equivalentes.
- Não alterar o ValueDetector para depender da IA.
- Não transformar a validação IA em fonte primária de verdade.
- Não criar endpoint mutável ou operacional.

## 6. Contrato de segurança da IA

### Entrada sanitizada

O input deve ser uma estrutura própria, por exemplo `SafeAIValidationInput`, construída a partir de uma oportunidade já segura:

- `opportunity_id`
- `match_id`
- `league`
- `market`
- `selection`
- `true_probability`
- `offered_odds`
- `expected_value`
- `edge_percentage`
- `source`
- `detection_method`
- `snapshot_age_seconds`
- `recent_hit_rate`
- `recent_false_positive_rate`
- `is_simulated=true`
- `paper_trading=true`
- `actionable=false`

Campos ausentes devem falhar claramente ou ser tratados como contexto desconhecido. A estrutura não deve aceitar campos extras.

### Saída técnica

O output deve ser uma estrutura própria, por exemplo `SafeAIValidationResult`:

- `validation_id`
- `opportunity_id`
- `technical_verdict`: `pass`, `review`, `reject`, `invalid_response`, `unavailable`
- `confidence`: número entre `0.0` e `1.0`
- `risk_factors`: lista curta de fatores técnicos
- `rationale`: texto curto e sanitizado
- `parser_status`: `parsed`, `recovered`, `failed`
- `provider`: `fake` inicialmente
- `model_name`: `fake-gemini-validator-v1` inicialmente
- `prompt_hash`
- `tokens_used=0` no fake client
- `is_simulated=true`
- `paper_trading=true`
- `actionable=false`
- `bet_placed=false`
- `alerted=false`
- `not_operational_advice=true`

Os nomes `recommendation` e `stake_adjustment` do PRD-04 original não devem ser usados nesta onda porque conflitam com o modo não operacional.

## 7. Integração com API e persistência

A API segura da Onda 5 é o limite externo correto. Para clientes e futuras telas, o fluxo deve ser:

1. Consultar oportunidades por `/api/value-detections`.
2. Validar tecnicamente uma oportunidade em fluxo local/offline controlado.
3. Persistir o relatório IA simulado.
4. Consultar relatórios por endpoint read-only protegido, quando a story de API for executada.

Persistência recomendada:

- Tabela `gemini_validation_reports` ou nome equivalente.
- Chave de idempotência por `opportunity_id`, `provider`, `model_name` e `prompt_hash`.
- Campos de segurança espelhando o contrato: `is_simulated`, `paper_trading`, `actionable`, `bet_placed`, `alerted`.
- Campos técnicos: `technical_verdict`, `confidence`, `risk_factors_json`, `rationale`, `parser_status`, `prompt_hash`, `tokens_used`, `created_at`.
- `response_raw` deve ser opcional e, se existir, deve passar por sanitização/redação.

A persistência formal de `/api/backtests` continua fora deste escopo. O endpoint atual retorna lista vazia e isso deve ser mantido como dívida média, não misturado com a primeira fatia do GeminiValidator.

## 8. Stories propostas

| Ordem | Story | Nome | Escopo |
|---|---|---|---|
| 1 | **STORY-06-001** | Contrato seguro do GeminiValidator | Criar dataclasses/tipos de input e output, validações de flags, enums técnicos e testes de contrato. Sem rede. |
| 2 | **STORY-06-002** | Prompt builder minimizado e não operacional | Gerar prompt determinístico a partir do input sanitizado, com lista de campos permitidos e linguagem proibida. |
| 3 | **STORY-06-003** | Parser e sanitizer de resposta IA | Extrair JSON, validar schema, normalizar falhas e bloquear termos operacionais. |
| 4 | **STORY-06-004** | Cliente fake e fluxo offline | Implementar interface de cliente IA com fake determinístico e `validate_opportunity` local. |
| 5 | **STORY-06-005** | Persistência de relatórios IA simulados | Criar schema/repositório para relatórios de validação, idempotente e com flags de segurança. |
| 6 | **STORY-06-006** | Consulta segura de validações IA | Expor endpoint read-only protegido para relatórios IA, sem campos operacionais e com paginação. |
| 7 | **STORY-06-007** | Auditoria de prontidão para Gemini real | Rodar adversariais, checar ausência de rede por padrão e decidir se uma onda futura pode ativar provedor real. |

## 9. Estratégia de testes

- Testes de contrato para input/output, enums e flags obrigatórias.
- Testes de prompt para garantir minimização e ausência de campos proibidos.
- Testes de parser com JSON puro, markdown fenced JSON, JSON malformado recuperável e resposta irrecuperável.
- Testes adversariais de prompt injection tentando forçar recomendação operacional.
- Testes de fake client sem rede e com saída determinística.
- Testes de persistência com SQLite temporário, idempotência e rejeição de payload inseguro.
- Testes de API com autenticação `X-API-Key`, paginação e OpenAPI sem linguagem proibida.
- Inspeção estática para impedir imports/chamadas de rede no fluxo default da onda.

Suites focadas esperadas por story:

- `tests/unit/core/test_gemini_validator_contract.py`
- `tests/unit/core/test_gemini_validator_prompt.py`
- `tests/unit/core/test_gemini_validator_parser.py`
- `tests/unit/core/test_gemini_validator_fake_client.py`
- `tests/unit/core/test_gemini_validator_persistence.py`
- `tests/unit/api/test_api_gemini_validations.py`
- `tests/unit/core/test_gemini_validator_adversarial.py`

Gates de fechamento da onda:

- `python -m pytest`
- `python scripts/check_doc_consistency.py`
- `python scripts/check_transaction_discipline.py`
- `git diff --check`

## 10. Dívidas ou bloqueios

### Críticos

- O PRD-04 original contém campos e exemplos operacionais (`recommendation`, `stake_adjustment`, Telegram, budget real e chamada real à API). A Onda 6 só é segura se esses itens forem explicitamente excluídos ou adaptados no código.
- Não existe módulo GeminiValidator implementado. A primeira story deve ser contrato e testes, não integração externa.
- Não existe schema para relatórios IA. Persistência precisa ser criada antes de endpoint público.

### Médios

- `/api/backtests` ainda retorna lista vazia; a persistência formal de relatórios de backtest segue dívida média.
- `pyproject.toml` não tem dependência do cliente Google/Gemini; isso é correto para a fase fake/offline, mas deve ser registrado se uma onda futura habilitar provedor real.
- PRD-05 permanece altamente operacional e deve continuar bloqueado até uma decisão explícita de produto.

### Baixos

- A versão da API ainda está em `0.7.0`; atualizar versão pode ser feito em story própria se o projeto passar a tratar versionamento semântico formal.
- Os documentos PRD-04/PRD-05 mantêm linguagem histórica operacional; o plano da Onda 6 deve prevalecer como guardrail de implementação.

## 11. Primeiro prompt recomendado

```text
# Tarefa: Implementar STORY-06-001 — Contrato seguro do GeminiValidator

## Contexto
Estamos iniciando a Onda 6 do EdgeHunter: GeminiValidator Seguro / Validação IA Não Operacional.
Leia primeiro:
- docs/implementation/ONDA_6_EXECUTION_PLAN.md
- docs/implementation/ONDA_5_CLOSURE_REPORT.md
- docs/prd/04_gemini_validator.md
- docs/prd/05_auto_evolution.md
- src/edgehunter/core/value_detector.py
- src/edgehunter/api/contracts.py

## Objetivo
Criar apenas contratos/tipos puros para entrada e saída do GeminiValidator seguro.
Não chamar Gemini real.
Não adicionar dependência externa.
Não criar Telegram, scheduler, stake, Kelly, bankroll, alerta ou recomendação operacional.

## Escopo esperado
- Criar módulo em src/edgehunter/core/ para contratos seguros do GeminiValidator.
- Criar input sanitizado para oportunidade técnica.
- Criar output com technical_verdict, confidence, risk_factors, rationale e flags de segurança.
- Rejeitar campos extras e flags inseguras.
- Garantir actionable=false, bet_placed=false, alerted=false, is_simulated=true e paper_trading=true.

## Testes obrigatórios
- tests/unit/core/test_gemini_validator_contract.py
- Testar input válido.
- Testar rejeição de flags inseguras.
- Testar rejeição de campos proibidos.
- Testar confidence fora de 0..1.
- Testar que não há termos de stake, Kelly, bankroll ou recomendação operacional no contrato.

## Validação obrigatória
python -m pytest tests/unit/core/test_gemini_validator_contract.py
python scripts/check_doc_consistency.py
python scripts/check_transaction_discipline.py
git diff --check

## Output
Relate arquivos alterados, testes executados com exit code e confirme explicitamente que não houve chamada real a Gemini nem criação de funcionalidade operacional.
```

## 12. Decisão para Rafael

Recomendação: iniciar a Onda 6 pela **STORY-06-001 — Contrato seguro do GeminiValidator**.

Justificativa técnica: a Onda 5 entregou a base pública segura e read-only, mas o PRD-04 ainda carrega intenção operacional histórica. A forma mais segura de avançar é transformar o GeminiValidator em uma camada técnica, auditável e offline primeiro. Isso permite ganhar parser, prompt, persistência e testes adversariais sem abrir superfície de rede, custo, Telegram, stake ou recomendação real.

Condição de aceite da Onda 6: ao final, o EdgeHunter deve conseguir registrar e consultar validações IA simuladas, com evidência testável de que elas não executam, não recomendam e não dimensionam apostas.
