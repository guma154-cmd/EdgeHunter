# EdgeHunter: Sistema de Value Betting Esportivo

EdgeHunter é um sistema automatizado para identificar e (opcionalmente) executar apostas de valor (EV+) em mercados de futebol, com foco inicial no Brasileirão e na Premier League. O projeto utiliza um modelo de regressão de Poisson para calcular probabilidades "justas" e as compara com as odds de mercado para encontrar discrepâncias de valor.

## Arquitetura e Decisões

Este projeto segue as diretrizes do **BMAD (Behavior-driven Modular Architecture & Design)**. Toda a documentação de design, incluindo PRDs (Product Requirements Documents), ADRs (Architecture Decision Records) e User Stories detalhadas, pode ser encontrada no diretório `/docs`.

- **/docs/prd/**: Documentos de Requisitos do Produto.
- **/docs/architecture/**: Decisões Arquiteturais (ex: escolha do modelo, stack, etc.).
- **/docs/_index/**: Índices auto-gerados de PRDs e ADRs. Não editar manualmente; regenerar com `python scripts/generate_index.py`.
- **/docs/stories/**: Todas as User Stories detalhadas que guiam a implementação.

## Stack Tecnológica

- **Backend**: Python 3.10+, Flask
- **Banco de Dados**: SQLite com modo WAL
- **Agendamento de Tarefas**: APScheduler
- **Gerenciamento de Dependências**: Poetry
- **Testes**: Pytest, pytest-cov, pytest-mock
- **Validação por IA**: Google Gemini Flash
- **Alertas**: Telegram
- **Linting & Formatting**: Ruff, Black, MyPy

## Estrutura de Pastas

```
edgehunter/
├── pyproject.toml          # Configuração do Poetry e dependências
├── README.md               # Este arquivo
├── docs/                   # Documentação (PRDs, ADRs, Stories)
├── src/                    # Código fonte principal
│   └── edgehunter/
│       ├── database/       # Lógica de banco de dados (schema, conexão)
│       ├── core/           # Lógica de negócio (modelos, detectores)
│       ├── api/            # Endpoints da API Flask
│       └── ...             # Outros módulos (scrapers, utils, etc.)
├── tests/                  # Testes automatizados
│   ├── unit/               # Testes unitários
│   ├── integration/        # Testes de integração
│   └── adversarial/        # Testes de robustez
└── scripts/                # Scripts utilitários (ex: init_db.py)
```

## Setup e Instalação

### Pré-requisitos

- Python >= 3.10
- Poetry instalado (`pip install poetry`)

### Passos para Instalação

1.  **Clonar o repositório:**
    ```bash
    git clone <url_do_repositorio>
    cd edgehunter
    ```

2.  **Instalar dependências:**
    O Poetry criará um ambiente virtual e instalará todas as dependências listadas no `pyproject.toml`.
    ```bash
    poetry install
    ```

3.  **Configurar variáveis de ambiente:**
    Copie o template `.env.example` para um novo arquivo `.env` e preencha com suas chaves e configurações.
    ```bash
    cp .env.example .env
    ```
    Edite o arquivo `.env` com suas informações (tokens de API, etc.).

4.  **Inicializar o banco de dados:**
    Este comando executa o script que cria o arquivo do banco de dados SQLite e aplica o schema mais recente.
    ```bash
    poetry run python scripts/init_db.py
    ```
    Após a execução, você deverá ver a mensagem "✅ Banco de dados inicializado com sucesso!" e um novo arquivo `edge_hunter.db` (e `edge_hunter.db-wal`) será criado no diretório raiz.

## Como Rodar os Testes

Para garantir que tudo está funcionando corretamente, execute a suíte de testes completa:

```bash
poetry run pytest
```

O comando executará todos os arquivos `test_*.py` dentro da pasta `tests/` e exibirá um relatório de cobertura de código no final.

Para gerar um relatório de cobertura em HTML:
```bash
poetry run pytest --cov=src/edgehunter --cov-report=html
```
Abra o arquivo `htmlcov/index.html` em seu navegador para ver o relatório detalhado.
