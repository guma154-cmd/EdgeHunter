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
