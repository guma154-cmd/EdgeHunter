# Plano de Execução — Onda 8 EdgeHunter

## 1. Veredicto

* [ ] APROVADO PARA COMEÇAR ONDA 8
* [ ] APROVADO COM RESSALVAS
* [ ] NÃO APROVADO

## 2. Objetivo da Onda 8

Criar um Outcome Feedback Loop simulado para registrar resultados observados de sinais classificados como GREEN_SIM ou RED_SIM, calcular métricas de acerto/erro, recalibrar assertividade histórica e sugerir ajustes técnicos de threshold, tudo em ambiente de aprendizado isolado. O sistema emitirá sugestões de autoaperfeiçoamento sem jamais aplicar as mudanças automaticamente.

## 3. Decisão de rota

Ao comparar as opções disponíveis, escolhemos **feedback loop de outcomes**. 
Avançar para o dashboard exigiria que as métricas de outcome e calibração estivessem presentes no backend; o Gemini Real continua proibido por segurança; hardening de migrações é infraestrutura e não avança o modelo analítico. O feedback loop é o caminho natural pós-Onda 7 para habilitar o aprendizado da IA sobre suas próprias simulações.

## 4. Modelo de outcome

* **Como registrar:** Entidade `SimulatedOutcomeResult` com um Enum explícito de estado.
* **Chave de vinculação:** O outcome será vinculado via `classification_id`, que é o nível de granularidade mais fino e exato de uma decisão de threshold (que por sua vez já carrega o `signal_id` e `opportunity_id`).
* **Estados Permitidos (Enum):**
  * `POSITIVE_OBSERVED`: O mercado validou a tese/tendência de forma favorável.
  * `NEGATIVE_OBSERVED`: O mercado não seguiu a tese, resultando em cenário desfavorável.
  * `UNRESOLVED`: O evento foi cancelado, suspenso ou não teve resultado apurável.
  * `INVALIDATED`: A oportunidade não chegou a abrir ou sofreu alteração severa.
* **Formato:** O resultado é um Enum, não booleano, para permitir nuances (ex: Unresolved).

## 5. Métricas de aprendizado

As interseções do modelo de aprendizado serão definidas pela matriz de confusão:
* **Sucesso de GREEN_SIM:** `GREEN_SIM` + `POSITIVE_OBSERVED` = `green_success`
* **Sucesso de RED_SIM:** `RED_SIM` + `NEGATIVE_OBSERVED` = `red_success` (rejeição correta)
* **Falso Positivo de GREEN_SIM:** `GREEN_SIM` + `NEGATIVE_OBSERVED` = `green_false_positive`
* **Falso Negativo de RED_SIM:** `RED_SIM` + `POSITIVE_OBSERVED` = `red_false_negative` (perdeu boa oportunidade)

## 6. Recalibração de threshold

O módulo analisará a base de outcomes em lotes (ex: últimos 100 resultados) e projetará curvas teóricas. Ele identificará o *Threshold Ideal* hipotético que teria maximizado a taxa de acerto ou evitado os Falsos Positivos.

* **Como recalibrar sem aplicar:** O sistema gera um relatório `SimulatedThresholdSuggestion` contendo as diretrizes (`current_threshold`, `suggested_threshold`, `reason`, `confidence`, `sample_size`).
* **Registro:** Essa sugestão será persistida apenas para fins de auditoria/histórico, em tabela própria, como uma "recomendação da IA".
* **Comportamento Sugerido:** "subir threshold" (muitos falsos positivos), "reduzir threshold" (muitos falsos negativos perdidos), "manter threshold" (curva ideal) ou "exigir mais amostra".

## 7. Guardrails contra AutoEvolution

* A classe `SimulatedThresholdSuggestion` possuirá obrigatoriamente os campos: `auto_apply=False`, `is_simulated=True`, `actionable=False`.
* Pydantic `@validator` na camada de persistência para travar se `auto_apply` for `True`.
* O mecanismo de classificação (`classify_simulated_signal`) da Onda 7 continuará usando sua constante operacional estática de 0.70. O relatório da Onda 8 não terá autoridade ou interface para injetar a variável de runtime no classificador.

## 8. Escopo proibido

Absolutamente proibido na Onda 8: aposta real, execução financeira, comando de entrada, alerta acionável, AutoEvolution, alteração automática de threshold, Telegram operacional, scheduler operacional, integração com casa de aposta, cálculo de stake/Kelly/bankroll.

## 9. Stories propostas

| Ordem | Story | Objetivo | Observação |
| ----: | ----- | -------- | ---------- |
| 1 | STORY-08-001 | Contrato de Outcome Simulado | Criar Modelos e Enums para SimulatedOutcomeResult |
| 2 | STORY-08-002 | Persistência de Outcomes | Funções puras em SQLite vinculadas ao classification_id |
| 3 | STORY-08-003 | Vínculo Outcome ↔ Classificação | Expansão do learning report para cruzar Classifications vs Outcomes reais persistidos |
| 4 | STORY-08-004 | Sugestão de Threshold (Recalibração) | Algoritmo que calcula e gera a SimulatedThresholdSuggestion baseada em histórico recente |
| 5 | STORY-08-005 | API Read-Only | Endpoints GET para consultar Outcomes e Suggestions |
| 6 | STORY-08-006 | Encerramento da Onda 8 | Relatório de fechamento e verificação de guardrails |

## 10. Estratégia de testes

*   **Testes Unitários:** Para a lógica de cálculo das taxas (Verificação rigorosa da matriz FP/FN/Sucessos).
*   **Testes Adversariais:** Enviar `auto_apply=True` no contrato da sugestão e garantir que ele gera falha catastrófica ou recusa, protegendo contra AutoEvolution.
*   **Testes de Integração:** SQLite `classification_id` foreign key ou verificação de integridade entre as entidades.
*   Executar consistentemente o script `check_transaction_discipline.py`.

## 11. Dívidas ou bloqueios

*   **Dívida prévia mantida:** Banco de dados SQLite contínuo sem framework de migração robusto (Drop/Create/Update_on_conflict ainda é usado localmente).

## 12. Primeiro prompt recomendado

```markdown
use bmad-agent-dev

# Tarefa: Implementar STORY-08-001 — Contrato de Outcome Simulado

## Etapa atual
Onda 8 — Etapa 1.

## Objetivo
Criar os contratos de dados e enums que representarão o resultado observado de uma classificação simulada. 

Implementar `SimulatedOutcomeState` como Enum (POSITIVE_OBSERVED, NEGATIVE_OBSERVED, UNRESOLVED, INVALIDATED).
Implementar `SimulatedOutcomeResult` com as chaves de segurança estritas (is_simulated=True, actionable=False, auto_apply=False) e o vínculo mandatório por `classification_id`.
Garantir rejeição de campos financeiros via `FORBIDDEN_FIELDS` (stake, kelly, bankroll).

Crie também a bateria de testes unitários que garantem esses comportamentos em `tests/unit/core/test_simulated_outcome_contract.py`.
```

## 13. Etapas restantes estimadas

A Onda 8 terá o total de **6 stories**.

## 14. Decisão para Rafael

* [ ] Pode iniciar Onda 8.
* [ ] Pode iniciar com ressalvas.
* [ ] Não deve iniciar ainda.
