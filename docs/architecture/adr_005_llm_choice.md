# ADR-005: Gemini 2.0 Flash como LLM Principal

*   **Status**: Accepted
*   **Date**: 2025-05-15
*   **Deciders**: Rafael
*   **Consulted**: Claude, Gemini
*   **Informed**: -

## Context and Problem Statement

A integração de modelos de linguagem grandes (LLMs) é um componente chave para funcionalidades como validação de oportunidades, detecção de anomalias e sugestões de evolução no sistema. A escolha do LLM impacta diretamente o custo, a latência, a qualidade das respostas e a sustentabilidade do projeto, especialmente considerando um volume limitado de chamadas de IA inicialmente.

## Decision Drivers

*   **Custo**: Priorizar soluções com tiers gratuitos ou de baixo custo para otimizar recursos.
*   **Latência**: Necessidade de respostas rápidas (<3s) para não atrasar o processo de alerta de value betting.
*   **Qualidade das Respostas**: O LLM deve ser "bom o suficiente" para as tarefas específicas (validação, anomalia, sugestões).
*   **Volume de Chamadas**: Estimativa de um volume baixo de chamadas (~40 chamadas/mês).
*   **Disponibilidade e Facilidade de Uso**: Acessibilidade da API e simplicidade de integração.

## Considered Options

*   **Gemini 2.0 Flash**: Modelo da Google otimizado para velocidade e custo, com um free tier generoso.
*   **Claude (Anthropic)**: Família de modelos conhecida pela capacidade de raciocínio e segurança, com custos competitivos.
*   **GPT-4 (OpenAI)**: Modelo líder de mercado, conhecido pela alta capacidade de raciocínio e geração de texto complexo.
*   **Gemini Pro**: Versão mais potente do Gemini, oferecendo maior capacidade de raciocínio que o Flash, mas com custo mais alto.

## Decision Outcome

**Chosen option**: "Gemini 2.0 Flash"

**Justification**: O Gemini 2.0 Flash é a opção mais adequada para as necessidades atuais do sistema, especialmente devido ao seu free tier generoso (2 milhões de tokens/mês) e à sua otimização para baixa latência (<3s). Para as tarefas específicas de validação, detecção de anomalias e sugestões de evolução (que não exigem raciocínio complexo profundo), o Flash oferece uma qualidade de resposta "boa o suficiente" e atende ao requisito de tempo real dos alertas. Dado o baixo volume de chamadas estimado (~40/mês), o free tier será mais do que suficiente para o projeto.

### Positive Consequences

*   **Custo Zero Inicial**: O free tier generoso elimina custos com IA para o volume de chamadas previsto.
*   **Baixa Latência**: Respostas rápidas garantem que os alertas de value betting não sejam atrasados.
*   **Suficiente para Tarefas**: A qualidade do Flash é adequada para as funções específicas delegadas à IA.
*   **Facilidade de Integração**: A API da Google é bem documentada e fácil de integrar.

### Negative Consequences

*   **Potencial Qualidade Inferior**: Pode ter uma qualidade de raciocínio ou nuances de resposta inferior a modelos mais caros (Gemini Pro, GPT-4, Claude) em tarefas mais complexas.
*   **Necessidade de Monitoramento**: Requer monitoramento contínuo da qualidade das respostas para garantir que não haja degradação ou falhas sutis.
*   **Risco de Escalabilidade de Custo**: Se o volume de chamadas ou a complexidade das tarefas crescerem significativamente, o custo pode escalar e exigir uma reavaliação.

## Implicações de Testabilidade e Confiabilidade

A dependência de um LLM externo, embora vantajosa em termos de custo e latência, introduz desafios em testabilidade, segurança e confiabilidade. As seguintes medidas serão adotadas:

*   **Isolamento e Mocking da API LLM**: Para testes isolados e determinísticos dos componentes que interagem com o Gemini Flash, a API do LLM será mockada. Isso permitirá simular retornos específicos (validação bem-sucedida, falha na validação, alucinações, latência alta, etc.) sem depender da conectividade externa ou incorrer em custos.
*   **Controle de Respostas da IA para Testes**: Serão desenvolvidos mocks ou stubs que permitam controlar as respostas do LLM, simulando diversos cenários de teste para verificar a lógica downstream do sistema.
*   **Geração de Dados de Teste**: Dados de teste variados serão gerados para cobrir uma ampla gama de entradas para o LLM, incluindo casos de borda e entradas que podem levar a respostas de baixa qualidade, para avaliar a robustez do sistema.
*   **Circuit Breakers para API LLM**: Será implementado um Circuit Breaker para chamadas à API do Gemini Flash. Ele atuará se a API apresentar alta latência ou erros consecutivos, protegendo o sistema de falhas em cascata e permitindo que ele opere em um modo degradado.
*   **Estratégia de Degradação Graciosa**: Em caso de falha ou indisponibilidade do serviço Gemini Flash, o sistema será capaz de operar de forma degradada (ex: desabilitar a validação de IA para certas oportunidades, usar regras lógicas mais conservadoras), evitando interrupções completas.
*   **Plano de Disaster Recovery para LLM**: Um plano de contingência será documentado para cenários de indisponibilidade prolongada do Gemini Flash, incluindo a potencial troca para outro provedor de LLM ou operação em modo puramente lógico.
*   **Segurança e Armazenamento de Chaves API**: As chaves da API do Gemini Flash serão armazenadas de forma segura (ex: variáveis de ambiente, gerenciador de segredos), nunca hardcoded no código fonte, e serão rotacionadas periodicamente.
*   **Validação e Sanitização de Input**: As entradas (prompts) enviadas para o LLM serão validadas e sanitizadas para prevenir ataques de "prompt injection" e garantir que apenas dados relevantes e seguros sejam processados.
*   **Gerenciamento e Versionamento de Prompts**: Os prompts e parâmetros do LLM serão tratados como código, versionados e submetidos a testes para garantir que as mudanças não afetem adversamente o comportamento do sistema.
*   **Compatibilidade e Rollback de Modelos**: Será definida uma estratégia para lidar com atualizações do modelo Gemini Flash, incluindo testes de regressão para verificar mudanças comportamentais e um plano de rollback para reverter a configurações anteriores do LLM ou a um modelo alternativo em caso de problemas.
*   **Monitoramento Contínuo**: O sistema de monitoramento incluirá métricas de latência, taxa de erro, volume de chamadas e uso de tokens da API do LLM, além da qualidade das respostas geradas (se possível, por meio de avaliações heurísticas ou humanas). Alertas serão configurados para desvios significativos.

## Exemplos de Interação com a API LLM

Esta seção fornece exemplos práticos de interação com a API do Gemini 2.0 Flash, ilustrando o formato esperado dos prompts de entrada e as respostas em diversos cenários, incluindo sucesso, falha e degradação.

*   **Exemplo 1: Prompt de Entrada (Validação de Oportunidade)**
    *   `JSON Request Body (para /v1beta/models/gemini-flash:generateContent)`:
        ```json
        {
          "contents": [
            {
              "parts": [
                {"text": "Analyze the following betting opportunity for value. Match: TeamA vs TeamB, League: Premier League, Date: 2025-05-20, Market: Over 2.5 Goals, MyOdds: 2.10, PinnacleOdds: 1.90. Determine if this is a valid value bet based on market efficiency. Output only 'VALID' or 'INVALID' and a brief justification. If uncertain, output 'INCONCLUSIVE'."}
              ]
            }
          ]
        }
        ```
*   **Exemplo 2: Resposta Esperada da IA (Sucesso)**
    *   `JSON Response Body (200 OK)`:
        ```json
        {
          "candidates": [
            {
              "content": {
                "parts": [
                  {"text": "VALID. Justification: MyOdds 2.10 > PinnacleOdds 1.90, positive EV detected."}
                ]
              }
            }
          ]
        }
        ```
*   **Exemplo 3: Resposta da IA (Alucinação/Resposta Inválida)**
    *   `JSON Response Body (200 OK, mas conteúdo problemático)`:
        ```json
        {
          "candidates": [
            {
              "content": {
                "parts": [
                  {"text": "Definitely a good bet. My cat told me so. Meow."}
                ]
              }
            }
          ]
        }
        ```
        *Comportamento do Sistema*: A lógica de validação de output do EdgeHunter classificaria esta resposta como inválida/alucinatória e faria fallback para o modo degradado.
*   **Exemplo 4: Falha da API do LLM (Comportamento do Sistema)**
    *   `HTTP Response`: `HTTP 500 Internal Server Error` ou `Connection refused`.
    *   *Comportamento do Sistema*: Aciona o Circuit Breaker, logs de erro, e fallback para a Estratégia de Failover definida.
*   **Exemplo 5: Resposta em Modo Degradado (Lógica Pura)**
    *   *Comportamento do Sistema*: Quando o LLM está em failover para lógica pura, a resposta interna gerada será: `INVALID. Justification: LLM service unavailable, fallback to deterministic rules resulted in conservative invalidation.`

## NFRs - Qualidade de Serviço (QoS) do LLM

Para garantir a qualidade do serviço fornecido pelo Gemini 2.0 Flash, serão definidos os seguintes Service Level Objectives (SLOs) e Service Level Indicators (SLIs):

*   **Latência**: P95 das requisições de inferência à API do Gemini Flash deve ser `menor que 1.5 segundos`.
*   **Taxa de Erro**: A taxa de erro (respostas HTTP 5xx ou erros de conexão) da API do Gemini Flash deve ser `inferior a 1%`.
*   **Taxa de Alucinação**: A taxa de respostas classificadas como 'alucinações' ou inconsistentes pela lógica de validação do EdgeHunter deve ser `inferior a 5%`.
*   **Taxa de Validação Correta**: A taxa de respostas 'VALID' ou 'INVALID' que são confirmadas como corretas pela validação manual ou por um baseline deve ser `superior a 90%`.
*   **Custo por Chamada**: O custo médio por chamada à API do LLM deve ser `inferior a USD 0.0001` (considerando o free tier e o uso previsto).
*   **Monitoramento**: Todas essas métricas serão monitoradas continuamente e alertas serão configurados para violações de SLOs/SLIs.

## NFRs - Recuperação de Desastres (DR) para LLM

Para garantir a resiliência contínua das funcionalidades dependentes de LLM, será implementada uma estratégia de failover automático:

*   **Avaliação de Fallback**: Em caso de degradação do Gemini Flash, o sistema avaliará automaticamente o fallback para:
    1.  Um **LLM Alternativo**: (ex: um modelo de IA local simplificado com menor acurácia, ou um modelo de outro provedor de LLM com maior custo).
    2.  **Lógica Determinística Pura**: Se nenhum LLM alternativo for viável, o sistema operará no modo puramente lógico, baseando-se em regras pré-definidas para as decisões.
*   **Gatilhos de Failover**: O failover será acionado por:
    *   Violação dos SLOs de **Latência** ou **Taxa de Erro** do Gemini Flash.
    *   Violação dos SLOs de **Taxa de Alucinação** ou **Taxa de Validação Correta**.
    *   Alertas de indisponibilidade do serviço Gemini Flash.
*   **Ordem de Fallback**: A prioridade de fallback será: **Gemini Flash (primário) -> LLM Alternativo (se configurado e viável) -> Lógica Determinística Pura**.
*   **Mecanismo de Retorno (Failback)**: O sistema monitorará continuamente o LLM alternativo e/ou a disponibilidade/qualidade do Gemini Flash. O retorno ao uso do Gemini Flash (failback) ocorrerá automaticamente quando suas métricas de SLO retornarem aos níveis aceitáveis por um período de 15 minutos e após validação de um conjunto de golden prompts.

## NFRs - Segurança da Interação com LLM

A segurança da comunicação e dos dados com o Gemini 2.0 Flash é fundamental.

*   **Criptografia em Trânsito**: Todas as comunicações com a API do Gemini Flash serão obrigatoriamente realizadas via **HTTPS (TLS 1.2+)**, garantindo a criptografia de ponta a ponta dos dados em trânsito e protegendo contra interceptação.
*   **Política de Retenção de Dados**: A política de retenção de dados da Google para o Gemini Flash será revisada e documentada. O EdgeHunter assumirá que nenhum dado enviado para o LLM deve ser considerado efêmero, e não se baseará em garantias de exclusão imediata.
*   **Tratamento de Dados Sensíveis**: **Informações de Identificação Pessoal (PII)**, dados financeiros ou quaisquer outras informações confidenciais do usuário ou do negócio **nunca** serão enviados ao Gemini Flash. Todos os prompts serão cuidadosamente construídos para conter apenas dados anonimizados e contextualizados que não permitam a inferência de informações sensíveis. Isso será garantido por validação e sanitização de inputs (conforme já documentado em 'Implicacões de Testabilidade e Confiabilidade').
*   **Gerenciamento de Segredos**: Conforme já documentado, as API Keys serão armazenadas em Secret Manager com rotação regular.

## NFRs - Monitorabilidade e Tracing Distribuído para LLM

Para garantir uma visibilidade profunda sobre a operação e as decisões envolvendo o LLM, será implementada uma estratégia de monitoramento e tracing distribuído:

*   **Correlation IDs**: Cada requisição que passar pelo fluxo de decisão híbrido, incluindo chamadas ao Gemini Flash, propagará um `Correlation ID` único. Este ID permitirá rastrear o ciclo de vida completo de uma oportunidade, desde a ingestão até a decisão final.
*   **Logs Estruturados**: Logs de eventos serão gerados em formato estruturado (JSON) em pontos chave da interação com o LLM:
    *   **Input Sanitizado**: O prompt de entrada, após sanitização e anonimização, será logado.
    *   **Output Validado**: A resposta crua do LLM e o resultado da validação interna do EdgeHunter serão logados.
    *   **Status da Chamada**: Sucesso, falha, latência, custo (em tokens ou USD) da chamada à API.
    *   **Eventos de Fallback**: Logs detalhados serão gerados quando o sistema realizar um fallback para um LLM alternativo ou lógica pura, incluindo o motivo do fallback e o impacto na decisão.
*   **Métricas de Tracing**: As métricas coletadas pelo "Monitoramento Contínuo" serão correlacionadas com os traces, permitindo análises de causa raiz mais rápidas em caso de anomalias de latência, erro ou qualidade.

## Pros and Cons of the Options

### Gemini 2.0 Flash

*   Good: Free tier generoso (2M tokens/mês), rápido (<3s), suficiente para tarefas de validação/anomalia/sugestão simples.
*   Bad: Pode ter qualidade menor que Pro/Claude em raciocínio complexo, necessidade de monitoramento da qualidade.

### Claude (Anthropic)

*   Good: Boa capacidade de raciocínio, forte em segurança e "helpful AI", custo competitivo.
*   Bad: Latência pode ser um pouco maior que Flash, free tier pode ser menos generoso ou ter limites diferentes.

### GPT-4 (OpenAI)

*   Good: Líder em capacidade de raciocínio e geração, alta performance em tarefas complexas.
*   Bad: Custo significativamente mais alto, latência pode ser maior que Flash, free tier muito limitado ou inexistente.

### Gemini Pro

*   Good: Melhor raciocínio que Flash, ainda da Google, boa integração.
*   Bad: Custo mais alto que Flash, latência potencialmente maior que Flash, free tier pode ser menor.

## Links

*   [PRD-04 (GeminiValidator) que referencia este ADR]
*   [ADR-003: Hybrid Logic + AI (Estratégia Híbrida) que referencia este ADR]
*   [Documentação do Gemini 2.0 Flash API]
