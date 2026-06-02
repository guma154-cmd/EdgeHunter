# Onda 14 — Hardening Final + Deploy Local + Manual Operacional

## Veredicto da Onda 14
A Onda 14 tem como foco fechar o EdgeHunter como versão robusta local, garantindo que o sistema seja facilmente empacotado, testado e mantido em ambientes locais, sem depender de recursos externos como o Telegram ou Gemini, e estritamente em modo read-only e simulado para operações financeiras.

## Objetivo Técnico
Estabilizar o ambiente com ferramentas locais, garantindo reproduzibilidade via scripts de ambiente, configuração `.env.example`, utilitários de backup/restore e manuais operacionais completos.

## Escopo Permitido
* Validação de ambiente local
* Criação de arquivo `.env.example`
* Criação de script de inicialização local
* Criação de script de smoke test
* Scripts de backup local e restore local controlado
* Documentação operacional e checklist final
* Consolidação de comandos de execução e teste
* Release report final

## Escopo Proibido
* Ação financeira real, cálculos operacionais ou execução real de apostas
* Chamadas de rede para APIs externas (Gemini, Telegram)
* Criação de recursos e scripts para deploy em nuvem ou CI/CD
* Alteração automática ou "auto-apply" de limiares
* Tarefas escalonadas reais ou auto-evolução autônoma

## Estratégias
### Deploy Local
Será mantido e documentado exclusivamente para rodar no ambiente da máquina do usuário local (`127.0.0.1`). Será providenciado um `.env.example`.

### Validação de Ambiente
O validador local irá apenas checar versão de Python, pacotes e presença de `.env`, sem tentar acesso à rede, criando um output de status `READY`/`NOT_READY`/`DEGRADED`.

### Backup e Restore
Baseado exclusivamente em filesystem usando o path do SQLite, garantindo que backups inválidos sejam rejeitados e path traversals bloqueados.

### Documentação Operacional
Centralização dos passos e das expectativas sobre read-only mode, garantindo que "nenhum" threshold é autoaplicado e tudo roda em modo simulação.

## Stories Propostas
* **STORY-14-001**: Plano formal da Onda 14 (Este documento)
* **STORY-14-002**: Validador de Ambiente Local (`src/edgehunter/ops/environment_check.py`)
* **STORY-14-003**: Configuração Local e `.env.example` (`src/edgehunter/ops/config.py`)
* **STORY-14-004**: Scripts Locais de Inicialização e Smoke Test (`scripts/run_local_api.py`, `scripts/smoke_test_local.py`)
* **STORY-14-005**: Backup e Restore Local Controlado (`src/edgehunter/ops/backup_restore.py`)
* **STORY-14-006**: Manual Operacional Local (`docs/OPERATIONS_MANUAL.md`, `docs/LOCAL_DEPLOYMENT.md`, `docs/BACKUP_RESTORE.md`)
* **STORY-14-007**: Checklist Final de Release Local (`scripts/release_check.py`, `docs/RELEASE_CHECKLIST.md`)
* **STORY-14-008**: Testes Adversariais Finais (`tests/unit/ops/test_ops_adversarial.py`, `tests/unit/scripts/test_release_adversarial.py`)
* **STORY-14-009**: Encerramento da Onda 14 / Release Final Local (`docs/implementation/ONDA_14_CLOSURE_REPORT.md`, tag `v2.0-local-robust-release`)

## Estratégia de Testes
Testes de unidade com `pytest` isolando inteiramente rede, IO nocivo, e focando puramente nas validações do utilitário e resiliência a "operational languages".

## Guardrails
Bloquear totalmente qualquer vocabulário operacional (ex: "aposta", "kelly", "stake", "lucro", "execution") de todos os logs, saídas e código da camada de ops. Falhar a suíte imediatamente se `read_only_mode=False` for forçado na configuração local.

## Critérios de Encerramento
* Todos os checks locais devem rodar e passar (healthcheck local, check de disciplina, pytest global limpo).
* Release checklist concluído e formalizado.
* Tag final `v2.0-local-robust-release` devidamente commitada e registrada com sucesso.
