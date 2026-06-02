# Operations Manual - EdgeHunter

## 1. Visão Geral
EdgeHunter é um sistema de monitoramento técnico e observabilidade analítica local. Todas as operações rodam em modo estritamente **simulado** e **read-only**. O sistema avalia dados passados ou dados de laboratório sem jamais interferir no ambiente externo.

## 2. Instalação de Dependências
Para rodar localmente, o EdgeHunter depende de Python 3.10+ e bibliotecas básicas como `fastapi`, `uvicorn`, `pytest` e `pydantic`.
Recomendamos o uso de um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows
pip install -r requirements.txt
```

## 3. Configuração Local (.env)
Copie o arquivo `.env.example` para `.env` na raiz do projeto:
```bash
cp .env.example .env
```
Neste arquivo, certifique-se de que os modos read-only e simulado estejam ativos. Jamais forneça credenciais produtivas ou APIs externas de mensagens. A API local aceitará requisições de leitura de forma segura via `EDGEHUNTER_API_KEY`.

## 4. Testes do Sistema
Todo o conjunto de validadores está disponível no `pytest`. Para executar toda a suíte de maneira segura e offline:
```bash
python -m pytest
```

## 5. Iniciar API Local
A inicialização local é protegida e exige conformidade do ambiente. Utilize o script oficial para iniciar:
```bash
python scripts/run_local_api.py
```
Isso verificará as variáveis, garantirá que os recursos simulados estão ativos e inicializará o servidor local (default: `127.0.0.1:8000`).

## 6. Acesso ao Dashboard
O dashboard é uma interface gráfica read-only e analítica, acessível diretamente no navegador. Com a API rodando, acesse:
[http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)

## 7. Execução do Smoke Test
O smoke test realiza chamadas às rotas internas via `TestClient` para garantir resiliência sem expor o banco à rede.
```bash
python scripts/smoke_test_local.py
```

## 8. Interpretação GREEN_SIM / RED_SIM
Os classificadores simulados marcam dados com os rótulos **GREEN_SIM** (quando o valor de modelo de Poisson excede a avaliação da probabilidade implícita do mercado) ou **RED_SIM** (caso não exceda ou se não houver confirmação). Nenhum deles constitui conselho financeiro.

## 9. Interpretação de Outcomes
Quando uma simulação de "outcome" ocorre, ela utiliza dados puramente históricos para fechar as classificações:
* **POSITIVE_OBSERVED**: Evento de simulação concluído e convergente com a modelagem GREEN_SIM.
* **NEGATIVE_OBSERVED**: Evento concluído de modo divergente.
* **UNRESOLVED / INVALIDATED**: Não processável por falhas de integração.

## 10. Calibração Avançada
A aba de calibração exibe clusters analíticos e tendências do sistema, oferecendo:
* Desvios históricos em janelas de dados.
* Threshold simulado técnico (`technical_threshold_suggestion`) que jamais é autoaplicado (o usuário apenas visualiza os dados como relatórios estáticos).

## 11. Como fazer Backup
Utilize a camada de ferramentas (Ops):
```python
from src.edgehunter.ops.backup_restore import create_local_backup
create_local_backup("data/edgehunter.db", "backups/")
```

## 12. Como fazer Restore
```python
from src.edgehunter.ops.backup_restore import restore_local_backup
# dry_run para simular a operação sem corromper:
restore_local_backup("backups/arquivo.bak", "data/edgehunter.db", dry_run=True)
# Realizar efetivamente (substitui o arquivo target):
restore_local_backup("backups/arquivo.bak", "data/edgehunter.db", dry_run=False)
```

## 13. Checklist de Manutenção
- Rodar `check_transaction_discipline.py` diariamente no ambiente de lab.
- Manter `.env` seguro.
- Validar `health` e `readiness` de maneira passiva.

## 14. Guardrails (Segurança)
O sistema bloqueia preventivamente:
- Autoaplicação de Thresholds.
- Conexões com sistemas de mensageria externa (ex: tokens são reportados como violações se injetados indevidamente no ambiente).
- Exibição ou processamento de volume financeiro simulado.
