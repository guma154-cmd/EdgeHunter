from fastapi import FastAPI, Depends
from src.edgehunter.api.contracts import build_safe_api_response
from src.edgehunter.api.security import get_api_key

def create_app() -> FastAPI:
    app = FastAPI(
        title="EdgeHunter API",
        description="EdgeHunter Safe API - Read Only / Simulated Data",
        version="0.1.0"
    )

    @app.get("/api/health")
    def health_check():
        return build_safe_api_response({"status": "ok", "service": "edgehunter-api"})

    @app.get("/api/readiness", dependencies=[Depends(get_api_key)])
    def readiness_check():
        return build_safe_api_response({"status": "ready"})

    return app
