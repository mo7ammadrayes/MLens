from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.features.ai.http_errors import handle_ai_errors

from backend.database.session import get_db
from backend.features.user.model import User
from backend.features.experiment.schemas import (
    AddExperiment,
    CompareExperimentsRequest,
    UpdateExperiment,
)
from backend.features.experiment.service import (
    create_experiment,
    delete_experiment_db,
    get_user_experiments,
    compare_experiments,
    get_related_experiments
) 
from backend.features.experiment.context import build_experiment_context,build_recommendation_context
from backend.features.ai.service import explain_experiment_context,explain_comparison_context,recommend_experiment_context
from backend.features.ai.schemas import Explanation,ExperimentRecommendations
import logging

from backend.auth.dependencies import CurrentUser, OptionalUser
from backend.auth.ownership import readable_experiment, require_experiment

logger = logging.getLogger(__name__)

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
        "is_public": experiment.is_public,
    }


def readable_experiments(db: Session, experiment_ids: list[int], user):
    for experiment_id in dict.fromkeys(experiment_ids):
        readable_experiment(db, experiment_id, user)


@router.get("")
def list_experiments(user: CurrentUser, db: Session = Depends(get_db)):
    return [
        experiment_response(experiment)
        for experiment in get_user_experiments(db, user.user_id)
    ]


@router.get("/{experiment_id}")
def get_experiment(
    experiment_id: int,
    user: OptionalUser,
    db: Session = Depends(get_db),
):
    experiment = readable_experiment(db, experiment_id, user)
    owner = db.get(User, experiment.user_id)
    return {
        **experiment_response(experiment),
        "owner_name": owner.name if owner else None,
    }


@router.patch("/{experiment_id}")
def update_experiment(
    experiment_id: int,
    request: UpdateExperiment,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    experiment = require_experiment(db, experiment_id, user)
    experiment.is_public = request.is_public

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(experiment)
    return experiment_response(experiment)


@router.post("", status_code=201)
def adding_experiment(
    request: AddExperiment,
    user: CurrentUser,
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
            user_id=user.user_id,
            target=request.target,
            features=request.features,
            is_public=request.is_public,
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
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    require_experiment(db, experiment_id, user)

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
    user: OptionalUser,
    db: Session = Depends(get_db),
):
    readable_experiments(db, request.experiment_ids, user)

    try:
        return compare_experiments(
            db=db,
            experiment_ids=request.experiment_ids,
        )
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    



@router.post("/compare/explanation", response_model=Explanation)
def explain_comparison_endpoint(
    request: CompareExperimentsRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    readable_experiments(db, request.experiment_ids, user)

    # Retrieve experiments and calculate the deterministic comparison.
    try:
        comparison = compare_experiments(
            db=db,
            experiment_ids=request.experiment_ids,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    # Prepare JSON-compatible context without changing the comparison.
    context = {
        **comparison,
        "experiments": [
            {
                key: value
                for key, value in experiment.items()
                if key != "created_at"
            }
            for experiment in comparison["experiments"]
        ],
    }

    # Generate and validate the explanation.
    # Comparison explanation
    with handle_ai_errors("Comparison explanation"):
        return explain_comparison_context(context)
    


@router.post("/{experiment_id}/explanation", response_model=Explanation)
def explain_experiment(
    experiment_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    experiment = readable_experiment(db, experiment_id, user)

    context = build_experiment_context(experiment)
        
    with handle_ai_errors("Experiment explanation"):
        return explain_experiment_context(context)
    
    


@router.post(
    "/{experiment_id}/recommendations",
    response_model=ExperimentRecommendations,
)
def recommend_experiment_endpoint(
    experiment_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    experiment = readable_experiment(db, experiment_id, user)

    try:
        # Other viewers only get the owner's public history as context.
        related_experiments = get_related_experiments(
            db,
            experiment,
            public_only=experiment.user_id != user.user_id,
        )

        context = build_recommendation_context(
            experiment=experiment,
            related_experiments=related_experiments,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    with handle_ai_errors("Experiment recommendations"):
        return recommend_experiment_context(context)
    
