# Roadmap Opcional — EdgeHunter

> **IMPORTANTE**: Nada neste roadmap é requisito para considerar o `v2.0-local-robust-release` entregue.
>
> Este documento registra ideias de expansão futura, classificadas por nível de risco. Nenhum item aqui listado é uma pendência do projeto atual.

---

## Opcional — Baixo risco

Expansões seguras que não alteram o core do sistema nem introduzem dependências externas.

| Item | Descrição |
|------|-----------|
| Melhorar UI visual | Refinamentos de layout, cores e responsividade no dashboard local. |
| Filtros no dashboard | Permitir filtragem por período, status ou conjunto de dados no painel analítico. |
| Exportação CSV local | Gerar relatórios CSV dos dados de classificação, calibração e outcomes para análise offline. |
| Comparação gráfica de períodos | Exibir comparação visual entre dois períodos de calibração distintos. |
| Melhorias de documentação | Expansão de exemplos, FAQs, diagramas de arquitetura e guias de troubleshooting. |

---

## Opcional — Médio risco

Expansões que adicionam automação local controlada, sem dependências externas ou ações operacionais.

| Item | Descrição |
|------|-----------|
| Automação local de ingestão | Monitorar diretório local para processar arquivos CSV/JSON automaticamente. Requer revisão de guardrails. |
| Agendamento local não operacional | Tarefas agendadas para relatórios e backups periódicos, sem acionar ações externas. |
| Relatórios automáticos locais | Geração periódica de relatórios de calibração e status, salvos localmente. |
| Compressão de backups | Comprimir arquivos `.bak` com gzip ou zip para economizar espaço. |
| Rotação automática de backups | Política de retenção local para limitar quantidade de backups antigos. |

---

## Opcional — Alto risco

Expansões que envolvem rede, integrações externas ou automação decisória. **Requerem nova auditoria completa antes de qualquer implementação.**

| Item | Descrição | Risco |
|------|-----------|-------|
| Validador Gemini real | Chamar API real do Gemini para classificação. Exige chave, rede e guardrails adicionais. | ALTO |
| Rede externa de dados | Integrar com provedores de dados de mercado via API. | ALTO |
| Scraping de dados | Captura automatizada de dados de fontes web. | ALTO |
| Integração com provedores externos | APIs de terceiros para enriquecimento de dados. | ALTO |
| Alertas automáticos | Notificações via canal externo baseadas em classificações. Requer revisão de escopo. | ALTO |
| Qualquer automação decisória | Qualquer sistema que tome decisões ou envie comandos com base em classificações. | ALTO |

---

## Fora do escopo atual

Itens que não serão implementados enquanto o projeto operar no modelo atual de laboratório analítico local.

| Item | Motivo |
|------|--------|
| Qualquer forma de execução financeira | Fora do escopo por definição do projeto. |
| Autoaplicação de threshold | Violação do guardrail central do sistema. |
| AutoEvolution | Não implementar. |
| Comandos operacionais diretos | Sem interface de comando operacional. |
| Integração com serviços externos sem nova auditoria | Qualquer integração requer ciclo de auditoria independente. |

---

## Nota de governança

Qualquer item desta lista, antes de ser implementado, deve passar por:

1. Revisão de escopo e guardrails.
2. Aprovação explícita do responsável.
3. Ciclo completo de testes unitários e adversariais.
4. Documentação antes do primeiro commit.
