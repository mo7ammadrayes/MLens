"""Browse public datasets, experiments and models from all users.

Available without signing in, so the landing page can show them.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.auth.dependencies import OptionalUser
from backend.database.session import get_db
from backend.features.dataset.model import Dataset
from backend.features.experiment.model import Experiment
from backend.features.model.model import Model
from backend.features.user.model import User

router = APIRouter(prefix="/explore", tags=["Explore"])

Limit = Query(50, ge=1, le=200)
Offset = Query(0, ge=0)


def _like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped.lower()}%"


def _experiment_summary(experiment: Experiment) -> dict:
    return {
        "experiment_id": experiment.experiment_id,
        "algorithm": experiment.algorithm,
        "target": experiment.target,
        "task_type": (experiment.parameters or {}).get("task_type", "classification"),
        "features": experiment.features,
        "split": experiment.split,
        "results": experiment.results,
        "dataset_id": experiment.dataset_id,
        "user_id": experiment.user_id,
        "created_at": experiment.created_at,
    }


@router.get("/datasets")
def explore_datasets(
    user: OptionalUser,
    q: str | None = None,
    featured: bool | None = None,
    limit: int = Limit,
    offset: int = Offset,
    db: Session = Depends(get_db),
):
    example_count = (
        select(func.count(Experiment.experiment_id))
        .where(
            Experiment.dataset_id == Dataset.dataset_id,
            Experiment.is_public.is_(True),
        )
        .correlate(Dataset)
        .scalar_subquery()
    )
    query = (
        select(Dataset, User.name, example_count)
        .join(User, User.user_id == Dataset.added_by)
        .where(Dataset.is_public.is_(True))
    )
    if featured is not None:
        query = query.where(Dataset.is_featured.is_(featured))
    if q:
        pattern = _like(q)
        query = query.where(
            or_(
                func.lower(Dataset.name).like(pattern, escape="\\"),
                func.lower(func.coalesce(Dataset.description, "")).like(pattern, escape="\\"),
            )
        )

    rows = db.execute(
        query.order_by(Dataset.is_featured.desc(), Dataset.dataset_id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return [
        {
            "dataset_id": dataset.dataset_id,
            "name": dataset.name,
            "rows": dataset.rows,
            "cols": dataset.cols,
            "added_by": dataset.added_by,
            "owner_name": owner_name,
            "is_mine": user is not None and dataset.added_by == user.user_id,
            "created_at": dataset.created_at,
            "description": dataset.description,
            "source": dataset.source,
            "tags": dataset.tags or [],
            "is_featured": dataset.is_featured,
            "example_experiments": examples,
        }
        for dataset, owner_name, examples in rows
    ]


@router.get("/experiments")
def explore_experiments(
    user: OptionalUser,
    q: str | None = None,
    dataset_id: int | None = None,
    limit: int = Limit,
    offset: int = Offset,
    db: Session = Depends(get_db),
):
    query = (
        select(Experiment, User.name, Dataset)
        .join(User, User.user_id == Experiment.user_id)
        .join(Dataset, Dataset.dataset_id == Experiment.dataset_id)
        .where(Experiment.is_public.is_(True))
    )
    if dataset_id is not None:
        query = query.where(Experiment.dataset_id == dataset_id)
    if q:
        pattern = _like(q)
        query = query.where(
            or_(
                func.lower(Experiment.algorithm).like(pattern, escape="\\"),
                func.lower(Experiment.target).like(pattern, escape="\\"),
            )
        )

    rows = db.execute(
        query.order_by(Experiment.experiment_id.desc()).limit(limit).offset(offset)
    ).all()

    return [
        {
            **_experiment_summary(experiment),
            "owner_name": owner_name,
            "is_mine": user is not None and experiment.user_id == user.user_id,
            # A private dataset's name is not revealed.
            "dataset_name": dataset.name if dataset.is_public else None,
            "dataset_is_public": dataset.is_public,
        }
        for experiment, owner_name, dataset in rows
    ]


@router.get("/models")
def explore_models(
    user: OptionalUser,
    q: str | None = None,
    experiment_id: int | None = None,
    limit: int = Limit,
    offset: int = Offset,
    db: Session = Depends(get_db),
):
    query = (
        select(Model, Experiment, User.name)
        .join(Experiment, Experiment.experiment_id == Model.experiment_id)
        .join(User, User.user_id == Experiment.user_id)
        .where(Experiment.is_public.is_(True))
    )
    if experiment_id is not None:
        query = query.where(Model.experiment_id == experiment_id)
    if q:
        pattern = _like(q)
        query = query.where(
            or_(
                func.lower(Experiment.algorithm).like(pattern, escape="\\"),
                func.lower(Experiment.target).like(pattern, escape="\\"),
            )
        )

    rows = db.execute(
        query.order_by(Model.model_id.desc()).limit(limit).offset(offset)
    ).all()

    return [
        {
            "model_id": model.model_id,
            "experiment_id": model.experiment_id,
            "created_at": model.created_at,
            "owner_name": owner_name,
            "is_mine": user is not None and experiment.user_id == user.user_id,
            "experiment": _experiment_summary(experiment),
        }
        for model, experiment, owner_name in rows
    ]


@router.get("/stats")
def explore_stats(db: Session = Depends(get_db)):
    public_experiments = select(Experiment.experiment_id).where(
        Experiment.is_public.is_(True)
    )
    return {
        "experiments": db.scalar(
            select(func.count()).select_from(public_experiments.subquery())
        ),
        "models": db.scalar(
            select(func.count(Model.model_id))
            .join(Experiment, Experiment.experiment_id == Model.experiment_id)
            .where(Experiment.is_public.is_(True))
        ),
        "datasets": db.scalar(
            select(func.count(Dataset.dataset_id)).where(Dataset.is_public.is_(True))
        ),
        "contributors": db.scalar(
            select(func.count(func.distinct(Experiment.user_id))).where(
                Experiment.is_public.is_(True)
            )
        ),
    }
