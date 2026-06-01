from fastapi import FastAPI, Depends
from src.edgehunter.api.contracts import build_safe_api_response
from src.edgehunter.api.security import get_api_key
from src.edgehunter.api.routes import router as detections_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="EdgeHunter API",
        description="EdgeHunter Safe API - Read Only / Simulated Data",
        version="0.1.0"
    )

    app.include_router(detections_router)

    @app.get("/api/health")
    def health_check():
        return build_safe_api_response({"status": "ok", "service": "edgehunter-api"})

    @app.get("/api/readiness", dependencies=[Depends(get_api_key)])
    def readiness_check():
        return build_safe_api_response({"status": "ready"})

    return app
