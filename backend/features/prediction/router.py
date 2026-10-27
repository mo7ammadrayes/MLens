from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.features.prediction.schemas import PredictRequest
from fastapi.responses import Response

from backend.features.prediction.service import (
    download_prediction_result,
    predict_dataset,
    delete_prediction_result,

)
router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"],
)


@router.post("")
def run_prediction(
    request: PredictRequest,
    db: Session = Depends(get_db),
):
    try:
        return predict_dataset(
            db=db,
            user_id=request.user_id,
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
    


@router.get("/{prediction_result_id}/download")
def download_result(
    prediction_result_id: int,
    db: Session = Depends(get_db),
):
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
    db: Session = Depends(get_db),
):
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