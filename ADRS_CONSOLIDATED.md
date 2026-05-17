# 🏛️ EdgeHunter — ADRs Consolidadas (Completo)

**Data de consolidação**: 2026-05-17 03:41:46
**Total de ADRs**: 5
**Idioma**: PT-BR
**Status**: ✅ Todas aceitas e documentadas

---

## 📋 Índice Navegável

1. [ADR-001: Usar modelo Poisson Clássico](#adr-001-usar-modelo-poisson-clássico)
2. [ADR-002: Usar Pinnacle como Sharp Benchmark](#adr-002-usar-pinnacle-como-sharp-benchmark)
3. [ADR-003: Estratégia Híbrida (Lógica + IA)](#adr-003-estratégia-híbrida-lógica--ia)
4. [ADR-004: SQLite como Banco de Dados Principal](#adr-004-sqlite-como-banco-de-dados-principal)
5. [ADR-005: Gemini 2.0 Flash como LLM Principal](#adr-005-gemini-20-flash-como-llm-principal)

---

## 📊 Resumo Executivo (2 linhas por ADR)

**ADR-001**: Modelo Poisson Clássico. Justificativa: Padrão acadêmico, treino rápido com poucos dados, alta interpretabilidade. (Total: ~500 palavras)

**ADR-002**: Pinnacle como Sharp Benchmark. Justificativa: Referência da indústria para eficiência de mercado. Implicações robustas de resiliência. (Total: ~1200 palavras)

**ADR-003**: Estratégia Híbrida (Lógica + IA). Justificativa: Determinismo para apostas, IA ocasional (free tier) para validação e anomalias. (Total: ~800 palavras)

**ADR-004**: SQLite como Banco de Dados Principal. Justificativa: Zero setup, adequado para single-machine deploy e o volume inicial estimado. (Total: ~1300 palavras)

**ADR-005**: Gemini 2.0 Flash como LLM Principal. Justificativa: Free tier generoso, baixa latência (<3s), suficiente para tarefas designadas. (Total: ~1600 palavras)

---

## 🎯 Estatísticas Globais das ADRs

| Métrica | Valor |
|---------|-------|
| Total de ADRs | 5 |
| Total de palavras | ~5,400 |
| Idioma | 100% PT-BR |
| Status das Decisões | 100% Accepted |
| Agentes BMAD usados | @architect |

---

## ⚠️ IMPORTANTE: Validação

Antes de avançar, **verifique que todas as 5 ADRs aparecem** abaixo:
- [x] ADR-001 presente 
- [x] ADR-002 presente 
- [x] ADR-003 presente 
- [x] ADR-004 presente 
- [x] ADR-005 presente 

---

[AQUI COMEÇA O CONTEÚDO DAS 5 ADRs]

# ADR-001: Usar modelo Poisson Clássico

*   **Status**: Accepted
*   **Date**: 2025-05-15
*   **Deciders**: Rafael
*   **Consulted**: Claude, Gemini
*   **Informed**: -

## Context and Problem Statement

A escolha do modelo estatístico para prever resultados de futebol é crucial para a eficácia do sistema de value betting. Precisamos de um modelo que seja preciso o suficiente para identificar "valor", mas que também seja prático e interpretável, especialmente nas fases iniciais de operação com dados limitados.

## Decision Drivers

*   **Disponibilidade de Dados**: Baixo volume de jogos para treino inicial (<500).
*   **Acurácia**: Necessidade de acurácia razoável para identificar oportunidades de valor.
*   **Interpretabilidade**: Capacidade de entender como o modelo chega às suas previsões (ex: força de ataque/defesa).
*   **Custo Computacional**: Manter a complexidade computacional baixa para operação em tempo real.

## Considered Options

*   **Modelo Poisson Clássico**: Padrão acadêmico para futebol, baseado em distribuições de Poisson para gols marcados/sofridos.
*   **XGBoost/LightGBM**: Modelos de boosting de árvores, conhecidos pela alta performance e capacidade de lidar com dados complexos.
*   **Neural Networks**: Modelos de aprendizado profundo, capazes de encontrar padrões não lineares complexos.
*   **Random Forest**: Modelo de ensemble que combina múltiplas árvores de decisão.

## Decision Outcome

**Chosen option**: "Modelo Poisson Clássico"

**Justification**: O modelo Poisson é um padrão acadêmico bem estabelecido para previsão de resultados de futebol, conforme a abordagem de Dixon-Coles (1997). Ele oferece um bom equilíbrio entre interpretabilidade, baixo requisito de dados e performance razoável para o estágio inicial do projeto. Com menos de 500 jogos para treino, modelos mais complexos como XGBoost ou Redes Neurais podem sofrer de overfitting ou simplesmente não ter dados suficientes para aprender padrões significativos de forma robusta, sendo menos eficientes que o Poisson.

### Positive Consequences

*   **Treino Rápido**: O modelo pode ser treinado rapidamente, mesmo com poucos dados históricos.
*   **Baixo Requisito de Dados**: Funciona eficazmente com o volume limitado de jogos disponíveis inicialmente.
*   **Interpretabilidade**: Fácil de entender os parâmetros (força de ataque e defesa dos times), o que facilita a análise e ajustes.
*   **Justificativa Matemática**: Baseado em princípios estatísticos sólidos e amplamente aceitos para este domínio.

### Negative Consequences

*   **Potencial de Acurácia Inferior**: Pode ser inferior a modelos de Machine Learning mais modernos (XGBoost, Neural Networks) quando houver 1000+ jogos disponíveis para treino.
*   **Simplificação de Interações**: Não captura interações complexas entre variáveis ou dependências entre eventos (ex: gol de um time afetando a performance do outro).

## Pros and Cons of the Options

### Modelo Poisson Clássico

*   Good: Treino rápido, poucos dados necessários, interpretável (attack/defense), matematicamente justificado.
*   Bad: Pode ser inferior a ML moderno com 1000+ jogos, não captura interações complexas.

### XGBoost/LightGBM

*   Good: Alta acurácia potencial com grandes volumes de dados, lida bem com features heterogêneas.
*   Bad: Requer mais dados para um bom treino, menos interpretável que o Poisson, maior risco de overfitting com poucos dados.

### Neural Networks

*   Good: Capaz de aprender padrões complexos e não lineares, alta flexibilidade.
*   Bad: Caixa preta (baixa interpretabilidade), requer grandes volumes de dados, alto custo computacional para treino e inferência.

### Random Forest

*   Good: Boa acurácia, menos propenso a overfitting que o boosting em certos cenários, pode lidar com features categóricas.
*   Bad: Menos interpretável que o Poisson, pode exigir mais dados que o Poisson para ser superior.

## Links

*   [PRD-02 (PoissonModel) que referencia este ADR]
*   Dixon, M. J., & Coles, S. G. (1997). Modelling Association in Football with Goals Scored by Independent Poisson Variables. Journal of the Royal Statistical Society: Series C (Applied Statistics), 46(2), 265-283.


---

# ADR-002: Usar Pinnacle como Sharp Benchmark

*   **Status**: Accepted
*   **Date**: 2025-05-15
*   **Deciders**: Rafael
*   **Consulted**: Claude, Gemini
*   **Informed**: -

## Context and Problem Statement

Para validar a eficácia da detecção de "value" em apostas, precisamos de um benchmark confiável e eficiente. As odds oferecidas por diferentes casas de apostas variam significativamente devido às suas margens de lucro (overround) e à forma como ajustam suas linhas. Escolher o benchmark correto é fundamental para garantir que o sistema esteja comparando suas previsões com uma representação justa do "mercado eficiente".

## Decision Drivers

*   **Eficiência de Mercado**: Necessidade de um benchmark que reflita o mercado de apostas mais eficiente e informado.
*   **Acesso a Dados**: Capacidade de obter dados de odds do benchmark de forma consistente.
*   **Confiabilidade**: A fonte dos dados deve ser estável e com histórico de operações.
*   **Padrão da Indústria**: Preferência por um benchmark reconhecido e respeitado na indústria de apostas.

## Considered Options

*   **Pinnacle**: Casa de apostas reconhecida por ter uma das "linhas" mais afiadas (sharpest lines) e baixos overrounds.
*   **Bet365/Betano**: Casas de apostas populares com grandes volumes de mercado, mas com overrounds maiores.
*   **Mercado Consolidado (Média)**: Calcular a média das odds de múltiplas casas de apostas.
*   **Odds Iniciais de Abertura**: Usar as primeiras odds oferecidas por qualquer casa.

## Decision Outcome

**Chosen option**: "Pinnacle"

**Justification**: A Pinnacle é amplamente considerada a referência da indústria de apostas em termos de eficiência de mercado. Suas odds refletem, na maioria das vezes, o "true probability" do evento, ajustadas por um overround muito baixo (~2-3%). Comparar as odds do sistema com as da Pinnacle nos permite validar a detecção de valor contra a linha mais "afiada" disponível, essencial para um sistema de value betting. Além disso, a capacidade de fazer scraper de dados da Pinnacle já está funcional e provou ser confiável.

### Positive Consequences

*   **Referência da Indústria**: Comparação contra o benchmark mais respeitado, garantindo validação robusta.
*   **Dados Confiáveis**: O scraper existente para Pinnacle funciona bem, fornecendo dados consistentes.
*   **Menor Overround**: As baixas margens da Pinnacle tornam-na ideal para identificar o "true probability".
*   **Agilidade na Ajuste de Odds**: A Pinnacle ajusta suas odds rapidamente, refletindo novas informações de mercado quase em tempo real.

### Negative Consequences

*   **Slippage em Mercados Ilíquidos**: Para jogos menos populares, a liquidez pode ser menor, e as odds da Pinnacle podem não ser tão "sharp" quanto em mercados principais, podendo introduzir um pequeno "slippage".
*   **Dependência de Cobertura**: Nem todos os jogos (especialmente de ligas menores) têm cobertura na Pinnacle, exigindo potenciais fontes alternativas para esses casos.
*   **Dependência do Scraper**: A funcionalidade do sistema é diretamente atrelada à capacidade de manter o scraper da Pinnacle online e funcional.

## Implicações de Testabilidade e Confiabilidade

A decisão de usar a Pinnacle como benchmark introduz uma dependência crítica do scraper. Para garantir a testabilidade e a confiabilidade do sistema, as seguintes estratégias serão adotadas:

*   **Mocking do Scraper**: Para testes unitários e de integração do `ValueDetector` (PRD-03) e outros componentes dependentes, o scraper da Pinnacle será mockado. Isso permitirá simular diferentes cenários de odds (ex: odds muito altas/baixas, movimentos de linha específicos) sem depender da disponibilidade do serviço real.
*   **Geração de Dados de Teste**: Serão desenvolvidas ferramentas para gerar dados sintéticos de odds da Pinnacle, cobrindo cenários extremos e casos de borda que não seriam facilmente encontrados em dados históricos reais.
*   **Monitoramento do Scraper**: Serão implementadas métricas de saúde e desempenho do scraper (ex: taxa de sucesso, latência de aquisição de dados, frescor dos dados). Alertas serão configurados para anomalias.
*   **Tracing do Scraper**: As operações do scraper (requisições, respostas, erros de parsing) serão rastreadas para facilitar a depuração e otimização.
*   **Estratégia de Fallback/DR**: A dependência da Pinnacle será mitigada com uma estratégia clara de fallback para quando os dados não estiverem disponíveis ou forem inconsistentes. Isso pode incluir o uso temporário de outras casas de apostas ou a suspensão de alertas de valor para os jogos afetados.
*   **Considerações de Performance**: Testes de performance serão realizados no scraper para identificar e mitigar gargalos sob carga.
*   **Tratamento de Rate Limits**: A lógica do scraper incluirá mecanismos para lidar com rate limits impostos pela Pinnacle, evitando bloqueios e garantindo a continuidade da coleta de dados.

## NFRs - Disponibilidade e Resiliência

Para garantir a alta disponibilidade e a resiliência do sistema frente à dependência do scraper da Pinnacle, serão adotadas as seguintes medidas:

*   **1.1 Statelessness do Scraper**:
    *   O scraper da Pinnacle será projetado para ser fundamentalmente **stateless** em sua operação principal de coleta de odds, ou seja, cada requisição será independente e não dependerá de sessões ou estados anteriores. Qualquer gerenciamento de estado (ex: cookies de sessão para autenticação, rotação de User-Agents) será encapsulado e isolado por instância do scraper para evitar dependências entre requisições ou instâncias.
    *   **Limites de Concorrência e Volume**: Limites de concorrência serão impostos no cliente do scraper para evitar sobrecarga tanto na fonte externa quanto em nosso próprio serviço. O volume máximo aceitável de requisições será determinado por testes de carga (ver Considerações de Performance) e monitoramento contínuo das respostas da Pinnacle.
    *   **Estratégia de Escalabilidade**: A estratégia de escalabilidade incluirá o deploy de múltiplas instâncias do scraper, possivelmente com rotação de IPs e User-Agents para distribuir a carga e minimizar o risco de bloqueios.
*   **1.2 Circuit Breaker para o Scraper**:
    *   Um **Circuit Breaker** será implementado na camada de consumo dos dados do scraper.
    *   **Ativação**: Será ativado se 3 falhas consecutivas ou uma taxa de erro de 20% for detectada em um período de 60 segundos, ou se a latência média exceder 500 milissegundos.
    *   **Fallback**: Quando o circuito estiver aberto, o sistema fará um fallback imediato para dados em cache (se disponíveis e ainda válidos) ou para o modo degradado definido na Estratégia de Failover.
    *   **Retorno**: O circuito tentará "fechar" (half-open state) após 30 segundos para reavaliar a disponibilidade do scraper.
    *   **Logs e Métricas**: Logs de eventos do Circuit Breaker (abertura, fechamento, falhas) e métricas (estado do circuito, número de falhas) serão coletados e monitorados através do sistema de observabilidade.
*   **1.3 Estratégia de Failover e Failback**:
    *   Em caso de falha persistente do scraper da Pinnacle (identificada pelo Circuit Breaker e/ou monitoramento de dados), o sistema ativará um mecanismo de **failover automático** para fontes alternativas de odds.
    *   **Fontes Alternativas**: Inicialmente, será considerada a "Casa de Apostas B" (a ser definida) para ligas principais e/ou um "Modelo Interno de Estimativa" de odds para ligas menores.
    *   **Modo Degradado**: Durante o failover, o sistema operará em um modo degradado, que pode incluir a redução da precisão dos alertas de valor, a suspensão temporária de alertas para mercados de menor liquidez, ou a utilização de odds com overround ligeiramente maior.
    *   **Gatilhos**: Os gatilhos para o failover serão baseados em violações de SLA do scraper (ex: ausência de dados por mais de 5 minutos, erro de scraper por mais de 3 minutos).
    *   **Failback**: O retorno (failback) ao serviço principal da Pinnacle ocorrerá quando a fonte primária demonstrar estabilidade (ex: 99% de sucesso nas requisições) por um período de 15 minutos.
    *   **Logs e Métricas**: Logs e métricas detalhadas do processo de failover/failback (ex: tempo de transição, sucesso do failover, alertas gerados) serão coletados e monitorados.

## NFRs - Segurança

Para garantir a segurança da operação do scraper e dos dados coletados, serão implementadas as seguintes diretrizes:

*   **2.1 Autenticação e Gestão de Segredos**:
    *   Se o acesso ao endpoint da Pinnacle ou de fontes alternativas exigir autenticação (ex: via API keys, cookies de sessão, tokens), as credenciais serão armazenadas exclusivamente em um **Secret Manager** (ex: HashiCorp Vault, AWS Secrets Manager).
    *   As credenciais serão acessadas em tempo de execução, nunca hardcoded no código fonte, e o acesso ao Secret Manager será controlado por políticas de menor privilégio (Princípio do Least Privilege).
    *   Será implementada a rotação regular de credenciais para minimizar o risco em caso de vazamento.
*   **2.2 Criptografia em Trânsito**:
    *   Toda a comunicação do scraper com a Pinnacle (e qualquer outra fonte externa) será realizada exclusivamente via **HTTPS (TLS 1.2+)**, garantindo a criptografia dos dados em trânsito e protegendo contra interceptação, adulteração ou ataques Man-in-the-Middle.
*   **2.3 Validação e Sanitização de Inputs**:
    *   Qualquer dado configurável que o scraper utilize (ex: URLs de destino, parâmetros de busca, cabeçalhos de requisição, User-Agents) será rigorosamente validado e sanitizado na entrada para prevenir ataques de injeção (ex: Command Injection, XSS se o input for renderizado) e garantir que apenas dados esperados e seguros sejam processados.
*   **2.4 Proteção contra Bloqueios e Scraping Abusivo**:
    *   **Estratégias de Mitigação**: Serão implementadas estratégias ativas para mitigar bloqueios pela Pinnacle, incluindo rotação de IPs (se disponível via proxy), rotação e camuflagem de User-Agents, gerenciamento adaptativo de delays entre requisições, e, se necessário, mecanismos para lidar com CAPTCHAs de forma programática ou manual.
    *   **Alertas e Monitoramento**: Alertas serão configurados para detecção de bloqueios persistentes (ex: status code 403, 429) ou acessos suspeitos, permitindo uma resposta proativa para manter a funcionalidade do scraper e proteger nossa reputação.

### Pinnacle

*   Good: Referência da indústria (sharpest line), scraper existente e funcional, baixos overrounds.
*   Bad: Potencial slippage em mercados ilíquidos, nem todos os jogos têm cobertura, dependência contínua do scraper.

### Bet365/Betano

*   Good: Ampla cobertura de jogos, alta liquidez, fácil acesso a dados.
*   Bad: Overrounds significativamente maiores (5-7%), o que dificulta a identificação de "true value", as linhas podem ser menos efidas.

### Mercado Consolidado (Média)

*   Good: Reduz a dependência de uma única casa, pode suavizar anomalias de odds.
*   Bad: O "true probability" ainda seria obscurecido pelas margens combinadas, complexidade maior na agregação e normalização.

### Odds Iniciais de Abertura

*   Good: Representa o primeiro consenso do mercado, antes de grandes influências de apostas.
*   Bad: Pode não ser tão preciso quanto a linha final da Pinnacle, que incorpora mais informações, maior variabilidade entre casas.

## Links

*   [PRD-03 (ValueDetector) que referencia este ADR]
*   [Referência da indústria sobre sharp books e Pinnacle]


---

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


---

# ADR-004: SQLite como Banco de Dados Principal

*   **Status**: Accepted
*   **Date**: 2025-05-15
*   **Deciders**: Rafael
*   **Consulted**: Claude, Gemini
*   **Informed**: -

## Context and Problem Statement

A escolha do sistema de gerenciamento de banco de dados (SGBD) é fundamental para o desempenho, escalabilidade e facilidade de manutenção do sistema. Dado que o EdgeHunter atualmente opera em um ambiente de máquina única (`single-machine deploy`) e tem um volume de dados estimado que não exige alta concorrência inicialmente, precisamos decidir qual tecnologia de banco de dados melhor atende a essas restrições e objetivos.

## Decision Drivers

*   **Facilidade de Setup e Manutenção**: Minimizar o tempo e esforço para configurar e manter o banco de dados.
*   **Custo Operacional**: Evitar a necessidade de servidores de banco de dados dedicados e suas infraestruturas.
*   **Compatibilidade com Python**: Boa integração com o ecossistema Python, frameworks ORM e bibliotecas.
*   **Volume de Dados Esperado**: O volume inicial de dados (estimado em 100k snapshots/mês, ~50MB) não é massivo.
*   **Ambiente de Deploy**: Operação em `single-machine deploy`.

## Considered Options

*   **SQLite**: Banco de dados relacional embarcado, sem servidor, que armazena dados em um único arquivo.
*   **PostgreSQL**: SGBD relacional robusto e escalável, ideal para aplicações com alta concorrência e integridade de dados.
*   **MongoDB**: Banco de dados NoSQL baseado em documentos, flexível para dados não estruturados e escalabilidade horizontal.

## Decision Outcome

**Chosen option**: "SQLite"

**Justification**: A escolha pelo SQLite é justificada pela sua simplicidade e adequação ao ambiente atual do EdgeHunter. Como o sistema já utiliza SQLite e o deploy é em máquina única, a migração para outro SGBD introduziria complexidade desnecessária sem um benefício imediato claro. O volume de dados previsto é baixo, e a concorrência de escrita será limitada, o que minimiza os pontos fracos do SQLite. Ele oferece setup zero, funciona "out of the box", e tem excelente compatibilidade com Python, tornando-o a opção mais eficiente para o estágio atual.

### Positive Consequences

*   **Zero Setup**: Não requer instalação ou configuração de um servidor de banco de dados separado.
*   **Embarcado**: O banco de dados é um arquivo único, fácil de mover e fazer backup.
*   **Compatibilidade com Python**: Alta compatibilidade com bibliotecas Python (ex: `sqlite3`) e ORMs.
*   **Funciona Out of the Box**: Reduz a complexidade de deploy e inicialização do sistema.
*   **Redução de Custos**: Evita custos de infraestrutura e manutenção associados a servidores de banco de dados dedicados.

### Negative Consequences

*   **Limites de Escrita Concorrente**: Pode apresentar gargalos de desempenho em cenários de alta concorrência de escrita, devido ao bloqueio de nível de arquivo.
*   **Não Escala Horizontalmente**: Não é adequado para arquiteturas distribuídas ou que necessitem de replicação e sharding para alta disponibilidade.
*   **Menos Ferramentas de Gerenciamento**: Comparado a PostgreSQL, possui um ecossistema de ferramentas de monitoramento e gerenciamento menos maduro.

## Implicações de Testabilidade e Confiabilidade

A escolha do SQLite, embora prática para o estágio inicial, exige atenção a certas implicações para testabilidade e confiabilidade:

*   **Testes de Performance e Concorrência**: Serão realizados testes de desempenho no SQLite sob cargas de leitura e escrita simuladas (próximas ao volume de 100k snapshots/mês e ligeiramente superiores) para identificar e testar os "Limites de Escrita Concorrente". Mitigações (ex: otimização de queries, indexação) serão aplicadas se gargalos forem encontrados.
*   **Definição de SLAs para DB**: Serão definidos SLAs explícitos para as operações de leitura e escrita no banco de dados, com metas de latência sob carga. Testes automatizados verificarão a conformidade com esses SLAs.
*   **Estratégia de Backup e Recuperação (DR)**:
    *   **RTO/RPO**: Serão definidos RTO (Recovery Time Objective) e RPO (Recovery Point Objective) específicos para a recuperação do arquivo SQLite.
    *   **Teste de Integridade de Backup**: Backups automáticos do arquivo `.db` serão implementados e sua integridade será testada regularmente por meio de restaurações automatizadas em ambientes de teste.
    *   **Ausência de Failover Nativo**: A limitação de não escalabilidade horizontal e ausência de failover nativo será documentada como um risco aceito para a fase atual.
*   **Segurança da Criptografia**: Será avaliada a necessidade de criptografia para o arquivo SQLite em repouso, e implementada se considerada um risco de segurança.
*   **Monitoramento e Tracing a Nível de Aplicação**: Para compensar a maturidade limitada das ferramentas de monitoramento nativas do SQLite, serão desenvolvidos mecanismos de tracing e métricas a nível de aplicação (ex: tempo de execução de queries, contagem de transações) para fornecer visibilidade operacional.
*   **Estratégia de Atualização e Rollback**:
    *   **Atualização**: Para atualizações de schema que não permitem zero-downtime, será planejada uma janela de manutenção.
    *   **Rollback**: Um plano claro de rollback será estabelecido para casos de corrupção do banco de dados ou falhas em migrações, tipicamente envolvendo a substituição do arquivo `.db` por uma versão de backup.
*   **Gatilho de Reavaliação**: Será claramente definido que ao atingir 1M+ snapshots/mês ou 10+ scrapers concorrentes (ou detecção de gargalos de concorrência nos testes de performance/monitoramento), uma reavaliação para migrar para PostgreSQL será disparada.

## Exemplos de Operações de Banco de Dados

Esta seção fornece exemplos práticos de como interagir com o banco de dados SQLite, ilustrando operações CRUD (Create, Read, Update, Delete) e gerenciamento. Os exemplos são representativos das interações via camada de persistência (ORM/SQL direto).

*   **Exemplo 1: Inserção de um Registro (CREATE)**
    *   `SQL: INSERT INTO odds_snapshot (match_id, bookie_id, odds_home, odds_draw, odds_away, timestamp) VALUES ('match123', 'pinnacle', 2.10, 3.20, 3.50, '2025-05-20T10:00:00Z');`
    *   `ORM (ex: SQLAlchemy): OddsSnapshot.create(match_id='match123', bookie_id='pinnacle', ...)`
*   **Exemplo 2: Consulta de Registros (READ)**
    *   `SQL: SELECT * FROM odds_snapshot WHERE match_id = 'match123' ORDER BY timestamp DESC LIMIT 1;`
    *   `ORM: OddsSnapshot.query.filter_by(match_id='match123').order_by(desc(OddsSnapshot.timestamp)).first()`
*   **Exemplo 3: Atualização de um Registro (UPDATE)**
    *   `SQL: UPDATE config SET value = 'new_value' WHERE key = 'feature_x_enabled';`
    *   `ORM: Config.update(key='feature_x_enabled', value='new_value')`
*   **Exemplo 4: Operação de Backup**
    *   `Shell: sqlite3 database.db ".backup 'database_backup_$(date +%Y%m%d%H%M%S).db'"`
*   **Exemplo 5: Restaurar Backup**
    *   `Shell: sqlite3 database.db ".restore 'database_backup_yyyyMMddHHmmss.db'"`
*   **Exemplo 6: Execução de Migração de Schema**
    *   `Shell (Alembic): alembic upgrade head`

## NFRs - Concorrência e Escalabilidade

Apesar do SQLite ser adequado para o ambiente de máquina única, é fundamental gerenciar suas limitações de concorrência de escrita.

*   **Limite de Concorrência Aceitável**: Será estabelecido um limite máximo de `5 transações de escrita concorrentes por segundo` no banco de dados SQLite. Este limite é uma estimativa inicial e será validado e ajustado através de testes de carga e monitoramento em ambiente de staging.
*   **Métricas de Monitoramento**: Serão implementadas métricas para monitorar a performance do banco de dados, incluindo:
    *   Tempo de bloqueio (`sqlite_lock_time_ms`).
    *   Latência média de escrita.
    *   Taxa de erros de escrita por segundo.
    *   Número de transações de escrita por segundo.
*   **Gatilho Objetivo para Migração**: Uma reavaliação da arquitetura de persistência e uma migração para PostgreSQL serão desencadeadas se qualquer uma das seguintes condições for atingida e persistir por mais de 10 minutos:
    *   `Mais de 5 transações de escrita por segundo`.
    *   `Mais de 2 usuários simultâneos realizando operações de escrita`.
    *   `Latência média de escrita consistentemente superior a 50 milissegundos`.

## NFRs - Recuperação de Desastres (DR)

A ausência de failover nativo no SQLite é um **risco aceito** para a fase atual do projeto, dada a complexidade de implementar redundância ativa para um DB de arquivo único e a natureza inicialmente de máquina única do EdgeHunter. No entanto, uma estratégia robusta de backup e recuperação será mantida.

*   **RTO (Recovery Time Objective)**: O RTO para o banco de dados SQLite será de **4 horas**.
*   **RPO (Recovery Point Objective)**: O RPO será de **1 hora** (garantindo que a perda máxima de dados seja de 1 hora).
*   **Processo de Recuperação Manual**: Em caso de corrupção ou perda do arquivo `database.db`, o processo de recuperação manual incluirá:
    1.  Detecção da falha via monitoramento de health checks do DB.
    2.  Parada imediata do serviço EdgeHunter.
    3.  Restaurar o último backup íntegro do arquivo `.db` para o local de operação.
    4.  Reiniciar o serviço EdgeHunter.
    5.  Realizar validações de integridade pós-restauração.
*   **Teste de Restauração de Backup**: Testes de restauração de backup serão realizados **trimestralmente** em um ambiente de não-produção para validar a integridade dos backups e a eficácia do processo de recuperação.

## NFRs - Deployability e Manutenção

Atualizações de schema do SQLite serão gerenciadas com o objetivo de minimizar o downtime, embora a natureza do banco de dados possa exigir janelas de manutenção para mudanças mais complexas.

*   **Processo de Alteração de Schema**: As alterações de schema serão aplicadas usando uma ferramenta de migração de banco de dados (ex: Alembic para Python). Os scripts de migração serão versionados e testados em ambientes de staging.
*   **Janelas de Manutenção**: Para migrações de schema que introduzem mudanças incompatíveis ou que exigem bloqueios de tabela prolongados, será definida uma **janela de manutenção de 10 minutos** a ser agendada em horários de baixo tráfego. Esforços serão feitos para projetar migrações que permitam a compatibilidade backward (N-1) sempre que possível.
*   **Plano de Rollback**: Todo processo de migração de schema terá um plano de rollback associado. Em caso de falha na migração ou problemas pós-deploy, o plano de rollback incluirá a restauração do backup do banco de dados (conforme o RPO definido) e/ou a execução de scripts de downgrade de schema.
*   **Comunicação**: Em caso de downtime planejado, uma comunicação prévia será enviada aos usuários (se aplicável) e sistemas dependentes com `24 horas` de antecedência, detalhando a duração esperada e o impacto.

## Pros and Cons of the Options

### SQLite

*   Good: Zero setup, embarcado (arquivo único), alta compatibilidade com Python, baixo custo operacional, ideal para single-machine deploy.
*   Bad: Limites em escrita concorrente, não escala horizontalmente, menos ferramentas de gerenciamento.

### PostgreSQL

*   Good: Robusto, escalável, alta integridade de dados, concorrência otimizada, vasto ecossistema de ferramentas.
*   Bad: Requer instalação e manutenção de servidor, maior complexidade de setup e operação para um ambiente single-machine.

### MongoDB

*   Good: Flexibilidade de schema (NoSQL), escalabilidade horizontal nativa, bom para dados não estruturados.
*   Bad: Curva de aprendizado para quem está acostumado com SQL, maior overhead de setup, menos adequado para dados estritamente relacionais como histórico de apostas.

## Links

*   [PRD-01 (OddsHistorian) que referencia este ADR]
*   [Seção 5.1 Schema de Banco de Dados do PRD-05]
*   [Referência sobre limites de concorrência em SQLite]


---

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


---

## ✅ Fim da Consolidação

**Total de seções**: 5
**Checksum**: 4d6b117f98708880ad17e20215444ed4d5567b056ad6c3aaa94aae8454e1b85e
**Validado em**: 2026-05-17 03:41:46
