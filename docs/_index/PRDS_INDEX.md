# PRDS_INDEX

> ⚠️ ARQUIVO AUTO-GERADO - NAO EDITAR MANUALMENTE
> Gerado por: python scripts/generate_index.py
> Fonte primaria: ver docs/prd/*.md e docs/architecture/*.md
> Ultima geracao: 2026-06-02 09:47 UTC

Total de documentos: 6

## Sumario

1. `Master PRD: EdgeHunter Value Betting Pivot` - `Accepted` - `docs/prd/00_master_value_betting.md`
2. `PRD-01: OddsHistorian v2` - `Accepted` - `docs/prd/01_odds_historian.md`
3. `PRD-02: Modelo de Poisson` - `Accepted` - `docs/prd/02_poisson_model.md`
4. `PRD-03: Value Detector` - `Accepted` - `docs/prd/03_value_detector.md`
5. `PRD-04: Gemini Validator` - `Accepted` - `docs/prd/04_gemini_validator.md`
6. `PRD-05: AutoEvolution` - `Accepted` - `docs/prd/05_auto_evolution.md`

---

## Master PRD: EdgeHunter Value Betting Pivot

- Fonte: `docs/prd/00_master_value_betting.md`
- Status: `Accepted`
- Metadados:
  - PRD ID: PRD-00
  - Status: Accepted
  - Aceito em: 2026-05-23
  - Owner: Rafael
  - Created Date: 2026-05-14
  - Version: 1.0.0
  - Last Updated: 2026-05-14

### Resumo

Este documento detalha o pivô estratégico do projeto EdgeHunter, passando da detecção de surebets (arbitragem) para a identificação de *Value Bets* (odds subavaliadas). O objetivo é construir um sistema sustentável e escalável combinando um core estatístico com uma camada de inteligência artificial (Gemini) para identificar apostas com valor esperado positivo (EV) de forma autônoma. O sucesso principal é medido pela capacidade de gerar um ROI consistente a longo prazo usando uma banca inicial controlada.
Atualmente, o modelo de surebets enfrenta desafios significativos que limitam o crescimento e a escalabilidade:
Abaixo a representação da arquitetura macro, detalhando o fluxo desde a extração até o alerta:

---

## PRD-01: OddsHistorian v2

- Fonte: `docs/prd/01_odds_historian.md`
- Status: `Accepted`
- Metadados:
  - ID: PRD-01
  - Status: Accepted
  - Aceito em: 2026-05-23
  - Owner: Rafael
  - Parent: PRD-00
  - Created: 2026-05-14
  - Depends on: ADR-004 (SQLite), Utility `app/utils/match_id.py`

### Resumo

Os scrapers existentes coletam odds a cada 15min, mas **SOBRESCREVEM** os dados temporais (overwrite a cada ciclo). Para o Value Betting, precisamos de:
A solução será atuar como um *wrapper* sobre os scrapers existentes + utility `match_id` + validation layer + health monitoring, evitando alterar os scrapers base.
Modificar `backend/app/data/scheduler.py`:

---

## PRD-02: Modelo de Poisson

- Fonte: `docs/prd/02_poisson_model.md`
- Status: `Accepted`
- Metadados:
  - ID: PRD-02
  - Status: Accepted
  - Aceito em: 2026-05-23
  - Responsável: John (PM)
  - Pai: [PRD-00: Pivot de Value Betting](/docs/prd/00_master_value_betting.md)
  - Criado em: 2026-05-15

### Resumo

Para identificar "apostas de valor" (value bets), precisamos comparar as odds oferecidas pelas casas de apostas com uma avaliação independente e objetiva das probabilidades de resultado da partida (vitória do time da casa, empate, vitória do time visitante). As odds das casas de apostas incluem sua própria margem de lucro e podem ser influenciadas pelo sentimento do mercado, não apenas pela probabilidade estatística pura.
O modelo de distribuição de Poisson é um método estatístico bem estabelecido para modelar placares de futebol. Ao estimar a força ofensiva e defensiva de cada equipe com base nos resultados históricos, podemos gerar as probabilidades objetivas necessárias para servir como nosso benchmark.
O cerne do modelo baseia-se na Estimativa de Máxima Verossimilhança para encontrar os parâmetros ideais de ataque e defesa para cada equipe.

---

## PRD-03: Value Detector

- Fonte: `docs/prd/03_value_detector.md`
- Status: `Accepted`
- Metadados:
  - ID: PRD-03
  - Status: Accepted
  - Aceito em: 2026-05-23
  - Responsável: John (PM)
  - Pai: [PRD-00: Pivot de Value Betting](/docs/prd/00_master_value_betting.md)
  - Criado em: 15/05/2026

### Resumo

Os bookmakers embutem uma margem de lucro (overround ~5-7% em casas "soft", ~2-3% na Pinnacle). Quando a Bet365 ou a Betano oferecem odds maiores que a "verdade" do mercado (representada pela Pinnacle) ou maiores que a nossa estimativa independente (PoissonModel), há **valor** — uma expectativa matemática positiva de lucro no longo prazo.
O `ValueDetector` é o coração analítico do pivô para Value Betting do EdgeHunter. Sem ele, todos os outros módulos (coleta de dados, modelagem) são apenas infraestrutura sem aplicação prática.
Justificativa técnica: esta decisão afeta comportamento default observável da detecção e precisava ser resolvida agora porque muda o contrato da função de avaliação. Sem benchmark da Pinnacle, o sistema teria de escolher entre bloquear, estimar um proxy ou emitir oportunidade com base incompleta; isso altera tanto risco operacional quanto a interpretação do usuário sobre o significado do alerta.

---

## PRD-04: Gemini Validator

- Fonte: `docs/prd/04_gemini_validator.md`
- Status: `Accepted`
- Metadados:
  - ID: PRD-04
  - Status: Accepted
  - Aceito em: 2026-05-23
  - Responsável: John (PM)
  - Pai: [PRD-00: Pivot de Value Betting](/docs/prd/00_master_value_betting.md)
  - Criado em: 15/05/2026

### Resumo

Os módulos analíticos do EdgeHunter (PRD-02 e PRD-03) são determinísticos e estatísticos — excelentes para a maioria dos casos, mas podem ter **pontos cegos**:
O `GeminiValidator` atua como um **revisor inteligente**, focado nos cenários de maior risco/recompensa. Ele complementa a lógica existente, fornecendo validação contextual e insights estratégicos, sem onerar o orçamento (o free tier do Gemini é suficiente para o uso planejado).
Acurácia últimos 7 dias: {accuracy_7d:.1f}% ROI últimos 30 dias: {roi_30d:.2f}%

---

## PRD-05: AutoEvolution

- Fonte: `docs/prd/05_auto_evolution.md`
- Status: `Accepted`
- Metadados:
  - ID: PRD-05
  - Status: Accepted
  - Aceito em: 2026-05-23
  - Responsável: John (PM)
  - Pai: [PRD-00: Pivot de Value Betting](/docs/prd/00_master_value_betting.md)
  - Criado em: 15/05/2026

### Resumo

Os módulos anteriores (PRD-01 a 04) constituem a **infraestrutura analítica** do sistema — eles coletam dados, calculam probabilidades, detectam valor e validam com IA. No entanto, sem um **engine operacional** que tome decisões financeiras concretas e gerencie o ciclo de vida do sistema, essa infraestrutura permanece inerte, sem gerar resultados práticos.
O `AutoEvolution` preenche essa lacuna, atuando como o maestro da orquestra:
Sem este módulo, o sistema gera insights, mas não possui a governança operacional para transformá-los em um processo de investimento estruturado e auto-otimizado.
