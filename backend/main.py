import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

# Register every ORM model with the shared metadata.
import backend.database.models
from backend.features.prediction.router import router as prediction_router
from backend.features.dataset.router import router as dataset_router
from backend.features.experiment.router import router as experiment_router
from backend.features.model.router import router as model_router
from backend.features.user.router import router as user_router
from backend.features.explore.router import router as explore_router


app = FastAPI(title="ML Experimentation Platform")

# Only needed when the frontend is served from another origin
# (the Vite dev server proxies /api, so local development needs none).
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Content-Disposition"],
    )

app.include_router(user_router)
app.include_router(dataset_router)
app.include_router(experiment_router)
app.include_router(model_router)
app.include_router(prediction_router)
app.include_router(explore_router)

logger = logging.getLogger(__name__)


@app.get("/health", tags=["Health"])
def health():
    """Liveness and database check for Docker and hosting platforms."""
    from backend.database.session import engine

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check: database unreachable")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unreachable"},
        )

    return {"status": "ok", "database": "ok"}
