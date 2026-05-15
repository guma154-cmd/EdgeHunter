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
