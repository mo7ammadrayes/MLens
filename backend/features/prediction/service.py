from sqlalchemy import select
import pandas as pd
from sqlalchemy.orm import Session

from backend.features.experiment.service import get_experiment_by_id
from backend.features.model.service import get_model_by_id
from backend.features.user.model import User
from backend.services.data_analysis_service import load_dataset_by_id
from backend.services.ml_service import predict_using_model_bytes
from backend.storage.service import download_file
import logging
from uuid import uuid4

from backend.features.prediction.model import PredictionResult
from backend.storage.model import PendingFileDeletion
from backend.storage.cleanup_service import process_file_deletion
from backend.storage.service import upload_file

logger = logging.getLogger(__name__)


def create_prediction_result(
    db: Session,
    *,
    user_id: int,
    model_id: int,
    dataset_id: int,
    storage_bucket: str,
    storage_path: str,
    prediction_column: str,
    rows: int,
) -> PredictionResult:
    result = PredictionResult(
        user_id=user_id,
        model_id=model_id,
        dataset_id=dataset_id,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
        prediction_column=prediction_column,
        rows=rows,
    )

    try:
        db.add(result)
        db.flush()
        db.refresh(result)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return result

def predict_dataset(
    db: Session,
    model_id: int,
    dataset_id: int,
    user_id: int,
    save_results: bool = False,
):
    if db.get(User, user_id) is None:
        raise LookupError(f"User {user_id} not found")

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

    if len(predictions) != len(df):
        raise RuntimeError(
            "Prediction count does not match the input row count"
        )

    prediction_result_id = None
    prediction_column = None

    if save_results:
        output_df = df.copy()

        prediction_column = "prediction"
        suffix = 1

        while prediction_column in output_df.columns:
            prediction_column = f"prediction_{suffix}"
            suffix += 1

        output_df[prediction_column] = predictions

        csv_contents = output_df.to_csv(
            index=False,
        ).encode("utf-8")

        bucket = "prediction-results"
        storage_path = (
            f"users/{user_id}/predictions/{uuid4().hex}.csv"
        )

        upload_file(
            bucket=bucket,
            path=storage_path,
            contents=csv_contents,
            content_type="text/csv",
        )

        try:
            saved_result = create_prediction_result(
                db=db,
                user_id=user_id,
                model_id=model_id,
                dataset_id=dataset_id,
                storage_bucket=bucket,
                storage_path=storage_path,
                prediction_column=prediction_column,
                rows=len(output_df),
            )
        except Exception:
            db.rollback()

            try:
                pending = PendingFileDeletion(
                    storage_bucket=bucket,
                    storage_path=storage_path,
                )

                db.add(pending)
                db.flush()
                deletion_id = pending.deletion_id
                db.commit()

                process_file_deletion(db, deletion_id)
            except Exception:
                db.rollback()
                logger.exception(
                    "Could not complete or register prediction cleanup: %s/%s",
                    bucket,
                    storage_path,
                )

            raise

        prediction_result_id = saved_result.prediction_result_id

    return {
        "prediction_result_id": prediction_result_id,
        "user_id": user_id,
        "model_id": model_id,
        "dataset_id": dataset_id,
        "rows": len(df),
        "prediction_column": prediction_column,
        "predictions": predictions.tolist(),
    }

def get_user_prediction_results(
    db: Session,
    user_id: int,
) -> list[PredictionResult]:
    return list(
        db.scalars(
            select(PredictionResult)
            .where(PredictionResult.user_id == user_id)
            .order_by(PredictionResult.prediction_result_id.desc())
        ).all()
    )


def download_prediction_result(
    db: Session,
    prediction_result_id: int,
) -> bytes:
    result = db.get(PredictionResult, prediction_result_id)

    if result is None:
        raise LookupError(
            f"Prediction result {prediction_result_id} not found"
        )

    if result.storage_bucket != "prediction-results":
        raise ValueError(
            "Unexpected storage bucket for prediction result"
        )

    return download_file(
        bucket=result.storage_bucket,
        path=result.storage_path,
    )

def delete_prediction_result(
    db: Session,
    prediction_result_id: int,
) -> dict | None:
    result = db.get(PredictionResult, prediction_result_id)

    if result is None:
        return None

    if result.storage_bucket != "prediction-results":
        raise ValueError(
            "Unexpected storage bucket for prediction result"
        )

    pending = PendingFileDeletion(
        storage_bucket=result.storage_bucket,
        storage_path=result.storage_path,
    )

    try:
        db.add(pending)
        db.delete(result)

        db.flush()
        deletion_id = pending.deletion_id

        db.commit()
    except Exception:
        db.rollback()
        raise

    cleanup_completed = process_file_deletion(db, deletion_id)

    return {
        "prediction_result_id": prediction_result_id,
        "file_cleanup_pending": not cleanup_completed,
        "cleanup_id": None if cleanup_completed else deletion_id,
    }