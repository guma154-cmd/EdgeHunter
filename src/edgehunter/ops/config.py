import os

def load_local_config(env: dict | None = None) -> dict:
    if env is None:
        env = dict(os.environ)

    # Defaults apply safely
    api_key = env.get("EDGEHUNTER_API_KEY", "")
    db_path = env.get("EDGEHUNTER_DB_PATH", "./data/edgehunter.db")
    host = env.get("EDGEHUNTER_HOST", "127.0.0.1")
    
    try:
        port = int(env.get("EDGEHUNTER_PORT", "8000"))
    except ValueError:
        port = 8000

    log_level = env.get("EDGEHUNTER_LOG_LEVEL", "INFO")
    environment = env.get("EDGEHUNTER_ENV", "local")

    read_only = str(env.get("EDGEHUNTER_READ_ONLY_MODE", "true")).lower() == "true"
    is_simulated = str(env.get("EDGEHUNTER_IS_SIMULATED", "true")).lower() == "true"
    paper_trading = str(env.get("EDGEHUNTER_PAPER_TRADING", "true")).lower() == "true"
    actionable = str(env.get("EDGEHUNTER_ACTIONABLE", "false")).lower() == "true"

    return {
        "api_key": api_key,
        "db_path": db_path,
        "host": host,
        "port": port,
        "log_level": log_level,
        "environment": environment,
        "read_only_mode": read_only,
        "is_simulated": is_simulated,
        "paper_trading": paper_trading,
        "actionable": actionable
    }

def validate_local_config(config: dict) -> dict:
    if not config.get("read_only_mode"):
        raise ValueError("EDGEHUNTER_READ_ONLY_MODE must be true in local mode.")
    
    if config.get("actionable"):
        raise ValueError("EDGEHUNTER_ACTIONABLE must be false in local mode.")
        
    if not config.get("is_simulated"):
        raise ValueError("EDGEHUNTER_IS_SIMULATED must be true in local mode.")
        
    if not config.get("paper_trading"):
        raise ValueError("EDGEHUNTER_PAPER_TRADING must be true in local mode.")
        
    port = config.get("port")
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise ValueError(f"EDGEHUNTER_PORT must be an integer between 1 and 65535, got {port}.")

    host = config.get("host")
    if not isinstance(host, str) or not host.strip():
        raise ValueError("EDGEHUNTER_HOST must be a valid string.")

    api_key = config.get("api_key")
    if not api_key:
        return {"status": "DEGRADED", "reason": "EDGEHUNTER_API_KEY is not set."}
        
    return {"status": "VALID", "reason": "Configuration is robust."}
