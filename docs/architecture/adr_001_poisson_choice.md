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
