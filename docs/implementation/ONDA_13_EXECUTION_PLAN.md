# Onda 13 — Calibração Histórica Avançada / Advanced Calibration Intelligence

## 1. Veredicto da Onda 13
A Onda 13 visa criar a inteligência estatística avançada do EdgeHunter, focada em estabelecer métricas detalhadas de calibração para diferentes segmentos do modelo, identificando padrões de melhoria ou degradação e sugerindo limiares de confiança sem modificar diretamente a operação financeira.

## 2. Objetivo Técnico
Desenvolver módulos puros (sem persistência automatizada ou interação de rede/API não autorizada) para classificar o histórico técnico (segmentação), avaliar as tendências, gerar scores técnicos de confiabilidade e produzir sugestões avançadas de thresholds que suportem as decisões sem AutoEvolution.

## 3. Escopo Permitido
- Criar contratos de score técnico de confiabilidade.
- Segmentar histórico por `source`, `detection_method`, `simulation_label`, `market`, `selection` e faixas de assertividade.
- Calcular métricas de performance por segmento (falsos positivos/negativos, taxas de confirmação).
- Avaliar a estabilidade ou volatilidade de cada segmento por período.
- Gerar o Score Técnico de Confiabilidade e a Sugestão Técnica Avançada de threshold de forma read-only.
- Expor relatórios e métricas via API read-only.
- Incluir visualização em dashboard read-only, se a fundação já existir.
- Aplicar testes adversariais rigorosos.

## 4. Escopo Proibido
- Nenhuma ação, cálculo financeiro operacional, stake, Kelly ou bankroll.
- Sem uso de Telegram, scheduler operacional ou AutoEvolution.
- Nenhuma modificação automática de threshold (Auto-apply) baseada nas sugestões geradas.
- Proibida interação real com Gemini, rede externa ou web scrapers.
- POST/PUT/PATCH/DELETE bloqueados nas APIs da Onda 13.

## 5. Modelo de Score de Confiabilidade
Definição dos níveis de confiabilidade (Ex: HIGH, MEDIUM, LOW, INSUFFICIENT_SAMPLE) e composição técnica de um score consolidando performance, tendência, confiança e assertividade, garantindo que o valor final seja normalizado (0.0 a 1.0).

## 6. Estratégia de Segmentação Histórica
Os dados históricos vinculados no EdgeHunter serão segmentados através de um mecanismo determinístico de agrupamento usando as dimensões chave do sistema (Source, Method, Market, Label, etc.) permitindo a aplicação independente das métricas para as janelas de calibração.

## 7. Estratégia de Análise por Faixas de Assertividade
As métricas serão detalhadas por buckets de 10% (0.00-0.09 a 0.90-1.00) da assertividade da IA, viabilizando o isolamento de instabilidades que podem surgir especificamente em ranges altos ou baixos.

## 8. Estratégia de Detecção de Melhoria/Degradação
Função de detecção técnica e estática para categorizar o avanço dos padrões numéricos das predições: IMPROVING, STABLE, DECLINING ou VOLATILE. O motor compara estatísticas da amostra com métricas de período anterior (se fornecidas).

## 9. Estratégia de Sugestão Técnica Avançada de Threshold
Módulo consultivo de Threshold que analisa as métricas de confiabilidade, falso positivo e erro para sugerir as seguintes ações read-only: KEEP_THRESHOLD, RAISE_THRESHOLD, LOWER_THRESHOLD e REQUIRE_MORE_SAMPLE.

## 10. Stories Propostas
- STORY-13-001 — Plano formal da Onda 13
- STORY-13-002 — Contratos de Score Técnico de Confiabilidade
- STORY-13-003 — Segmentação Histórica por Source/Method/Label
- STORY-13-004 — Métricas por Faixa de Assertividade
- STORY-13-005 — Detector de Degradação/Melhoria de Padrão
- STORY-13-006 — Score Técnico de Confiabilidade por Segmento
- STORY-13-007 — Sugestão Técnica Avançada de Threshold
- STORY-13-008 — API/Dashboard Read-only da Calibração Avançada
- STORY-13-009 — Testes Adversariais da Calibração Avançada
- STORY-13-010 — Encerramento da Onda 13

## 11. Estratégia de Testes
Onda altamente baseada em testes analíticos e cálculos de fronteiras numéricas. Todos os métodos incluirão testes unitários assertivos com falhas antecipadas (ex: Divisão por Zero, Dados Vazios). A story final contemplará testes adversariais que forçam vazamento de terminologia bloqueada ou violação de mutabilidade.

## 12. Guardrails
- Language Checker nativo que expurga nomenclaturas que denotam ações operacionais.
- Validação estrita de Flags Seguras (is_simulated=True, bet_placed=False, actionable=False).
- Imutabilidade do Threshold na operação principal do sistema EdgeHunter.

## 13. Critérios de Encerramento
1. Código 100% testado (unit tests).
2. Gates globais consistentes sem degradação do banco SQLite.
3. Repositório de trabalho na Master limpo (`git status` e branch rules).
4. Todas as Stories de 1 a 10 implementadas e validadas contra o plano executivo.

## 14. Tag Alvo
`v1.6-onda13-advanced-calibration`
