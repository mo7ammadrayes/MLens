from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.auth.dependencies import CurrentUser
from backend.auth.ownership import readable_model, require_dataset, require_model
from backend.features.experiment.model import Experiment
from backend.features.model.service import (
    delete_model_db,
    get_user_models,
)
from backend.database.session import get_db
from backend.services.model_options import get_model_options
from backend.run_ml_workflow import (
    train_and_save_model,
)
from backend.features.model.schemas import TrainModelRequest

router = APIRouter(prefix="/models", tags=["Models"])


def model_response(model, experiment=None):
    return {
        "is_public": experiment.is_public if experiment is not None else None,
        "model_id": model.model_id,
        "storage_bucket": model.storage_bucket,
        "artifact_path": model.artifact_path,
        "experiment_id": model.experiment_id,
        "created_at": model.created_at,
    }

@router.get("/options")
def model_options():
    return get_model_options()
@router.get("")
def list_models(user: CurrentUser, db: Session = Depends(get_db)):
    return [
        model_response(model, db.get(Experiment, model.experiment_id))
        for model in get_user_models(db, user.user_id)
    ]


@router.post("/train", status_code=201)
def train_model(
    request: TrainModelRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    require_dataset(db, request.dataset_id, user)

    try:
        return train_and_save_model(
            db=db,
            dataset_id=request.dataset_id,
            user_id=user.user_id,
            target=request.target,
            features=request.features,
            categorical=request.categorical,
            train_size=request.train_size,
            task_type=request.task_type,
            algorithm=request.algorithm,
            model_parameters=request.model_parameters,
            persist_model=request.save_model,
            numerical_strategy=request.numerical_strategy,
            drop_duplicates=request.drop_duplicates,
            missing_strategy=request.missing_strategy,
            is_public=request.is_public,
        )
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(
            500,
            "A registered dataset file is missing",
        ) from error
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) == "23503":
            raise HTTPException(
                409,
                "A referenced record is no longer available",
            ) from error
        raise

@router.get("/{model_id}")
def get_model(
    model_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    model = readable_model(db, model_id, user)
    return model_response(model, db.get(Experiment, model.experiment_id))



@router.delete("/{model_id}")
def delete_model(
    model_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    require_model(db, model_id, user)

    try:
        result = delete_model_db(db, model_id)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) == "23503":
            raise HTTPException(
                409,
                "Cannot delete a model referenced by prediction results",
            ) from error
        raise
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )
    

    message = "Model and stored artifact deleted successfully"

    if result["file_cleanup_pending"]:
        message = (
            "Model deleted; stored artifact cleanup is pending"
        )

    return {
        "message": message,
        **result,
    }


