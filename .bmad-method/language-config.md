# BMAD Language Configuration — EdgeHunter Project

## REGRA OBRIGATÓRIA: Português Brasileiro (PT-BR)

**TODOS os agentes BMAD operando neste workspace DEVEM:**

1. **Responder ao usuário em PT-BR** (Português Brasileiro)
2. **Criar todos os artefatos em PT-BR**:
   - PRDs (Product Requirements Documents)
   - ADRs (Architecture Decision Records)
   - User Stories
   - Documentação técnica
   - Comentários em código (quando aplicável)
   - Mensagens de commit
   - README e runbooks

## Exceções (manter em INGLÊS)

**Apenas estes elementos permanecem em inglês**:
- Nomes de variáveis, funções e classes no código (Python convention)
- Strings de log técnico (debug/error messages para devs)
- Nomes de bibliotecas e frameworks (FastAPI, Playwright, etc.)
- Termos técnicos consagrados sem tradução padrão:
  - "value betting" (manter no original)
  - "snapshot", "scraper", "endpoint"
  - "rate limit", "timeout", "deploy"
  - "Pull Request", "commit", "branch"
  - "true probability", "expected value (EV)"
  - "Kelly Criterion"
  - "Maximum Likelihood Estimation (MLE)"
  
- Acrônimos técnicos: API, REST, SQL, JSON, MLE, EV, ROI, UTC, BRT

## Padrões de Terminologia BMAD em PT-BR

| Inglês | Português (usar este) |
|--------|----------------------|
| Status | Status (manter) |
| Owner | Responsável |
| Parent | Pai (ou: PRD pai, ADR pai) |
| Draft | Rascunho |
| Created | Criado em |
| Acceptance Criteria | Critério de Aceitação |
| Estimate | Estimativa |
| User Story | História de Usuário |
| Goals | Metas |
| Non-Goals | Não-Metas |
| Open Questions | Questões em Aberto |
| Resolved Decisions | Decisões Resolvidas |
| Dependencies | Dependências |
| Upstream | Upstream (manter) |
| Downstream | Downstream (manter) |
| References | Referências |
| Problem Statement | Declaração do Problema |
| Technical Specification | Especificação Técnica |
| Risks & Mitigations | Riscos & Mitigações |
| todo | a fazer |
| in-progress | em andamento |
| done | concluído |
| blocked | bloqueado |

## Padrão de Datas

- **Formato**: DD/MM/AAAA no display
- **Armazenamento**: ISO 8601 (AAAA-MM-DD) no SQL/JSON
- **Hora**: 24h, sem AM/PM
- **Timezone**: UTC no DB, BRT no display Telegram

## Padrão de Números

- **Decimais**: vírgula (R$ 5,73 — não R$ 5.73)
- **Milhares**: ponto (1.000 jogos — não 1,000)
- **Percentuais**: 65% (sem espaço)
- **Moeda**: R$ X,XX

## Enforcement

Se um agente BMAD produzir conteúdo em inglês neste workspace:
1. Usuário pode comandar: "Refaça em PT-BR seguindo `.bmad-method/language-config.md`"
2. Agente deve reconhecer a violação e regenerar
3. Não fazer tradução pós-hoc — sempre regenerar do zero em PT-BR

## Vigência

Este arquivo está ativo para TODOS os agentes BMAD que operarem neste
workspace, desde a data de criação até revogação explícita.

**Criado em**: 2026-05-15
**Aprovado por**: Rafael (Product Owner do EdgeHunter)
