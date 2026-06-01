# Plano de Execução — Onda 5 EdgeHunter

## 1. Veredicto

* [x] APROVADO PARA COMEÇAR ONDA 5
* [ ] APROVADO COM RESSALVAS
* [ ] NÃO APROVADO

## 2. Objetivo da Onda 5

Estabelecer a **API Segura / Exposição Controlada** do EdgeHunter. O objetivo técnico é criar uma camada de serviço (REST) *somente leitura*, protegida por autenticação, que exponha os resultados do ValueDetector e do ambiente de Backtest de maneira controlada, explícita e estruturada. Essa API servirá como fundação para a futura integração do GeminiValidator, garantindo previamente paginação eficiente, tipagem de contratos (OpenAPI) e injeção forçada de metadados de simulação para erradicar qualquer viés de recomendação operacional real.

## 3. Decisão de rota

A recomendação (confirmada pelo relatório da Onda 4B) é priorizar a **API Segura** antes do GeminiValidator.
- **API Segura**: Constrói um funil de exposição estruturado, onde os dados chegam à IA ou a dashboards com contratos bem definidos e bloqueios sistêmicos contra linguagem de *sizing* financeira.
- **GeminiValidator**: Adiado para a Onda 6. Alimentá-lo diretamente com scripts soltos sem uma API paginada e segura seria pular uma etapa arquitetural, elevando risco e custo.
- **Nova onda de hardening / Observabilidade**: O sistema já teve hardening (Onda 4B). Observabilidade (logs produtivos) deve nascer nativamente com a própria API Segura.

## 4. Endpoints avaliados

| Endpoint | Decisão | Motivo | Risco |
| -------- | ------- | ------ | ----- |
| `GET /api/value-detections` | **Necessário agora** | O Gemini e outras UIs precisarão consultar janelas de detecções. | Exigirá paginação rígida para evitar DdoS no banco. |
| `GET /api/value-detections/{id}` | **Necessário agora** | Consulta de drill-down de uma oportunidade específica e rastreabilidade. | Baixo (lookup no banco por ID). |
| `GET /api/backtests` | **Necessário agora** | Consultar sumário histórico de métricas (reports). | Risco de payload massivo sem limite de tempo. |
| `GET /api/backtests/{run_id}` | **Adiar** | Um endpoint geral com paginação de backtests históricos serve por enquanto. Drill-down pode atrasar a entrega principal. | Baixo. |
| `GET /api/health` | **Necessário agora** | Essencial para docker, monitoramento e prontidão da aplicação. | Nenhum. |
| `GET /api/readiness` | **Rejeitar** | Para este estágio, um `/health` abrangente é suficiente. | Overhead excessivo em uma API recém-nascida. |

## 5. Contrato de segurança da API

Toda resposta estruturada ou *wrapper* principal da API REST deve **obrigatoriamente** assinar os seguintes campos booleanos:

* **Campos Obrigatórios (Flags)**:
  - `is_simulated`: `true`
  - `paper_trading`: `true`
  - `actionable`: `false`
  - `bet_placed`: `false`
  - `alerted`: `false`
  - `not_operational_advice`: `true`

* **Campos Proibidos** (nunca devem constar no DTO de reposta):
  - `stake`
  - `kelly` / `kelly_criterion`
  - `bankroll`
  - `entrada` (valor monetário)

* **Linguagem Proibida**: A API não pode veicular nomes de chaves que induzam à operação, como `should_bet`, `execute_trade`, `signal`, ou `action`.

## 6. Auth/Authz

A API não pode ser exposta ao público geral sem autenticação.
**Estratégia Mínima Recomendada**: Autenticação via Chave Simples (Header `X-API-Key` ou Bearer Token estático validado por variável de ambiente). Como não há conceito nativo de multi-tenant ou papéis granulares de usuário nesta fase, o sistema só precisa barrar acesso anônimo externo para proteger as rotas de serem chamadas excessivamente (mesmo que *read-only*).

## 7. Stories propostas

| Ordem | Story | Objetivo | Observação |
| ----: | ----- | -------- | ---------- |
| 1 | **STORY-05-001** | **Base da API e OpenAPI (FastAPI/Flask + Swagger)** | Configurar o app base, definir rotas `/health` e gerar o artefato OpenAPI vazio. |
| 2 | **STORY-05-002** | **Middleware de Auth e Wrapper de Segurança** | Injetar obrigatoriamente as flags de `actionable=false` e `is_simulated=true` em todos os retornos. Exigir `X-API-Key`. |
| 3 | **STORY-05-003** | **Endpoint de Consulta Pagina: Detections** | Criar `GET /api/value-detections` com `limit`, `offset` e suporte a filtros básicos (`source`, `detection_method`, `date`). |
| 4 | **STORY-05-004** | **Endpoint de Drill-down Detections** | Criar `GET /api/value-detections/{id}`. |
| 5 | **STORY-05-005** | **Endpoint de Consulta: Backtests** | Criar `GET /api/backtests` para consultar os relatórios gerados e indexados de papel trading. |
| 6 | **STORY-05-006** | **Auditoria de Contratos DTO** | Garantir, através de testes em nível de view/roteamento, que propriedades financeiras (Kelly, stake) não vazam no JSON. |

## 8. Estratégia de testes

* **Unitários**: Testar as funções de filtro, paginação e validadores DTO, garantindo injeção apropriada dos middlewares.
* **Integração**: Subir a aplicação usando o cliente de teste nativo (ex: `TestClient` do FastAPI ou Flask) contra um banco SQLite em memória que retorne resultados de paper trading, com e sem Header HTTP de API Key.
* **Segurança e Contrato**:
  - Testar propositalmente chamadas anônimas buscando receber HTTP 401 ou 403.
  - Assertivas rígidas verificando se os campos da **seção 5** estão presentes e marcados como booleanos restritivos no JSON puro de resposta em todas as rotas (guardrails adversariais).

## 9. Dívidas ou bloqueios

### Críticos
Nenhum bloqueio arquitetural impede a inicialização desta API read-only.

### Médios
Definição estrutural entre manter Flask da API legada (`backend/app`) ou criar uma micro-aplicação segregada e mais moderna em `src/edgehunter/api` usando FastAPI, para se beneficiar da documentação OpenAPI/Swagger gratuita. *(A recomendação da Onda 5 é modernizar para FastAPI ou utilizar extensões fortes para Flask se reaproveitado).*

### Baixos
O schema `value_detections` precisa de indíces apropriados caso a paginação seja submetida a varreduras longas.

## 10. Primeiro prompt recomendado

```text
use bmad-agent-dev

# Tarefa: Implementar STORY-05-001 — Base da API e OpenAPI (Health Check)

## Contexto
Onda 5 aprovada. O objetivo desta story é fundar o aplicativo da API REST, sem ainda expor dados analíticos do EdgeHunter, focando exclusivamente na estrutura base, criação do endpoint GET /api/health e a configuração fundamental para geração de OpenAPI (Swagger).

## Objetivo
1. Escolher e configurar o framework da API (recomenda-se criar em src/edgehunter/api/app.py).
2. Criar a rota GET /api/health retornando status: "ok" e a flag is_simulated: true.
3. Expor /docs (OpenAPI/Swagger) configurado.
4. Escrever testes validando o startup da aplicação e o retorno de health.

Lembre-se dos guardrails: Sem aposta real, sem stake/Kelly, sem requisições HTTP externas.
```

## 11. Etapas restantes estimadas

A Onda 5 foi planejada com **6 stories**.

## 12. Decisão para Rafael

* [x] Pode iniciar Onda 5.
* [ ] Pode iniciar com ressalvas.
* [ ] Não deve iniciar ainda.

**Justificativa técnica**: O core local analítico do EdgeHunter foi robustecido, deduplicado de forma material e atende às expectativas base. A falta de API Segura é um estrangulador que impede o progresso do GeminiValidator e o desenvolvimento de clientes web. A Onda 5 trará essa infraestrutura com barreiras sistêmicas fortíssimas, transformando o projeto de um script isolado em um motor consultável profissionalmente e protegido. O caminho foi pavimentado pela Onda 4B e está limpo. O plano é exequível.
