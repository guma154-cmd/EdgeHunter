# Histórico Oficial de Releases — EdgeHunter

Este documento registra o histórico oficial de versões, tags e ondas de entrega do EdgeHunter.

> Qualquer divergência entre o nome lógico esperado e o nome real da tag no repositório é registrada na coluna **Observação**, sem impacto no estado final validado.

---

## Tabela de Releases

| Tag | Commit (curto) | Onda | Entrega Principal | Status | Observação |
|-----|----------------|------|-------------------|--------|------------|
| `v0.1-freeze` | `cc20643` | — | Freeze inicial da estrutura do projeto | APPLIED | — |
| `v0.2-corrected` | `b2399e4` | — | Correções críticas da auditoria v0.2 | APPLIED | — |
| `v0.2-onda1-fundacao-dados` | `14b5f0a` | Onda 1 | Fundação de dados e estrutura base | APPLIED | — |
| `v0.3-stable` | `e533e24` | — | Correções cirúrgicas da auditoria v0.3 | APPLIED | — |
| `v0.4-onda2-poissonmodel` | `498bdb5` | Onda 2 | Modelo Poisson implementado e testado | APPLIED | — |
| `v0.5-onda3-valuedetector` | `1bfbe71` | Onda 3 | Value Detector com EV e deduplicação | APPLIED | — |
| `v0.6-onda4a-backtest` | `19d4d6d` | Onda 4A | Motor de backtest com dataset e métricas | APPLIED | — |
| `v0.7-onda4b-robustez` | `80a6af3` | Onda 4B | Hardening do backtest e casos adversariais | APPLIED | — |
| `v0.8-onda5-api-segura` | `7e94545` | Onda 5 | API FastAPI segura, read-only, sem campos financeiros | APPLIED | — |
| `v0.9-onda6-geminivalidator-offline` | `0bb63c8` | Onda 6 | Validador Gemini em modo offline/simulado | APPLIED | — |
| `v1.0-onda7-green-red-classifier` | `b2abd10` | Onda 7 | Classificador GREEN_SIM / RED_SIM com persistência | APPLIED | — |
| `v1.1-onda8-outcome-feedback-loop` | `c2d378d` | Onda 8 | Loop de feedback com outcomes e Pinnacle | APPLIED | Nome lógico era `v1.1-onda8-pinnacle-resilience` em versões anteriores. Divergência documental histórica detectada, sem impacto no estado final validado. |
| `v1.2-onda9-dashboard-readonly` | `0302450` | Onda 9 | Dashboard read-only com hardening leve | APPLIED | — |
| `v1.3-onda10-visual-migrations` | `3742c1f` | Onda 10 | Observabilidade visual e migrações versionadas | APPLIED | — |
| `v1.4-onda11-migration-engine` | `bade543` | Onda 11 | Engine de migrações versionadas completa | APPLIED | — |
| `v1.5-onda12-outcome-ingestion` | `8f370e7` | Onda 12 | Coleta controlada de outcomes / resultado final consolidado | APPLIED | Nome lógico do plano era `v1.5-onda12-outcome-collection`. Divergência documental histórica detectada, sem impacto no estado final validado. |
| `v1.6-onda13-advanced-calibration` | `68931a1` | Onda 13 | Calibração histórica avançada / Advanced Calibration Intelligence | APPLIED | — |
| `v2.0-local-robust-release` | `cc9e680` | Onda 14 | Hardening final, deploy local, manual operacional | APPLIED | Tag principal de release. |

---

## Notas sobre nomenclatura

- A sequência de tags no repositório segue fielmente as ondas definidas no plano de projeto.
- Divergências históricas identificadas são puramente documentais e não alteram o estado funcional validado do sistema.
- Nenhuma tag foi removida ou reescrita durante este processo de normalização.

---

## Status consolidado

```
Release atual : v2.0-local-robust-release
Commit HEAD   : cc9e680
Estado        : APPLIED — Versão robusta local entregue
```
