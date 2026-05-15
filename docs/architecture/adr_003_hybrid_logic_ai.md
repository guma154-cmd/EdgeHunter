# ADR-003: Estratégia Híbrida (Lógica + IA)

*   **Status**: Accepted
*   **Date**: 2025-05-15
*   **Deciders**: Rafael
*   **Consulted**: Claude, Gemini
*   **Informed**: -

## Context and Problem Statement

O sistema de value betting precisa ser capaz de identificar oportunidades de forma rápida e consistente, mas também com inteligência suficiente para se adaptar a cenários complexos ou anômalos. A escolha entre uma abordagem puramente lógica (baseada em regras), puramente de Inteligência Artificial (IA) ou uma combinação híbrida é fundamental para equilibrar custo, performance, determinismo e adaptabilidade do sistema. O `AutoEvolution` (PRD-05) atua como o motor de decisão operacional, necessitando dessa estratégia para orientar suas ações.

## Decision Drivers

*   **Velocidade e Determinismo**: Capacidade de operar rapidamente com resultados previsíveis para a maioria das decisões.
*   **Custo Operacional**: Minimizar os custos associados ao uso de recursos de IA, que geralmente são baseados em consumo.
*   **Inteligência e Adaptação**: Habilidade de lidar com exceções, anomalias ou situações complexas que regras fixas não cobririam.
*   **Manutenibilidade**: Facilidade de entender, depurar e ajustar a lógica do sistema.
*   **Restrições de Tier Gratuito**: A necessidade de operar dentro de limites de uso para evitar custos, aproveitando tiers gratuitos de IA.

## Considered Options

*   **100% Lógica Determinística**: Sistema baseado inteiramente em regras fixas e algoritmos predefinidos.
*   **100% Inteligência Artificial (IA Pura)**: Todas as decisões são tomadas por modelos de IA, com base em dados e aprendizado.
*   **Estratégia Híbrida (Lógica e IA Ocasional)**: A maioria das decisões é tomada por lógica determinística; a IA é acionada apenas em casos específicos ou quando agrega valor significativo.

## Decision Outcome

**Chosen option**: "Estratégia Híbrida (Lógica e IA Ocasional)"

**Justification**: A estratégia híbrida oferece o melhor dos dois mundos para um sistema de value betting. A maioria das decisões críticas (cálculo de stake, ajuste de threshold em cenários normais, avanço de fase) pode ser feita de forma determinística e rápida por lógica baseada em regras, que é barata e previsível. A IA (especificamente o Gemini 2.0 Flash) é utilizada pontualmente para validação de oportunidades de alto EV, detecção de anomalias e sugestões de evolução de baixo risco, onde sua inteligência adaptativa pode agregar valor sem incorrer em custos excessivos (aproveitando o free tier). Isso garante velocidade e determinismo onde são mais importantes, ao mesmo tempo que permite a intervenção inteligente da IA em situações que justificam seu custo e latência.

### Positive Consequences

*   **Custo Otimizado**: Aproveita o free tier de serviços de IA (como Gemini Flash) ao limitar as chamadas apenas onde são essenciais.
*   **Determinismo na Maior Parte**: Garante que a maioria das operações seja previsível, rápida e fácil de auditar.
*   **Inteligência Adaptativa**: Permite que a IA lide com anomalias, padrões emergentes ou validações complexas que regras fixas não abordariam.
*   **Menor Latência Média**: Evita o overhead de IA na maioria das decisões, mantendo o sistema responsivo.

### Negative Consequences

*   **Maior Complexidade**: Mais complexo de projetar e manter do que abordagens puras, pois requer lógica para decidir "quando chamar a IA".
*   **Gestão de Thresholds**: Necessidade de documentar claramente os thresholds e gatilhos que disparam a intervenção da IA.
*   **Potencial "Glue Code"**: Risco de criar código de "cola" (glue code) complexo para integrar as duas abordagens.

## Implicações de Testabilidade e Confiabilidade

A estratégia híbrida, embora otimizada, introduz complexidade na garantia de qualidade. As seguintes abordagens serão adotadas para mitigar os riscos e garantir a robustez:

*   **Isolamento e Mocking da IA**: Para testes unitários e de integração dos componentes de lógica determinística, as chamadas à API da IA (Gemini Flash) serão mockadas. Isso permitirá simular diversos retornos da IA (sucesso, falha, latência alta, respostas ambíguas) de forma isolada e determinística.
*   **Controle de Respostas da IA para Testes**: Serão desenvolvidos mocks ou stubs que permitam controlar as respostas da IA, simulando cenários específicos de validação, detecção de anomalias e sugestões para verificar a lógica do sistema.
*   **Geração de Dados de Teste**: Dados de teste serão gerados para cobrir os thresholds e triggers que acionam a IA, garantindo que a IA seja chamada apenas nos momentos corretos e a lógica de fallback seja testada.
*   **Circuit Breakers para IA**: Será implementado um Circuit Breaker para as chamadas à API da IA. Este circuit breaker pausará ou redirecionará requisições se a IA apresentar alta latência, erros consecutivos (5xx) ou indisponibilidade, protegendo o sistema de falhas em cascata.
*   **Estratégia de Degradação Graciosa**: Em caso de falha ou indisponibilidade da IA, o sistema continuará operando com base apenas na lógica determinística, retornando a um estado seguro (ex: não enviar alertas de alto risco, reduzir stakes, usar um threshold mais conservador).
*   **Plano de Disaster Recovery para IA**: Embora a IA seja externa, será documentado um plano de contingência para falhas prolongadas, incluindo a possibilidade de um fallback para um modelo local simplificado ou a operação em modo puramente lógico.
*   **Gerenciamento de Compatibilidade e Rollback**: As regras lógicas e os modelos de IA (prompts e configurações) serão versionados. Para modelos de IA, será estabelecida uma estratégia para gerenciar mudanças comportamentais e garantir compatibilidade retroativa. Um plano claro de rollback será definido para reverter para versões anteriores de regras ou prompts em caso de problemas.
*   **SLAs e Monitoramento**: Serão definidos SLAs explícitos para a latência das chamadas à IA e para a responsividade geral do sistema. O monitoramento incluirá a latência da IA, a taxa de sucesso das chamadas e o volume de uso, para garantir que os custos e a performance estejam dentro do esperado.

## Pros and Cons of the Options

### 100% Lógica Determinística

*   Good: Rápido, previsível, baixo custo, fácil de depurar e entender.
*   Bad: Incapaz de se adaptar a padrões não previstos ou anomalias, limitado pela complexidade das regras codificadas.

### 100% Inteligência Artificial (IA Pura)

*   Good: Alta capacidade de adaptação, pode identificar padrões complexos, potencial para otimização contínua.
*   Bad: Alto custo de operação (chamadas de API), maior latência, "caixa preta" (baixa interpretabilidade), dependência de grandes volumes de dados de treino.

### Estratégia Híbrida (Lógica e IA Ocasional)

*   Good: Otimização de custos, velocidade na maioria das operações, inteligência adaptativa para exceções, aproveitamento de free tiers de IA.
*   Bad: Maior complexidade de design e manutenção, exige critérios claros para acionamento da IA.

## Links

*   [PRD-04 (GeminiValidator) que referencia este ADR]
*   [PRD-05 (AutoEvolution) que referencia este ADR]
*   ADR-005: LLM Choice (Gemini 2.0 Flash)
