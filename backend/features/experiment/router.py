from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.features.experiment.schemas import AddExperiment,CompareExperimentsRequest
from backend.features.experiment.service import (
    create_experiment,
    delete_experiment_db,
    get_all_experiments,
    get_experiment_by_id,
    compare_experiments
)


router = APIRouter(prefix="/experiments", tags=["Experiments"])


def experiment_response(experiment):
    return {
        "experiment_id": experiment.experiment_id,
        "algorithm": experiment.algorithm,
        "split": experiment.split,
        "parameters": experiment.parameters,
        "results": experiment.results,
        "target": experiment.target,
        "features": experiment.features,
        "created_at": experiment.created_at,
        "dataset_id": experiment.dataset_id,
        "user_id": experiment.user_id,
    }


@router.get("")
def list_experiments(db: Session = Depends(get_db)):
    return [
        experiment_response(experiment)
        for experiment in get_all_experiments(db)
    ]


@router.get("/{experiment_id}")
def get_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
):
    experiment = get_experiment_by_id(db, experiment_id)

    if experiment is None:
        raise HTTPException(404, "Experiment not found")

    return experiment_response(experiment)


@router.post("", status_code=201)
def adding_experiment(
    request: AddExperiment,
    db: Session = Depends(get_db),
):
    try:
        experiment = create_experiment(
            db,
            algorithm=request.algorithm,
            split={"train_size": request.split},
            parameters=request.parameters,
            results=request.results,
            dataset_id=request.dataset_id,
            user_id=request.user_id,
            target=request.target,
            features=request.features,
        )
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) == "23503":
            raise HTTPException(
                409,
                "The referenced user or dataset is no longer available",
            ) from error
        raise

    return experiment_response(experiment)


@router.delete("/{experiment_id}")
def delete_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
):
    try:
        deleted = delete_experiment_db(db, experiment_id)
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) == "23503":
            raise HTTPException(
                409,
                "Cannot delete an experiment referenced by saved models",
            ) from error
        raise

    if not deleted:
        raise HTTPException(404, "Experiment not found")

    return {"message": "Experiment deleted successfully"}

@router.post("/compare")
def compare_experiments_endpoint(
    request: CompareExperimentsRequest,
    db: Session = Depends(get_db),
):
    try:
        return compare_experiments(
            db=db,
            experiment_ids=request.experiment_ids,
        )
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error