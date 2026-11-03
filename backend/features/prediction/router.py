from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.auth.dependencies import CurrentUser
from backend.auth.ownership import (
    readable_model,
    require_dataset,
    require_prediction_result,
)
from backend.database.session import get_db
from backend.features.prediction.schemas import PredictRequest
from backend.features.prediction.service import (
    delete_prediction_result,
    download_prediction_result,
    get_user_prediction_results,
    predict_dataset,
)

router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"],
)


def prediction_result_response(result):
    return {
        "prediction_result_id": result.prediction_result_id,
        "user_id": result.user_id,
        "model_id": result.model_id,
        "dataset_id": result.dataset_id,
        "rows": result.rows,
        "prediction_column": result.prediction_column,
        "created_at": result.created_at,
    }


@router.post("")
def run_prediction(
    request: PredictRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    # Any readable model (yours or a public one); predictions use your own data.
    readable_model(db, request.model_id, user)
    require_dataset(db, request.dataset_id, user)

    try:
        return predict_dataset(
            db=db,
            user_id=user.user_id,
            model_id=request.model_id,
            dataset_id=request.dataset_id,
            save_results=request.save_results,
        )
    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@router.get("")
def list_prediction_results(
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    return [
        prediction_result_response(result)
        for result in get_user_prediction_results(db, user.user_id)
    ]


@router.get("/{prediction_result_id}")
def get_prediction_result(
    prediction_result_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    return prediction_result_response(
        require_prediction_result(db, prediction_result_id, user)
    )


@router.get("/{prediction_result_id}/download")
def download_result(
    prediction_result_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    require_prediction_result(db, prediction_result_id, user)

    try:
        contents = download_prediction_result(
            db=db,
            prediction_result_id=prediction_result_id,
        )
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error

    return Response(
        content=contents,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; "
                f'filename="prediction_result_{prediction_result_id}.csv"'
            ),
        },
    )


@router.delete("/{prediction_result_id}")
def delete_result(
    prediction_result_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    require_prediction_result(db, prediction_result_id, user)

    try:
        result = delete_prediction_result(
            db=db,
            prediction_result_id=prediction_result_id,
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error

    if result is None:
        raise HTTPException(
            404,
            "Prediction result not found",
        )

    message = "Prediction result and stored CSV deleted successfully"

    if result["file_cleanup_pending"]:
        message = (
            "Prediction result deleted; stored CSV cleanup is pending"
        )

    return {
        "message": message,
        **result,
    }
