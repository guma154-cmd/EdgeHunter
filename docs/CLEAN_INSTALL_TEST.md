# Teste de Instalação Limpa Local — EdgeHunter

Este documento descreve o roteiro de validação de instalação limpa e o script automatizado que o executa.

## Objetivo

Garantir que o projeto pode ser clonado, configurado e executado localmente a partir de um estado limpo, sem dependências ocultas, sem chamadas de rede e sem execução de comandos externos não declarados.

---

## Pré-requisitos

- Python 3.10 ou superior instalado.
- Git instalado.
- Dependências do projeto instaladas via `pip install -r requirements.txt`.

---

## Roteiro manual de instalação limpa

### Passo 1 — Clonar (ou copiar) o projeto

```bash
git clone <repositório-local>
cd EdgeHunter
```

### Passo 2 — Criar e ativar ambiente virtual

```bash
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### Passo 3 — Instalar dependências

```bash
pip install -r requirements.txt
```

### Passo 4 — Configurar ambiente

```bash
cp .env.example .env
# Verificar que READ_ONLY_MODE=true e ACTIONABLE=false estão ativos
```

### Passo 5 — Rodar verificação de instalação limpa

```bash
python scripts/clean_install_check.py
```

Resultado esperado:
```
Running EdgeHunter Clean Install Check...
  [✓] file_exists:pyproject.toml
  [✓] file_exists:.env.example
  ...
  [✓] fastapi_app:create_app_callable
  [✓] tests_listable

Status: READY
```

### Passo 6 — Rodar smoke test

```bash
python scripts/smoke_test_local.py
```

### Passo 7 — Rodar suíte completa de testes

```bash
python -m pytest
```

---

## Script automatizado

O script `scripts/clean_install_check.py` realiza as seguintes verificações:

| Verificação | Descrição |
|-------------|-----------|
| Arquivos obrigatórios | Verifica existência de `pyproject.toml`, `.env.example`, docs e scripts principais. |
| Imports obrigatórios | Confirma que os módulos principais da aplicação são importáveis. |
| FastAPI app | Confirma que `create_app()` retorna uma instância válida. |
| Tests listáveis | Confirma que o diretório `tests/` existe e contém arquivos de teste. |

### Garantias do script

- **Não chama rede**: Nenhuma conexão HTTP/socket é aberta.
- **Não instala pacotes**: Nenhum `pip install` ou `subprocess.run` é chamado.
- **Não executa shell**: Nenhum `os.system` ou comando externo é disparado.
- **Determinístico**: O resultado é idêntico entre chamadas sucessivas no mesmo estado.

---

## Interpretação do resultado

| Status | Significado |
|--------|-------------|
| `READY` | Projeto instalado corretamente e pronto para uso local. |
| `NOT_READY` | Uma ou mais verificações falharam. Ver lista de `errors` para diagnóstico. |

---

## Testes automatizados

O arquivo `tests/unit/scripts/test_clean_install_check.py` cobre os seguintes cenários:

1. Projeto válido retorna `READY`.
2. Ausência de `pyproject.toml` retorna `NOT_READY`.
3. Ausência de `.env.example` retorna `NOT_READY`.
4. Ausência de doc principal retorna `NOT_READY`.
5. Ausência de script principal retorna `NOT_READY`.
6. Resultado é determinístico.
7. Não chama rede.
8. Não instala dependências.
9. Não executa shell.
10. Flags de segurança (`is_simulated`, `actionable`, `not_operational_advice`) sempre presentes.
11. Lista de checks nunca vazia.
