import sys
import os

# Add root project to sys.path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.edgehunter.ops.config import load_local_config, validate_local_config
from src.edgehunter.ops.environment_check import run_environment_check

def check_and_prepare_local_api(env_dict=None) -> dict:
    """Valida ambiente e configuração antes de subir o app. Pode ser testada sem abrir porta."""
    # 1. Carrega config
    config = load_local_config(env_dict)
    
    # 2. Valida regras locais obrigatórias (read_only, is_simulated, etc)
    config_validation = validate_local_config(config)
    if config_validation.get("status") == "DEGRADED" and not config.get("api_key"):
        print("WARNING: EDGEHUNTER_API_KEY is not set. API might be inaccessible.")
        
    # 3. Valida ambiente (pastas, pacotes)
    env_res = run_environment_check(base_path=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), env=env_dict)
    
    if env_res["status"] == "NOT_READY":
        raise RuntimeError(f"Environment is NOT_READY. Errors: {env_res['errors']}")
        
    return config

def main():
    try:
        config = check_and_prepare_local_api()
    except Exception as e:
        print(f"Failed to start local API: {e}")
        sys.exit(1)
        
    host = config["host"]
    port = config["port"]
    
    print("=" * 60)
    print("EdgeHunter - Local Robust Release Mode")
    print(f"Starting API on {host}:{port}")
    print("WARNING: Simulated & Read-Only mode is enforced.")
    print("=" * 60)
    
    try:
        import uvicorn
        uvicorn.run("src.edgehunter.api.app:create_app", host=host, port=port, log_level=config["log_level"].lower(), factory=True)
    except ImportError:
        print("uvicorn is not installed. Please install requirements.")
        sys.exit(1)

if __name__ == "__main__":
    main()
