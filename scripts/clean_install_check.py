import os
import importlib
from typing import Optional

# Lista de arquivos/dirs que DEVEM existir para um projeto limpo
REQUIRED_FILES = [
    "pyproject.toml",
    ".env.example",
    "docs/OPERATIONS_MANUAL.md",
    "docs/LOCAL_DEPLOYMENT.md",
    "docs/BACKUP_RESTORE.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/RELEASE_HISTORY.md",
    "docs/PROJECT_STATUS.md",
    "scripts/run_local_api.py",
    "scripts/smoke_test_local.py",
    "scripts/release_check.py",
    "src/edgehunter/api/app.py",
    "src/edgehunter/api/routes.py",
    "src/edgehunter/ops/backup_restore.py",
    "src/edgehunter/ops/environment_check.py",
    "src/edgehunter/ops/config.py",
]

# Módulos que DEVEM ser importáveis
REQUIRED_IMPORTS = [
    "src.edgehunter.api.app",
    "src.edgehunter.api.routes",
    "src.edgehunter.ops.backup_restore",
    "src.edgehunter.ops.environment_check",
    "src.edgehunter.ops.config",
    "src.edgehunter.database.migrations",
]


def run_clean_install_check(project_root: Optional[str] = None) -> dict:
    """
    Valida se o projeto está em estado limpo e instalável localmente.

    Não chama rede, não instala pacotes, não executa comandos externos.

    Returns:
        dict com status READY | NOT_READY, lista de checks, errors e warnings.
    """
    if project_root is None:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    checks = []
    errors = []
    warnings = []

    # --- Verificação de arquivos obrigatórios ---
    for rel_path in REQUIRED_FILES:
        full_path = os.path.join(project_root, rel_path)
        if os.path.exists(full_path):
            checks.append({"check": f"file_exists:{rel_path}", "result": "PASS"})
        else:
            checks.append({"check": f"file_exists:{rel_path}", "result": "FAIL"})
            errors.append(f"Missing required file: {rel_path}")

    # --- Verificação de imports ---
    import sys
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    for module_name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(module_name)
            checks.append({"check": f"import:{module_name}", "result": "PASS"})
        except ImportError as e:
            checks.append({"check": f"import:{module_name}", "result": "FAIL"})
            errors.append(f"Import failed: {module_name} — {e}")

    # --- Verificar que FastAPI app é importável e instanciável ---
    try:
        app_module = importlib.import_module("src.edgehunter.api.app")
        create_app_fn = getattr(app_module, "create_app", None)
        if create_app_fn is None:
            checks.append({"check": "fastapi_app:create_app_callable", "result": "FAIL"})
            errors.append("create_app not found in src.edgehunter.api.app")
        else:
            app = create_app_fn()
            if app is not None:
                checks.append({"check": "fastapi_app:create_app_callable", "result": "PASS"})
            else:
                checks.append({"check": "fastapi_app:create_app_callable", "result": "FAIL"})
                errors.append("create_app() returned None")
    except Exception as e:
        checks.append({"check": "fastapi_app:create_app_callable", "result": "FAIL"})
        errors.append(f"FastAPI app instantiation failed: {e}")

    # --- Verificar que tests podem ser listados (sem execução) ---
    tests_dir = os.path.join(project_root, "tests")
    if os.path.isdir(tests_dir):
        test_files = []
        for root, dirs, files in os.walk(tests_dir):
            for f in files:
                if f.startswith("test_") and f.endswith(".py"):
                    test_files.append(f)
        if test_files:
            checks.append({"check": "tests_listable", "result": "PASS"})
        else:
            checks.append({"check": "tests_listable", "result": "FAIL"})
            errors.append("No test files found under tests/")
    else:
        checks.append({"check": "tests_listable", "result": "FAIL"})
        errors.append("tests/ directory not found")

    status = "READY" if not errors else "NOT_READY"

    return {
        "status": status,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "is_simulated": True,
        "actionable": False,
        "not_operational_advice": True,
    }


def main():
    import sys
    print("Running EdgeHunter Clean Install Check...")
    res = run_clean_install_check()
    for chk in res["checks"]:
        icon = "✓" if chk["result"] == "PASS" else "✗"
        print(f"  [{icon}] {chk['check']}")
    if res["errors"]:
        print("\nErrors:")
        for err in res["errors"]:
            print(f"  - {err}")
    print(f"\nStatus: {res['status']}")
    sys.exit(0 if res["status"] == "READY" else 1)


if __name__ == "__main__":
    main()
