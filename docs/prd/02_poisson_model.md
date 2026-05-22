# PRD-02: Modelo de Poisson

| Metadados | Valor |
|---|---|
| **ID** | PRD-02 |
| **Status** | Accepted |
| **Responsável** | John (PM) |
| **Pai** | [PRD-00: Pivot de Value Betting](./00_master_value_betting.md) |
| **Criado em** | 2026-05-15 |

---

## 1. Declaração do Problema

Para identificar "apostas de valor" (value bets), precisamos comparar as odds oferecidas pelas casas de apostas com uma avaliação independente e objetiva das probabilidades de resultado da partida (vitória do time da casa, empate, vitória do time visitante). As odds das casas de apostas incluem sua própria margem de lucro e podem ser influenciadas pelo sentimento do mercado, não apenas pela probabilidade estatística pura.

O modelo de distribuição de Poisson é um método estatístico bem estabelecido para modelar placares de futebol. Ao estimar a força ofensiva e defensiva de cada equipe com base nos resultados históricos, podemos gerar as probabilidades objetivas necessárias para servir como nosso benchmark.

---

## 2. Metas

- **Precisão**: Atingir uma precisão de previsão superior a 65% em backtests para o Brasileirão Série A e a Premier League.
- **Performance**:
    - O tempo de treinamento deve ser inferior a 30 segundos para um conjunto de dados de 500 partidas.
    - A latência de previsão deve ser inferior a 10ms por partida.
- **Automação**: O modelo deve ser retreinado automaticamente diariamente, usando os dados mais recentes do módulo OddsHistorian.

---

## 3. Não-Metas

- **Modelos de Ensemble**: Não implementaremos modelos de ensemble (por exemplo, empilhar Poisson com outros modelos) nesta fase. Isso pode ser considerado para futuras iterações.
- **Conjunto de Recursos Estendido**: O modelo usará *apenas* as identidades das equipes e os placares finais. Recursos como clima, lesões de jogadores ou formações específicas estão fora do escopo desta versão.
- **Contagem Específica de Gols**: A saída principal do modelo são as probabilidades 1x2 (vitória/empate/derrota). Ele não será usado para prever o número exato de gols ou outros mercados relacionados (por exemplo, Mais/Menos gols).

---

## 4. Histórias de Usuário

- [ ] **STORY-02-001**: Implementar algoritmo do modelo de Poisson usando Estimativa de Máxima Verossimilhança (MLE).
  - **Status**: a fazer | **Estimativa**: 6h
  - **Critério de Aceitação**: A função `scipy.optimize` converge com sucesso e retorna os parâmetros de força das equipes. As probabilidades calculadas para qualquer partida somam 1.0 (±0.001).

- [ ] **STORY-02-002**: Treinar o modelo usando dados históricos do OddsHistorian.
  - **Status**: a fazer | **Estimativa**: 3h
  - **Critério de Aceitação**:
    - O modelo consome corretamente os dados de `historian.get_finished_matches_with_last_odds(valid_only=True)`.
    - Um aviso é registrado se mais de 20% dos snapshots históricos disponíveis forem marcados como inválidos (`valid_for_analysis = False`), indicando um possível problema de sincronia de dados.
    - Partidas sem um snapshot válido são ignoradas e não usadas no treinamento.

- [ ] **STORY-02-003**: Implementar salvamento e carregamento dos pesos do modelo.
  - **Status**: a fazer | **Estimativa**: 2h
  - **Critério de Aceitação**: Os pesos do modelo (parâmetros de ataque/defesa) podem ser salvos em um arquivo JSON com timestamp e carregados de volta, com um teste de ida e volta que preserve os valores.

- [ ] **STORY-02-004**: Implementar a função de previsão para probabilidades 1x2.
  - **Status**: a fazer | **Estimativa**: 3h
  - **Critério de Aceitação**: O método `predict_probabilities` retorna um dicionário `{'home_win': P, 'draw': P, 'away_win': P}` onde as probabilidades somam 1.0 (±0.001).

- [ ] **STORY-02-005**: Implementar avaliação do modelo e backtesting.
  - **Status**: a fazer | **Estimativa**: 4h
  - **Critério de Aceitação**: Uma função de avaliação calcula e retorna métricas chave: precisão (accuracy), log_loss e Brier score.

- [ ] **STORY-02-006**: Integrar o retreinamento do modelo ao agendador diário (scheduler).
  - **Status**: a fazer | **Estimativa**: 2h
  - **Critério de Aceitação**: A tarefa de retreinamento é agendada com sucesso para rodar diariamente às 04:00 UTC. O status de execução e os logs são registrados no banco de dados.

- [ ] **STORY-02-007**: Criar testes unitários e de integração para o modelo de Poisson.
  - **Status**: a fazer | **Estimativa**: 5h
  - **Critério de Aceitação**:
    - A cobertura de testes para o módulo excede 80%.
    - **Testes adversariais passam:**
        - `test_team_not_seen_in_training()`: Lida com novas equipes graciosamente usando a força média da liga, evitando crashes.
        - `test_extreme_team_strength_disparity()`: Prevê corretamente alta probabilidade de vitória (>70%) para uma equipe de ponta contra uma equipe de baixo nível em casa.
        - `test_probabilities_sum_validation()`: Garante que as probabilidades sempre somam 1.0 ± 0.001.
        - `test_convergence_with_minimal_data()`: Confirma que o algoritmo de otimização converge mesmo com o mínimo de dados exigidos (30 partidas por liga).
        - `test_handle_team_name_variations()`: Mapeia corretamente variações de nomes (por exemplo, 'São Paulo FC', 'S. Paulo') para a mesma entidade usando o `match_id` determinístico.
        - `test_zero_goal_handling()`: O cálculo da PMF de Poisson não falha ao lidar com partidas 0-0 (evita erros de `log(0)`).

- [ ] **STORY-02-008**: Implementar uma verificação de sanidade (sanity check) pré-implantação para o modelo treinado.
  - **Status**: a fazer | **Estimativa**: 3h | **Prioridade**: alta
  - **Critério de Aceitação**:
    - Um método `sanity_check()` é executado automaticamente após cada rodada de treinamento.
    - A verificação testa:
        1. A precisão (accuracy) é > 55% em um conjunto de validação (hold-out) (últimos 20% das partidas).
        2. As probabilidades somam 1.0 para 100 confrontos aleatórios gerados.
        3. A probabilidade de vitória prevista de uma equipe de ponta contra uma equipe de baixo nível é > 0.5.
        4. Convergência da otimização: `scipy.optimize.minimize` retornou `result.success == True` no último treinamento (caso contrário, modelo é descartado e mantém-se versão anterior).
    - Se a verificação de sanidade falhar, a flag `model.trained` é definida como `False`, um alerta do Telegram é enviado e o modelo ativo anteriormente é mantido.

---

## 5. Especificação Técnica

### 5.1 Algoritmo: MLE de Poisson

O cerne do modelo baseia-se na Estimativa de Máxima Verossimilhança para encontrar os parâmetros ideais de ataque e defesa para cada equipe.

Para cada partida no conjunto de dados de treinamento, calculamos o número esperado de gols (lambda) para as equipes da casa e visitante:
` + "`" + `` + "`" + `` + "`" + `
lambda_casa = forca_ataque[equipe_casa] * forca_defesa[equipe_visitante] * vantagem_casa
lambda_visitante = forca_ataque[equipe_visitante] * forca_defesa[equipe_casa]
` + "`" + `` + "`" + `` + "`" + `
A log-verossimilhança negativa (NLL) é então calculada como a soma dos logs negativos da função de massa de probabilidade (PMF) de Poisson para os gols reais marcados:
` + "`" + `` + "`" + `` + "`" + `
nll = 0
para partida em dados_treinamento:
    # calcular lambda_casa, lambda_visitante
    nll += -log(pmf_poisson(gols_casa_reais, lambda_casa))
    nll += -log(pmf_poisson(gols_visitante_reais, lambda_visitante))
` + "`" + `` + "`" + `` + "`" + `
Usamos `scipy.optimize.minimize(method='BFGS')` para encontrar os parâmetros `forca_ataque` e `forca_defesa` que minimizam a NLL. O treinamento é realizado independentemente para cada liga para evitar a diluição do sinal.

### 5.2 Contrato da API

A funcionalidade será encapsulada em uma classe `PoissonModel`.

` + "`" + `` + "`" + `` + "`" + `python
class PoissonModel:
    def __init__(self, league: str, min_training_matches: int = 30):
        # ...

    def train(self) -> bool:
        """Treina o modelo com dados históricos. Retorna True em caso de sucesso."""
        # ...

    def load_weights(self) -> bool:
        """Carrega pesos pré-treinados de um arquivo. Retorna True em caso de sucesso."""
        # ...

    def predict_probabilities(self, home_team: str, away_team: str) -> dict[str, float]:
        """Prevê probabilidades 1x2 para uma dada partida."""
        # ...

    def evaluate_accuracy(self, days_back: int) -> dict[str, float]:
        """Executa um backtest e retorna métricas de performance."""
        # ...
` + "`" + `` + "`" + `` + "`" + `

### 5.3 Armazenamento

- **Pesos do Modelo**: `backend/models/poisson_weights_{nome_da_liga}.json`
  - Ex: `poisson_weights_brasileirao.json`
- **Metadados do Modelo**: `backend/models/poisson_metadata_{nome_da_liga}.json`
  - Armazena a data de treinamento, o número de partidas usadas e as principais métricas de precisão da última execução.

### 5.4 Requisitos de Performance

- **Treinamento**: < 30 segundos para 500 partidas por liga.
- **Previsão**: < 10ms (latência p95).
- **Memória**: < 100MB de uso de memória durante o processo de treinamento.

---

## 6. Critérios de Aceitação

- [ ] Todas as histórias de usuário (STORY-02-001 a STORY-02-008) estão implementadas e cumprem seus critérios de aceitação.
- [ ] O back-testing no conjunto de dados do Brasileirão confirma uma precisão preditiva superior a 65%.
- [ ] O algoritmo de otimização converge com sucesso em >95% das execuções de treinamento com dados válidos.
- [ ] A lógica matemática, incluindo a estimativa de parâmetros e o cálculo de probabilidades, está documentada com comentários inline no código.

---

## 7. Dependências

- **Upstream**: [PRD-01 OddsHistorian](./01_odds_historian.md) - Este módulo é a única fonte de dados para treinar o modelo de Poisson.
- **Downstream**: [PRD-03 ValueDetector](./03_value_detector.md) - Este módulo consumirá as probabilidades geradas pelo modelo de Poisson para calcular o Valor Esperado (EV).

---

## 8. Decisões

### 8.1 Decisões Aceitas
- A vantagem de mando de campo será modelada como parâmetro global único na v1.
- Para equipes com poucas partidas históricas (incluindo recém-promovidas), usar fallback para prior médio da liga e marcar a previsão com menor confiança operacional.

Justificativa técnica: estas decisões afetam diretamente o contrato matemático inicial do modelo e o comportamento default das previsões, então não poderiam ser deixadas em aberto. Sem esse fechamento, a implementação do treino e inferência ficaria indeterminada sobre quantos parâmetros estimar e como tratar dados esparsos.

O parâmetro global único de mando reduz variância e complexidade na v1, o que é mais compatível com a base inicial esperada. Para equipes com pouco histórico, usar prior médio da liga evita extrapolações frágeis e cria um comportamento previsível para o sistema: produzir saída conservadora, mas sem quebrar o pipeline ou inventar força estatística inexistente.

### 8.2 Decisões Deferidas
- Decadência temporal no treinamento: adiada; default v1 com peso uniforme para o histórico.

As decisões deferidas estão consolidadas em [`docs/decisions/deferred_decisions.md`](../decisions/deferred_decisions.md).

---

## 9. Referências

- **Interna**: [ADR-001: Escolha Inicial do Modelo (Poisson vs. ML)](../architecture/adr_001_poisson_choice.md)
- **Acadêmica**: Dixon, M. J., & Coles, S. G. (1997). "Modelling Association Football Scores and Inefficiencies in the Football Betting Market."
- **Técnica**: Documentação do `scipy.optimize.minimize`.
