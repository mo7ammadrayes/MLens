from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.features.experiment.model import Experiment
from backend.features.model.model import Model
from backend.storage.model import PendingFileDeletion
from backend.storage.cleanup_service import process_file_deletion
def get_model_by_id(
    db: Session,
    model_id: int,
) -> Model | None:
    return db.get(Model, model_id)


def get_all_models(db: Session) -> list[Model]:
    return list(
        db.scalars(
            select(Model).order_by(Model.model_id)
        ).all()
    )


def create_model(
    db: Session,
    *,
    storage_bucket: str,
    artifact_path: str,
    experiment_id: int,
) -> Model:
    if db.get(Experiment, experiment_id) is None:
        raise LookupError("Experiment not found")

    model = Model(
        storage_bucket=storage_bucket,
        artifact_path=artifact_path,
        experiment_id=experiment_id,
    )

    try:
        db.add(model)
        db.flush()
        db.refresh(model)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return model


def delete_model_db(
    db: Session,
    model_id: int,
) -> dict | None:
    model = db.get(Model, model_id)

    if model is None:
        return None

    if model.storage_bucket != "models":
        raise ValueError(
            "This deletion workflow only supports hosted models"
        )

    pending = PendingFileDeletion(
        storage_bucket=model.storage_bucket,
        storage_path=model.artifact_path,
    )

    try:
        db.add(pending)
        db.delete(model)

        db.flush()
        deletion_id = pending.deletion_id

        db.commit()
    except Exception:
        db.rollback()
        raise

    cleanup_completed = process_file_deletion(db, deletion_id)

    return {
        "model_id": model_id,
        "file_cleanup_pending": not cleanup_completed,
        "cleanup_id": None if cleanup_completed else deletion_id,
    }