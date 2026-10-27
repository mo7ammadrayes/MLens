from fastapi import FastAPI

# Register every ORM model with the shared metadata.
import backend.database.models
from backend.features.prediction.router import router as prediction_router
from backend.features.dataset.router import router as dataset_router
from backend.features.experiment.router import router as experiment_router
from backend.features.model.router import router as model_router
from backend.features.user.router import router as user_router


app = FastAPI()

app.include_router(user_router)
app.include_router(dataset_router)
app.include_router(experiment_router)
app.include_router(model_router)
app.include_router(prediction_router)