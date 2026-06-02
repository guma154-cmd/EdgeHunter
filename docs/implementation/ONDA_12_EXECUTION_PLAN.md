# Onda 12 — Coleta Controlada de Outcomes / Resultado Final Consolidado

## Veredicto da Onda 12
A Onda 12 implementará o pipeline de importação local de resultados observados e reconciliação (fechamento de ciclo). O design será 100% dry-run/simulado e seguro.

## Objetivo Técnico
Criar um pipeline controlado para transformar resultados finais consolidados em outcomes simulados, fechando o ciclo de classificação (Classificação GREEN/RED → Resultado final observado → Outcome técnico → Persistência). Aceitar apenas fontes locais (CSV, JSON, fixtures em memória).

## Escopo Permitido
- Contrato de resultado final observado.
- Parser local de CSV/JSON.
- Engine de vínculo/reconciliação (resultado final x classificação simulada).
- Conversão para `SimulatedSignalOutcome`.
- Persistência dos outcomes gerados.
- Relatório de reconciliação.
- API read-only de reconciliação/status.
- Testes adversariais de ingestão.

## Escopo Proibido
- Nenhuma ação financeira real, cálculo financeiro operacional (stake, Kelly, bankroll).
- Sem Telegram, AutoEvolution, scraper, ou execução de comandos externos.
- Sem POST/PUT/PATCH/DELETE operacional na API.
- Nenhuma rede externa ou integração com casas/Google/Gemini.

## Modelo de Resultado Final Observado
O contrato conterá os status:
- `POSITIVE_OBSERVED`
- `NEGATIVE_OBSERVED`
- `UNRESOLVED`
- `INVALIDATED`

## Estratégia de Ingestão Local
Ingestão determinística recebendo o conteúdo bruto via código (`content` em string) para CSV/JSON. Sem chamadas HTTP ou I/O de rede.

## Estratégia de Vínculo com Classificações
Tentativa de match por ordem de prioridade: `signal_id`, `classification_id`, `opportunity_id`, `match_id`.

## Estratégia de Geração de Outcomes
Transformação estrita dos estados mapeados de `ObservedResultStatus` para `OutcomeStatus`. ID determinístico, não usa heurística/AI, não altera threshold, flags seguras (paper trading).

## Stories Propostas
- STORY-12-001: Plano formal da Onda 12.
- STORY-12-002: Contrato de Resultado Final Observado.
- STORY-12-003: Parser Local CSV/JSON de Resultados Observados.
- STORY-12-004: Vinculador Resultado Observado ↔ Classificação.
- STORY-12-005: Conversor Resultado Observado → SimulatedSignalOutcome.
- STORY-12-006: Pipeline Local de Ingestão Controlada.
- STORY-12-007: API Read-only de Reconciliação.
- STORY-12-008: Testes Adversariais de Ingestão.
- STORY-12-009: Encerramento da Onda 12.

## Estratégia de Testes
Testes 100% unitários focados, gates de qualidade globais (`check_doc_consistency`, `check_transaction_discipline`), proteção adversarial contra injeção de jargão de aposta, malformação de dados, sobrecarga de tamanho e locks.

## Guardrails
- Nenhuma string operacional/apostadora nos payloads.
- Sem SQLite onde não é explícito.
- Sem acessos de rede.

## Critérios de Encerramento
100% dos testes rodando, tree clean, relatório formal gerado.

## Tag Alvo
`v1.5-onda12-outcome-ingestion`
