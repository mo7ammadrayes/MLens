from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.features.dataset.model import Dataset
from backend.features.experiment.model import Experiment
from backend.features.user.model import User


def get_experiment_by_id(
    db: Session,
    experiment_id: int,
) -> Experiment | None:
    return db.get(Experiment, experiment_id)


def get_all_experiments(db: Session) -> list[Experiment]:
    return list(
        db.scalars(
            select(Experiment).order_by(Experiment.experiment_id)
        ).all()
    )

def get_user_experiments(db: Session, user_id: int) -> list[Experiment]:
    return list(
        db.scalars(
            select(Experiment)
            .where(Experiment.user_id == user_id)
            .order_by(Experiment.experiment_id)
        ).all()
    )


def get_related_experiments(
    db: Session,
    experiment: Experiment,
    public_only: bool = False,
) -> list[Experiment]:
    task_type = experiment.parameters.get("task_type")

    if not task_type:
        raise ValueError("Experiment task type is missing")

    candidates = db.scalars(
        select(Experiment)
        .where(
            Experiment.dataset_id == experiment.dataset_id,
            Experiment.user_id == experiment.user_id,
            Experiment.target == experiment.target,
            Experiment.experiment_id != experiment.experiment_id,
        )
        .order_by(Experiment.experiment_id)
    ).all()

    return [
        candidate
        for candidate in candidates
        if candidate.parameters.get("task_type") == task_type
        and (candidate.is_public or not public_only)
    ]


def create_experiment(
    db: Session,
    *,
    algorithm: str,
    split: dict,
    parameters: dict,
    results: dict,
    dataset_id: int,
    user_id: int,
    target: str,
    features: list[str],
    is_public: bool | None = None,
) -> Experiment:
    dataset = db.get(Dataset, dataset_id)

    if dataset is None:
        raise LookupError("Dataset not found")

    if db.get(User, user_id) is None:
        raise LookupError("User not found")

    if dataset.added_by != user_id:
        raise ValueError("Dataset does not belong to this user")

    experiment = Experiment(
        algorithm=algorithm,
        split=split,
        parameters=parameters,
        results=results,
        dataset_id=dataset_id,
        user_id=user_id,
        target=target,
        features=features,
        # Results default to the dataset's visibility.
        is_public=dataset.is_public if is_public is None else is_public,
    )

    try:
        db.add(experiment)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(experiment)
    return experiment


def delete_experiment_db(
    db: Session,
    experiment_id: int,
) -> bool:
    experiment = db.get(Experiment, experiment_id)

    if experiment is None:
        return False

    try:
        db.delete(experiment)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return True

def compare_experiments(
    db: Session,
    experiment_ids: list[int],
) -> dict:
    if not 2 <= len(experiment_ids) <= 10:
        raise ValueError("Select between 2 and 10 experiments")

    duplicates = [
        experiment_id
        for experiment_id in set(experiment_ids)
        if experiment_ids.count(experiment_id) > 1
    ]

    if duplicates:
        raise ValueError(
            f"Duplicate experiment IDs: {sorted(duplicates)}"
        )

    experiments = []

    for experiment_id in experiment_ids:
        experiment = db.get(Experiment, experiment_id)

        if experiment is None:
            raise LookupError(
                f"Experiment {experiment_id} not found"
            )

        experiments.append(experiment)

    reference = experiments[0]
    task_type = reference.parameters.get(
        "task_type",
        "classification",
    )

    warnings = []

    def add_warning(message):
        if message not in warnings:
            warnings.append(message)

    for exp in experiments[1:]:
        if exp.dataset_id != reference.dataset_id:
            raise ValueError(
                "Experiments must use the same dataset"
            )

        if exp.target != reference.target:
            raise ValueError(
                "Experiments must use the same target"
            )

        if exp.parameters.get(
            "task_type", "classification"
        ) != task_type:
            raise ValueError(
                "Experiments must use the same task type"
            )

        if exp.split != reference.split:
            add_warning(
                "Split configurations differ; metrics may use "
                "different test rows."
            )

        # Missing values remain distinguishable from recorded settings.
        row_settings = (
            "drop_duplicates",
            "missing_strategy",
            "duplicates_removed",
            "missing_rows_removed",
        )

        if any(
            exp.parameters.get(key)
            != reference.parameters.get(key)
            for key in row_settings
        ):
            add_warning(
                "Row-removal configurations or counts differ; "
                "the evaluated populations may differ."
            )

        if set(exp.features) != set(reference.features):
            add_warning(
                "Feature selections differ. With drop_rows, this "
                "can also change which rows reach the split."
            )

        preprocessing_keys = (
            "categorical_features",
            "numerical_strategy",
            "categorical_strategy",
        )

        if any(
            exp.parameters.get(key)
            != reference.parameters.get(key)
            for key in preprocessing_keys
        ):
            add_warning(
                "Preprocessing configurations differ; review "
                "them alongside the metrics."
            )

    required_row_settings = (
        "drop_duplicates",
        "missing_strategy",
        "duplicates_removed",
        "missing_rows_removed",
    )

    if any(
        key not in exp.parameters
        for exp in experiments
        for key in required_row_settings
    ):
        add_warning(
            "Some experiments lack row-preparation metadata; "
            "equivalent evaluation conditions cannot be confirmed."
        )

    if task_type == "classification":
        metric_directions = {
            "accuracy": "higher",
            "macro_f1": "higher",
        }
    elif task_type == "regression":
        metric_directions = {
            "mae": "lower",
            "rmse": "lower",
            "r2": "higher",
        }
    else:
        raise ValueError(f"Unsupported task type: {task_type}")

    comparison = []

    for exp in experiments:
        metrics = {
            metric: exp.results.get(metric)
            for metric in metric_directions
        }

        # Older classification runs stored macro-F1 only in the report.
        if task_type == "classification":
            if metrics["macro_f1"] is None:
                metrics["macro_f1"] = (
                    exp.results
                    .get("classification_report", {})
                    .get("macro avg", {})
                    .get("f1-score")
                )

        if any(value is None for value in metrics.values()):
            add_warning(
                f"Experiment {exp.experiment_id} is missing "
                "one or more comparison metrics."
            )

        comparison.append({
            "experiment_id": exp.experiment_id,
            "algorithm": exp.algorithm,
            "features": exp.features,
            "split": exp.split,
            "parameters": exp.parameters,
            "metrics": metrics,
            "created_at": exp.created_at,
        })

    return {
        "dataset_id": reference.dataset_id,
        "target": reference.target,
        "task_type": task_type,
        "metric_directions": metric_directions,
        "warnings": warnings,
        "experiments": comparison,
    }