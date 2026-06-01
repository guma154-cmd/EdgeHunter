from fastapi import FastAPI, Depends
from src.edgehunter.api.contracts import build_safe_api_response
from src.edgehunter.api.security import get_api_key
from src.edgehunter.api.routes import router as detections_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="EdgeHunter API",
        description=(
            "EdgeHunter Safe API.\n\n"
            "- **Strictly Read-Only**\n"
            "- All data is **simulated** and for **paper trading** only.\n"
            "- This is **not** an operational recommendation and **not** betting advice.\n"
            "- This API does **not** execute any actions.\n"
            "- No financial fields are returned."
        ),
        version="0.7.0"
    )

    app.include_router(detections_router)

    @app.get("/api/health", tags=["health"])
    def health_check():
        return build_safe_api_response({"status": "ok", "service": "edgehunter-api"})

    @app.get("/api/readiness", dependencies=[Depends(get_api_key)], tags=["readiness"])
    def readiness_check():
        return build_safe_api_response({"status": "ready"})

    return app
