# Plano de Execução — Onda 7 EdgeHunter

## 1. Veredicto

Escolher:

* [ ] APROVADO PARA COMEÇAR ONDA 7
* [x] APROVADO COM RESSALVAS
* [ ] NÃO APROVADO

(Ressalva: as validações apontaram links locais quebrados no relatório da Onda 6 devido a marcações absolutas `file:///...`, que precisam ser tratadas no CI/doc, mas a lógica e o negócio estão aprovados para evoluir.)

## 2. Objetivo da Onda 7

Adicionar um **cliente real** do Gemini (`RealGeminiValidationClient`) na infraestrutura já segura construída na Onda 6, garantindo proteção financeira via controle de quotas, timeout e failover local síncrono. O objetivo é testar a rede em produção, provando que o EdgeHunter consegue obter respostas do Gemini sem ultrapassar limites, sem quebrar perante lentidões da IA, e sem gerar conselhos operacionais. 

O cliente real só deve ser habilitado ativamente quando `GEMINI_API_KEY` estiver presente e o usuário optar por usá-lo.

## 3. Decisão de rota

A rota escolhida é a **Opção D — Onda híbrida**. 
Criaremos o cliente real mockável, controles de cota, timeout e fallback para o cliente fake. O sistema, mesmo após a Onda 7, não disparará apostas reais; continuaremos com paper trading e sem recomendação de stake/Kelly (esses temas permanecem fora do Gemini). A Onda 7 fecha o ciclo técnico da IA introduzindo a rede de forma totalmente governada.

## 4. Dependências externas

- **Biblioteca**: `google-generativeai`.
- **Inclusão**: Deve ser adicionada em `pyproject.toml` como dependência principal de `runtime`, mas o sistema deve degradar para "fake" graciosamente se ela falhar ou se não houver chave.
- O SDK só deve ser instanciado no `RealGeminiValidationClient`.

## 5. Segurança de segredo/API key

- A chave da API deve ser carregada via variável de ambiente `GEMINI_API_KEY` a partir do `.env`.
- **Proibido:** hardcode, passagem explícita no código fonte como string, commit da chave ou log da mesma.
- Testes unitários NÃO devem ler do `.env` real nem atingir a API. Devem injetar Mocks ou chaves sintéticas.
- Caso a API key não exista, a inicialização do cliente real falha defensivamente e volta ao modo fake.

## 6. Timeout, retry e fallback

Conforme PRD-04:
- **Timeout**: Máximo de 10 segundos por chamada.
- **Retry**: Decorator/logica com exponential backoff (ex: 1s, 2s, 4s), máximo de 3 tentativas por chamada.
- **Fallback**: Se todos os retries falharem, ou se houver esgotamento de quota ou RateLimit (429), o cliente degrada para o _fallback determinístico_ (`FakeGeminiValidationClient` ou retorno `unavailable`/`SEM_VALIDACAO_IA`), logando o evento.

## 7. Cotas e custos

Estratégia de orçamento de Tokens:
- **Limite mensal**: 1.600.000 tokens (para proteger 80% do Free Tier de 2M).
- **Monitoramento**: Antes de chamar o Gemini real, checar se a cota do mês corrente foi esgotada.
- **Recusa:** Se o teto for atingido, negar a chamada de rede e devolver fallback imediatamente.

## 8. Persistência de usage

- Uma nova tabela `gemini_token_usage` (com chave mês_ano) deve ser adicionada ao schema para consolidar os tokens.
- O relatório IA da oportunidade, em `gemini_validation_reports.tokens_used`, já existe no banco e deverá ser preenchido com o metadata retornado pelo provedor real.

## 9. Stories propostas

| Ordem | Story | Objetivo | Observação |
| ----: | ----- | -------- | ---------- |
| 1 | **STORY-07-001** | Controle de cota de tokens | Criar tabela de usage mensal, tracking e lógica de recusa ao atingir o budget de 1.6M. |
| 2 | **STORY-07-002** | Dependência oficial e configuração de chave | Atualizar `pyproject.toml` com SDK, ler chave do ambiente sem logar e sem hardcode. |
| 3 | **STORY-07-003** | `RealGeminiValidationClient` com retry e timeout | Cliente que faz a requisição de rede, implementando backoff e limite de 10s, retornando payload cru. |
| 4 | **STORY-07-004** | Orquestração híbrida com Fallback dinâmico | Integrar cliente real, parser, token tracking e downgrade para FakeClient em caso de erro. |
| 5 | **STORY-07-005** | Testes e liberação | Suítes de mock, testes adversariais de rede (simular Timeout) e teste opcional/skips de integração real. |

## 10. Estratégia de testes

- **Unitários com Mock**: Testar a lógica de backoff e timeouts lançando exceções simuladas. `google.generativeai` deve ser "monkeypatched".
- **Contrato e Sanitização**: Garantir que as restrições da Onda 6 não quebraram.
- **Testes de Orçamento**: Validar parada síncrona ao atingir o limite na tabela.
- **Integração Real (Opcional)**: Um teste específico, desabilitado por padrão (e.g. `@pytest.mark.integration`), para rodar o fluxo completo apenas quando autorizado.

## 11. Guardrails de linguagem

- O prompt validado e encurtado na Onda 6 será reutilizado (garante disclaimer explícito de "não operacional").
- O parser seguro da Onda 6, que possui `_BLOCKED_TERMS`, impedirá vazamentos de "stake", "aposta", "recomendação", etc., caso o Gemini ignore o prompt.
- As flags `actionable=False` e `is_simulated=True` continuam hardcoded nos contratos de entrada e saída.

## 12. Escopo proibido

- Aposta real;
- Execução financeira;
- Modulação via Stake, Kelly ou Bankroll;
- Telegram operacional / Alertas por notificação fora de logs;
- Scheduler operacional para auto-betting;
- AutoEvolution (módulo segue pendente);
- Integração de leitura/escrita em Casas de aposta.

## 13. Dívidas ou bloqueios

### Críticos
Nenhum. A arquitetura defensiva da Onda 6 provê terreno seguro. As quebras da verificação de consistência de docs da Onda 6 precisam ser resolvidas para passar no CI sem erro, mas não são bloqueios arquiteturais.

### Médios
- `api/backtests` continua vazia (herdado da Onda 5). Persistência de backtests formais continua atrasada.

### Baixos
- Consistência dos links markdown locais (`file:///` path) identificada pelo validador.

## 14. Primeiro prompt recomendado

```text
# Tarefa: Implementar STORY-07-001 — Controle de cota de tokens

## Objetivo
Criar mecanismo SQLite para gerenciar uso mensal de tokens, protegendo a cota do Free Tier.

## Instruções
1. Atualizar o script de schema no `schema.py` para criar a tabela `gemini_token_usage` (mês_ano, tokens_input, tokens_output, total).
2. Criar um repositório `token_budget.py` com o método `check_budget_available()` (limite hardcoded de 1.600.000).
3. Criar o método `record_usage(input_tokens, output_tokens)`.
4. Garantir que não existam queries soltas (usar padrão repositório + contexto).
5. Escrever testes unitários em `test_token_budget.py`.
```

## 15. Etapas restantes estimadas

A Onda 7 é projetada para ser entregue em **5 stories** concisas.

## 16. Decisão para Rafael

* [x] Pode iniciar Onda 7.
* [ ] Pode iniciar com ressalvas.
* [ ] Não deve iniciar ainda.

**Justificativa**: A infraestrutura defensiva construída nas Ondas 5 (API Segura) e 6 (Validador Offline via Fake) garante que o sistema está blindado contra comportamentos maliciosos e conselhos operacionais da IA. O terreno está tecnicamente e contratualmente seguro para adicionarmos o risco de rede (Opção D). A integração é focada 100% em resiliência local (retries e fallbacks) e orçamentação financeira (proteção ao Free Tier), e não alterará uma vírgula sequer das proibições de aposta real.
