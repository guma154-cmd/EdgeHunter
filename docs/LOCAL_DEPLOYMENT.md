# Local Deployment - EdgeHunter

## 1. Pré-requisitos
- Python 3.10 ou superior.
- Git para versionamento e hooks locais.
- SQLite3 (incluído no ecossistema Python padrão).

## 2. Instalação Local
Execute a clonagem do repositório (apenas para ambiente laboratorial/local) e instale os pacotes:

```bash
git clone <seu-repo-local>
cd EdgeHunter
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Configuração
Copie o template do ambiente:
```bash
cp .env.example .env
```
O arquivo de configuração local garante um ambiente simulado em 100%. Nunca altere a variável `EDGEHUNTER_READ_ONLY_MODE` para `false`.

## 4. Execução
O EdgeHunter não precisa de webservers produtivos pesados como Gunicorn no laboratório local. Utilize nosso script seguro para inicialização embutida:

```bash
python scripts/run_local_api.py
```
Isso instanciará a aplicação na porta 8000 via Uvicorn. O script rejeitará a execução se as configurações do `.env` desrespeitarem o padrão analítico read-only.

## 5. Healthcheck e Observabilidade
Para validar o serviço de forma offline, execute:
```bash
python scripts/smoke_test_local.py
```
Ele passará por todas as rotas e garantirá o retorno seguro (`/api/health`, `/dashboard`, etc).

## 6. Troubleshooting
- **Erro de ambiente (NOT_READY)**: Rode o comando do `pytest tests/unit/ops/test_environment_check.py` para visualizar o output e garantir que faltas de dependências ou variáveis foram apontadas corretamente.
- **Porta em uso**: Se o Uvicorn falhar porque a porta 8000 está sendo usada, altere a variável `EDGEHUNTER_PORT` no `.env` para outro número inteiro de 1 a 65535.
- **Banco Corrompido**: Realize um "restore" local através do utilitário `src.edgehunter.ops.backup_restore` caso o `integrity_check` falhe.
