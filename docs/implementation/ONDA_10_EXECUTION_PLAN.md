# ONDA 10 EXECUTION PLAN

## 1. Veredicto da Onda 10
O EdgeHunter está avançando de forma segura para criar uma camada de observabilidade visual read-only e estruturar o versionamento de banco de dados, sem quebrar os guardrails estabelecidos (simulado, paper trading, learning mode). A Onda 10 é AUTORIZADA em modo read-only.

## 2. Objetivo Técnico
Criar uma camada visual read-only para observabilidade do EdgeHunter e iniciar estrutura formal de migrações versionadas.

## 3. Escopo Permitido
- Criação de modelos puramente visuais e read-only.
- Implementação de um renderizador HTML (seguro, estático, sem JS externo).
- Exposição do HTML gerado através do endpoint GET `/dashboard`.
- Estabelecimento de um registro formal (histórico lógico) de migrações versionadas (sem executar alterações destrutivas).
- Implementação de validador para comparar schema esperado com migrações registradas.

## 4. Escopo Proibido
- Ação financeira real, stake, Kelly, bankroll.
- Comandos operacionais ou cálculos financeiros operacionais.
- Modificação autônoma de threshold.
- AutoEvolution, Scheduler ou integração real com Telegram.
- Utilização de APIs do Gemini para operação na Onda 10.
- Execução real de migrações de banco destrutivas (apenas o registro e a validação são criados).
- Uso da palavra-chave aposta ou termos como recomendação operacional, lucro, gain, etc.

## 5. Stories Propostas
- STORY-10-001 — Plano formal da Onda 10
- STORY-10-002 — Contratos de Visualização Read-only
- STORY-10-003 — Renderer HTML/JSON Read-only
- STORY-10-004 — Endpoint Visual Read-only
- STORY-10-005 — Registro Formal de Migrações
- STORY-10-006 — Validador de Migrações Versionadas
- STORY-10-007 — Testes Adversariais Visual + Migrações
- STORY-10-008 — Encerramento da Onda 10

## 6. Estratégia de Testes
Testes unitários severos garantindo que as classes de domínio (`DashboardVisualMetric`, etc) se recusem a aceitar parâmetros como `actionable=True` ou vocabulário proibido. Testes adversariais para garantir injeção zero em HTML, nenhuma gravação destrutiva em banco ao acessar o dashboard e imutabilidade do schema no registry de migrações.

## 7. Guardrails
- Somente leitura no dashboard (sem tags de script injetadas ou CDN externa).
- Apenas o registro formal de versões lógicas nas migrações, sem auto-apply.
- Manutenção do learning mode e alertas de restrição nas telas.

## 8. Endpoints Previstos
- GET `/dashboard` (HTML)
- GET `/api/dashboard/visual` (JSON, opcional)

## 9. Estratégia Visual Read-only
Renderização local e manual usando formatação de strings (`f-strings` ou similar), retornando diretamente texto (text/html). Nada interativo. Banners claros sinalizando que é um painel meramente analítico e estritamente simulado.

## 10. Estratégia de Migrações Versionadas
Listagem estática e ordenada do histórico esperado do schema, baseada em prefixos numéricos (e.g., `0001_foundation_schema`). O validador não aplicará migrações, apenas acusará tabelas ou colunas faltantes em relação ao último baseline validado.

## 11. Dívidas e Riscos
- Dívida: sem biblioteca profissional de template ainda (Jinja2 seria melhor no futuro, mas o escopo limita dependências não cruciais ou obriga segurança máxima no escape manual por agora).
- Risco: O registry de migrations é apenas para observação; em ondas futuras precisaremos construir a mecânica real (engine de up/down).

## 12. Critérios de Encerramento
Todas as stories concluídas; todos os testes passando (coverage 100% nas novas units e adversariais); validadores documentais (`check_doc_consistency.py` e `check_transaction_discipline.py`) aprovando as modificações; tag correspondente criada.

## 13. Tag Alvo
v1.3-onda10-visual-migrations

## 14. Status
**CONCLUÍDO** (Todas as stories concluídas e validadas)
