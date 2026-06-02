import sys
import os
import importlib.util

def check_python_version() -> dict:
    version = sys.version_info
    valid = version.major == 3 and version.minor >= 10
    message = f"Python version is {version.major}.{version.minor}"
    return {
        "name": "Python Version Check",
        "passed": valid,
        "details": message
    }

def check_required_modules() -> dict:
    required = ["fastapi", "pydantic", "pytest", "uvicorn", "dotenv"]
    missing = []
    for mod in required:
        if importlib.util.find_spec(mod) is None:
            missing.append(mod)
    
    passed = len(missing) == 0
    details = f"Missing modules: {', '.join(missing)}" if missing else "All core modules present."
    return {
        "name": "Required Modules Check",
        "passed": passed,
        "details": details,
        "missing": missing
    }

def check_project_paths(base_path: str | None = None) -> dict:
    if base_path is None:
        base_path = os.getcwd()
        
    required_paths = [
        "src/edgehunter/core",
        "src/edgehunter/api",
        "src/edgehunter/database",
        "tests"
    ]
    
    missing = []
    for path in required_paths:
        full_path = os.path.join(base_path, os.path.normpath(path))
        if not os.path.exists(full_path):
            missing.append(path)
            
    passed = len(missing) == 0
    details = f"Missing paths: {', '.join(missing)}" if missing else "All required paths present."
    return {
        "name": "Project Paths Check",
        "passed": passed,
        "details": details,
        "missing": missing
    }

def check_environment_variables(env: dict | None = None) -> dict:
    if env is None:
        env = dict(os.environ)
        
    warnings = []
    
    # DB path is optional but recommended
    db_path = env.get("EDGEHUNTER_DB_PATH")
    if not db_path:
        warnings.append("EDGEHUNTER_DB_PATH is not set. A default or temporary memory path will be used.")
        
    api_key = env.get("EDGEHUNTER_API_KEY")
    if not api_key:
        warnings.append("EDGEHUNTER_API_KEY is not set. API will be inaccessible if auth is required.")
        
    # Check for forbidden variables
    forbidden_keys = ["GEMINI", "TELEGRAM", "AUTOEVOLUTION"]
    for k in env.keys():
        k_upper = k.upper()
        for forbidden in forbidden_keys:
            if forbidden in k_upper:
                warnings.append(f"Forbidden environment variable detected: {k}")

    # No strict errors for env vars to remain local-first
    return {
        "name": "Environment Variables Check",
        "passed": True, # It's not a fatal error if they are missing
        "details": "Environment variables checked.",
        "warnings": warnings
    }

def run_environment_check(base_path: str | None = None, env: dict | None = None) -> dict:
    checks = []
    errors = []
    warnings = []
    
    # 1. Python version
    py_check = check_python_version()
    checks.append(py_check)
    if not py_check["passed"]:
        errors.append(py_check["details"])
        
    # 2. Required modules
    mod_check = check_required_modules()
    checks.append(mod_check)
    if not mod_check["passed"]:
        errors.append(mod_check["details"])
        
    # 3. Project paths
    path_check = check_project_paths(base_path)
    checks.append(path_check)
    if not path_check["passed"]:
        errors.append(path_check["details"])
        
    # 4. Environment Variables
    env_check = check_environment_variables(env)
    checks.append(env_check)
    warnings.extend(env_check.get("warnings", []))
    
    # Determine status
    if len(errors) > 0:
        status = "NOT_READY"
    elif len(warnings) > 0:
        status = "DEGRADED"
    else:
        status = "READY"
        
    return {
        "status": status,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
        "is_simulated": True,
        "actionable": False,
        "not_operational_advice": True
    }
