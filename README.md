# EdgeHunter - Algorithmic Sports Trading Bot (PAUSED)

## Status do Projeto
**PAUSADO.** O desenvolvimento atingiu um gargalo físico e geopolítico (Junho de 2026). A transição de Value Betting estático para High-Frequency Trading (Scalping) na Betfair esbarrou no bloqueio de IP da API institucional para residentes no Brasil (Erro 403) e na latência transatlântica (~200ms), que inviabiliza execuções em tempo real.

O projeto aguarda o provisionamento de uma VPS em Londres/Frankfurt e a abertura de conta em um Betting Broker (ex: Asianconnect/Orbit Exchange) para retomar os testes.

## Arquitetura Construída até o Congelamento
1. **Motor Quantitativo (ValueDetector):** Algoritmo capaz de expurgar a margem de lucro (juice) de corretoras Sharp (Pinnacle), calcular a *True Probability* e definir o tamanho da entrada usando o Critério de Kelly.
2. **Orquestrador Assíncrono:** Sistema desenhado para varredura de mercado sem travar o Event Loop do Python.
3. **Árbitro de CLV (Closing Line Value):** Sistema de auditoria que captura a odd de fechamento para provar a validade matemática (Edge real) da estratégia a longo prazo.
4. **Séries Temporais (PostgreSQL):** Modelagem de banco de dados (`odds_time_series`) com índices B-Tree para armazenar o filme do mercado (Steam Chasing) e alimentar futuros modelos preditivos de Machine Learning.
5. **Mocking Offline:** Infraestrutura de testes isolada para ler payloads estáticos e poupar cotas de API.

## Próximos Passos (Retomada)
- Provisionar servidor offshore (Europa).
- Obter App Key da Betfair via Broker.
- Implementar biblioteca `flumine` para conexão via WebSockets e leitura de Order Book.
- Substituir regressão/busca simples por Reinforcement Learning focado em micro-flutuações (Ticks).
