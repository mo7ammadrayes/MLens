"""Owner-scoped record lookups.

Records belonging to another user are reported as not found, so the API
never reveals whether another user's ID exists.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.features.dataset.model import Dataset
from backend.features.experiment.model import Experiment
from backend.features.model.model import Model
from backend.features.prediction.model import PredictionResult
from backend.features.user.model import User


def require_dataset(db: Session, dataset_id: int, user: User) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.added_by != user.user_id:
        raise HTTPException(404, "Dataset not found")
    return dataset


def require_experiment(db: Session, experiment_id: int, user: User) -> Experiment:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None or experiment.user_id != user.user_id:
        raise HTTPException(404, f"Experiment {experiment_id} not found")
    return experiment


def require_model(db: Session, model_id: int, user: User) -> Model:
    model = db.get(Model, model_id)
    if model is None:
        raise HTTPException(404, "Model not found")
    experiment = db.get(Experiment, model.experiment_id)
    if experiment is None or experiment.user_id != user.user_id:
        raise HTTPException(404, "Model not found")
    return model


def require_prediction_result(
    db: Session,
    prediction_result_id: int,
    user: User,
) -> PredictionResult:
    result = db.get(PredictionResult, prediction_result_id)
    if result is None or result.user_id != user.user_id:
        raise HTTPException(404, "Prediction result not found")
    return result


# ---------- Read access: the owner, or anyone (even signed out) when public ----------

def readable_dataset(db: Session, dataset_id: int, user: User | None) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or not (
        dataset.is_public or (user is not None and dataset.added_by == user.user_id)
    ):
        raise HTTPException(404, "Dataset not found")
    return dataset


def readable_experiment(db: Session, experiment_id: int, user: User | None) -> Experiment:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None or not (
        experiment.is_public or (user is not None and experiment.user_id == user.user_id)
    ):
        raise HTTPException(404, f"Experiment {experiment_id} not found")
    return experiment


def readable_model(db: Session, model_id: int, user: User) -> Model:
    """Models inherit their experiment's visibility."""
    model = db.get(Model, model_id)
    if model is None:
        raise HTTPException(404, "Model not found")
    experiment = db.get(Experiment, model.experiment_id)
    if experiment is None or not (
        experiment.user_id == user.user_id or experiment.is_public
    ):
        raise HTTPException(404, "Model not found")
    return model
