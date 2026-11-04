from pathlib import Path
from uuid import uuid4

import pandas as pd
from sqlalchemy.orm import Session

from backend.features.dataset.service import get_dataset_by_id
from backend.features.experiment.service import (
    create_experiment,
    get_experiment_by_id,
)
from backend.features.model.service import (
    create_model,
    get_model_by_id,
)
from backend.features.user.model import User
from backend.services.data_analysis_service import load_dataset_by_id
from backend.services.ml_service import (
    analysing_attempt,
    predict_using_existing_models,
    save_model,
    serialize_model,
    predict_using_model_bytes
)
import logging
from backend.storage.service import upload_file,download_file
from backend.storage.model import PendingFileDeletion
from backend.storage.cleanup_service import process_file_deletion

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts"


def model_storage_message(error: Exception, size_mb: float) -> str:
    status = str(getattr(error, "status", ""))
    if status == "413" or "exceeded the maximum allowed size" in str(error):
        return (
            f"The experiment was saved, but its model ({size_mb:.0f} MB) is "
            "larger than storage allows, so it was not saved. Models grow "
            "with many one-hot columns (for example ID or date columns) and "
            "with many trees. Try fewer or lower-cardinality features, or "
            "fewer estimators, then re-run with Save model."
        )
    return (
        "The experiment was saved, but the model could not be stored "
        "because of a storage error. Re-run with Save model to try again."
    )


def train_and_save_model(
    db: Session,
    dataset_id,
    user_id,
    target,
    features,
    categorical,
    train_size,
    algorithm,
    persist_model=False,
    numerical_strategy="median",
    drop_duplicates=False,
    missing_strategy="impute",
    task_type="classification",
    model_parameters=None,
    is_public=None,
):
    
    dataset = get_dataset_by_id(db, dataset_id)

    if dataset is None:
        raise LookupError("Dataset not found")

    if db.get(User, user_id) is None:
        raise LookupError("User not found")

    if dataset.added_by != user_id:
        raise ValueError("Dataset does not belong to this user")

    df = load_dataset_by_id(db, dataset_id)

    model_pipeline, experiment = analysing_attempt(
        target=target,
        features=features,
        categorical=categorical,
        df=df,
        train_size=train_size,
        algorithm=algorithm,
        numerical_strategy=numerical_strategy,
        drop_duplicates=drop_duplicates,
        missing_strategy=missing_strategy,
        task_type=task_type,
        model_parameters=model_parameters,
    )


    configuration = {
        "classifier": experiment["parameters"],
        "categorical_features": experiment["categorical_features"],
        "random_state": experiment["random_state"],
        "numerical_strategy": experiment["numerical_strategy"],
        "categorical_strategy": experiment["categorical_strategy"],
        "drop_duplicates": experiment["drop_duplicates"],
        "missing_strategy": experiment["missing_strategy"],
        "duplicates_removed": experiment["duplicates_removed"],
        "missing_rows_removed": experiment["missing_rows_removed"],
        "task_type": experiment["task_type"],
    }

    saved_experiment = create_experiment(
        db,
        algorithm=experiment["algorithm"],
        split={
            "train_size": experiment["train_size"],
            "random_state": experiment["random_state"],
        },
        parameters=configuration,
        results=experiment["results"],
        dataset_id=dataset_id,
        user_id=user_id,
        target=experiment["target"],
        features=experiment["features"],
        is_public=is_public,
    )

    experiment_id = saved_experiment.experiment_id
    model_id = None
    model_error = None

    if persist_model:
        contents = serialize_model(model_pipeline)
        size_mb = len(contents) / (1024 * 1024)

        bucket = "models"
        artifact_path = (
            f"users/{user_id}/models/"
            f"experiment_{experiment_id}_{uuid4().hex}.joblib"
        )

        try:
            upload_file(
                bucket=bucket,
                path=artifact_path,
                contents=contents,
                content_type="application/octet-stream",
            )
        except Exception as error:
            # Training succeeded and the experiment is already saved; only
            # storing the fitted model failed. Report it instead of a 500.
            logger.exception(
                "Could not store model for experiment %s (%.1f MB)",
                experiment_id,
                size_mb,
            )
            model_error = model_storage_message(error, size_mb)
        else:
            try:
                saved_model = create_model(
                    db,
                    storage_bucket=bucket,
                    artifact_path=artifact_path,
                    experiment_id=experiment_id,
                )
            except Exception:
                # Registration failed after the file was uploaded.
                # Save a cleanup task, then attempt cleanup immediately.
                db.rollback()

                try:
                    pending = PendingFileDeletion(
                        storage_bucket=bucket,
                        storage_path=artifact_path,
                    )

                    db.add(pending)
                    db.flush()
                    deletion_id = pending.deletion_id
                    db.commit()

                    process_file_deletion(db, deletion_id)
                except Exception:
                    db.rollback()
                    logger.exception(
                        "Could not complete or register model cleanup: %s/%s",
                        bucket,
                        artifact_path,
                    )

                raise

            model_id = saved_model.model_id

    return {
        "experiment_id": experiment_id,
        "model_id": model_id,
        "is_public": saved_experiment.is_public,
        # Set when save_model was requested but the model could not be stored.
        "model_error": model_error,
        "results": experiment["results"],
    }


def predict_dataset(
    db: Session,
    model_id: int,
    dataset_id: int,
):
    model = get_model_by_id(db, model_id)

    if model is None:
        raise LookupError(f"Model {model_id} not found")

    experiment = get_experiment_by_id(db, model.experiment_id)

    if experiment is None:
        raise LookupError("The model's experiment was not found")

    if model.storage_bucket != "models":
        raise ValueError(
            "This model must be saved in the models bucket"
        )

    features = experiment.features

    if not features:
        raise ValueError("The experiment has no saved feature list")

    df = load_dataset_by_id(db, dataset_id)

    if df.empty:
        raise ValueError("The prediction dataset is empty")

    for feature in features:
        if feature not in df.columns:
            raise ValueError(
                f"Required feature '{feature}' is missing"
            )

    configuration = experiment.parameters
    categorical = configuration.get("categorical_features", [])

    for feature in features:
        if feature not in categorical:
            values = df[feature].dropna()

            if (
                not values.empty
                and not pd.api.types.is_numeric_dtype(values)
            ):
                raise ValueError(
                    f"Feature '{feature}' must contain numerical values"
                )

    if configuration.get("missing_strategy", "impute") == "drop_rows":
        if df[features].isna().any().any():
            raise ValueError(
                "This model requires complete feature values; "
                "its training strategy was drop_rows"
            )

    model_contents = download_file(
        bucket=model.storage_bucket,
        path=model.artifact_path,
    )

    predictions = predict_using_model_bytes(
        model_contents=model_contents,
        df=df[features],
    )

    return {
        "model_id": model_id,
        "dataset_id": dataset_id,
        "predictions": predictions.tolist(),
    }