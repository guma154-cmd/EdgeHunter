# Plano de Execução — Onda 7 EdgeHunter

## 1. Veredicto

Escolher:

* [x] APROVADO PARA COMEÇAR ONDA 7
* [ ] APROVADO COM RESSALVAS
* [ ] NÃO APROVADO

## 2. Objetivo da Onda 7

Onda 7 — Simulated Green/Red Classifier.

O objetivo técnico principal desta onda é transformar a validação da IA em uma classificação simulada rigorosa e binária, baseada no estudo histórico de contexto. O plano anterior de integração contínua de rede real do Gemini foi substituído pelo foco em aprendizado histórico ("learning mode").

O sistema preservará o Gemini/IA como revisor técnico e integrará sua avaliação (a `confidence`) com dados históricos — agrupamentos técnicos, backtests e falsos positivos passados — para derivar a `calibrated_assertiveness`. O resultado final será um label rigoroso:
- **GREEN_SIM**: Sinais simulados com assertividade calibrada >= 70%.
- **RED_SIM**: Sinais simulados com assertividade calibrada < 70%.

Zonas neutras não são permitidas.

## 3. Decisão de rota

A rota agora foca na **Classificação Simulada Binária e Aprendizado Histórico**.
A IA fornece a análise técnica, e o sistema cruza esses dados com a resiliência histórica do sistema para obter a `calibrated_assertiveness`. O foco é estudar acertos e erros, ajustar algoritmos para prever falsos positivos e negativos de forma empírica e manter as execuções restritas ao estudo não operacional.

## 4. Dependências externas

A adoção real da API do Gemini (e o SDK `google-generativeai`) pode prosseguir se útil para mock/integração síncrona offline de relatórios, mas o "Gemini real operacional" não é mais o foco da camada de classificação. O esforço se concentra no cálculo de probabilidade condicionada com base na análise textual, não no transporte HTTP.

## 5. Segurança de segredo/API key

Nenhuma configuração de rede exposta ao pipeline principal; qualquer teste ou mock deve respeitar a premissa de que a rede real pode ser trocada e a chave da API deve vir unicamente do `.env` e nunca logada.

## 6. Timeout, retry e fallback

Se a análise não for possível, o classificador fará `fail-closed` para `RED_SIM` (assertividade forçada a 0), priorizando proteção matemática perante a incerteza do sistema.

## 7. Cotas e custos

Como o objetivo é focar em classificação simulada histórica, processaremos massivamente dados de backtest já contidos no SQLite, garantindo não gerar custos de transação desnecessários em endpoints de terceiros.

## 8. Persistência de usage

Os esquemas e DTOs deverão acomodar os novos campos exigidos:
* `simulation_label`: GREEN_SIM | RED_SIM
* `calibrated_assertiveness`: float entre 0.0 e 1.0
* `confidence`: float entre 0.0 e 1.0 (já existente, derivado da revisão técnica)
* `learning_mode`: true
* `display`: true
* Campos de segurança mantidos: `is_simulated: true`, `paper_trading: true`, `actionable: false`, `bet_placed: false`, `alerted: false`, `not_operational_advice: true`.

## 9. Stories propostas

| Ordem | Story | Objetivo | Observação |
| ----: | ----- | -------- | ---------- |
| 1 | **STORY-07-001** | Contrato do Green/Red Classifier | Atualizar DTOs e entidades com os novos labels, flags (`learning_mode`, `display`) e a taxonomia rigorosa sem zona neutra. |
| 2 | **STORY-07-002** | Motor de Assertividade Calibrada | Implementar regra `>= 70%` para `GREEN_SIM` usando lógica empírica baseada no histórico. |
| 3 | **STORY-07-003** | Persistência dos Labels de Aprendizado | Adicionar colunas `simulation_label`, `calibrated_assertiveness`, `learning_mode` e `display` no schema do DB SQLite. |
| 4 | **STORY-07-004** | Estudo de Acertos, Falsos Positivos e Falsos Negativos | Implementar métricas focadas no estudo quantitativo das categorizações GREEN/RED_SIM frente aos resultados reais das partidas passadas. |
| 5 | **STORY-07-005** | Geração de Relatórios Técnicos | Consolidar endpoints/rotinas para exportar ou consultar o estudo histórico focado no aprendizado do algoritmo. |

## 10. Estratégia de testes

* **Mock do Classificador**: Validar cenários onde uma alta `confidence` da IA é sobreposta e corrigida por uma baixa `calibrated_assertiveness` (forçando `RED_SIM`) devido ao histórico ruim do agrupamento técnico.
* **Teste de Rigidez**: Evidenciar falha do parser e fail-close se tentar atribuir uma "zona neutra" ou um veredito intermediário.
* **Testes de Segurança**: Validar estaticamente as propriedades `actionable=False` e `learning_mode=True`.

## 11. Guardrails de linguagem

A terminologia do sistema abandona conselhos operacionais ou predições. Passa a lidar puramente em termos de estatística de backtest: "Simulation Label", "Calibrated Assertiveness", "Learning Mode".

## 12. Escopo proibido

Onda 7 e subsequentes seguem estritamente proibidas de implementar:
* Recomendação operacional;
* Execução financeira real ou integração com casas de aposta;
* Prescrição de Stake, dimensionamento por Kelly Criterion ou cálculo de Bankroll;
* Alerta acionável ou push para o Telegram;
* Comando de entrada ou triggers de sistema.
* Scheduler operacional contínuo ou o antigo engine do AutoEvolution.

## 13. Dívidas ou bloqueios

### Críticos
Nenhum.

### Médios
O acesso a "histórico de falsos positivos e performance recente" para calcular a `calibrated_assertiveness` forçará a resolução da dívida de repositórios ausentes de execuções passadas (o endpoint `/api/backtests` vazio). Será necessário interconectar relatórios passados simulados.

### Baixos
Nenhum.

## 14. Primeiro prompt recomendado

```text
# Tarefa: Implementar STORY-07-001 — Contrato do Green/Red Classifier

## Objetivo
Atualizar o SafeAIValidationResult e os contratos DTO do Gemini para suportar as flags de simulação binária do classificador.

## Instruções
1. Em `src/edgehunter/core/gemini_validator.py`, adicionar a classe/Enum `SimulationLabel` com valores apenas `GREEN_SIM` e `RED_SIM`.
2. Adicionar as propriedades: `simulation_label: SimulationLabel`, `calibrated_assertiveness: float`, `learning_mode: bool = True`, `display: bool = True`.
3. Manter inalteradas as propriedades estritas (`actionable: bool = False`, `is_simulated: bool = True`, etc).
4. Ajustar as regras de instanciacão para forçar que `GREEN_SIM` ocorra unicamente se `calibrated_assertiveness >= 0.7`.
5. Modificar e expandir o `test_gemini_validator_contract.py` para provar que a falta da label binária e as lógicas `>= 70%` funcionam sob coerção.
```

## 15. Etapas restantes estimadas

5 stories estimadas, substituindo as histórias de infraestrutura de rede por histórias de enriquecimento de base analítica.

## 16. Decisão para Rafael

* [x] Pode iniciar Onda 7.
* [ ] Pode iniciar com ressalvas.
* [ ] Não deve iniciar ainda.

**Justificativa**: A mudança do foco da integração real com Gemini para o "Simulated Green/Red Classifier" é madura e altamente alinhada com o modelo paper-trading e non-actionable do projeto. A nova onda alavanca a lógica estatística do sistema com dados simulados e transforma as predições em objetos de aprendizado, blindando a fundação do EdgeHunter de responsabilidades financeiras operacionais.
