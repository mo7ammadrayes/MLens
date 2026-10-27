from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.services.data_analysis_service import (
    inspect_dataset,
    load_dataset_by_id,
)
from backend.database.session import get_db
from backend.features.dataset.schemas import  UpdateDataset,CleanDatasetRequest,AddDataset
from backend.features.dataset.service import (
    MAX_CSV_SIZE,
    upload_dataset,
    get_dataset_by_id,
    get_all_datasets,
    update_dataset_db,
    delete_dataset_db,
)
from backend.features.dataset.cleaning_service import (
    clean_and_save_dataset,
)

from fastapi.responses import Response
from backend.storage.service import download_file

router = APIRouter(prefix="/datasets", tags=["Datasets"])

@router.post("", status_code=201)
def adding_dataset(
    name: str = Form(..., min_length=1),
    added_by: int = Form(..., gt=0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        # Read one byte beyond the limit to detect oversized files.
        contents = file.file.read(MAX_CSV_SIZE + 1)
    finally:
        file.file.close()

    if len(contents) > MAX_CSV_SIZE:
        raise HTTPException(
            status_code=413,
            detail="CSV file must not exceed 10 MiB",
        )

    try:
        saved_dataset = upload_dataset(
            db=db,
            name=name,
            added_by=added_by,
            original_filename=file.filename or "",
            contents=contents,
        )
    except FileExistsError as error:
        raise HTTPException(409, str(error)) from error
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except IntegrityError as error:
        code = getattr(error.orig, "sqlstate", None)

        if code == "23505":
            raise HTTPException(
                409,
                "Dataset name or storage location already registered",
            ) from error

        if code == "23503":
            raise HTTPException(
                422,
                "Dataset owner does not exist",
            ) from error

        raise

    return {
        "dataset_id": saved_dataset.dataset_id,
        "name": saved_dataset.name,
        "rows": saved_dataset.rows,
        "cols": saved_dataset.cols,
        "added_by": saved_dataset.added_by,
        "original_filename": saved_dataset.original_filename,
        "created_at": saved_dataset.created_at,
    }


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = get_dataset_by_id(db, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found",
        )

    return {
        "dataset_id": dataset.dataset_id,
        "name": dataset.name,
        "rows": dataset.rows,
        "cols": dataset.cols,
        "added_by": dataset.added_by,
    }


@router.get("")
def get_datasets(db: Session = Depends(get_db)):
    datasets = get_all_datasets(db)
    final_results = []

    for dataset in datasets:
        result = {
            "dataset_id": dataset.dataset_id,
            "name": dataset.name,
            "rows": dataset.rows,
            "cols": dataset.cols,
            "added_by": dataset.added_by,
        }
        final_results.append(result)

    return final_results


@router.patch("/{dataset_id}")
def update_dataset(
    dataset_id: int,
    dataset: UpdateDataset,
    db: Session = Depends(get_db),
):
    changes = dataset.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    if changes.get("name", "") is None:
        raise HTTPException(
            status_code=422,
            detail="Dataset name cannot be null",
        )

    try:
        updated_dataset = update_dataset_db(db, dataset_id, changes)
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise HTTPException(
                status_code=409,
                detail="You already have a dataset with that name",
            ) from error
        raise

    if updated_dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found",
        )

    return {
        "dataset_id": updated_dataset.dataset_id,
        "updated_fields": changes,
    }

@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    try:
        result = delete_dataset_db(db, dataset_id)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) == "23503":
            raise HTTPException(
                status_code=409,
                detail=(
                "Cannot delete a dataset referenced by "
                "experiments or prediction results"),
            ) from error
        raise

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found",
        )

    message = "Dataset and stored CSV deleted successfully"

    if result["file_cleanup_pending"]:
        message = (
            "Dataset deleted; stored CSV cleanup is pending"
        )

    return {
        "message": message,
        **result,
    }

@router.get("/{dataset_id}/inspect")
def inspect_dataset_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    try:
        df = load_dataset_by_id(db, dataset_id)
        return inspect_dataset(df)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(
            500,
            "The registered dataset file is missing",
        ) from error
    

@router.post("/{dataset_id}/clean", status_code=201)
def clean_dataset(
    dataset_id: int,
    request: CleanDatasetRequest,
    db: Session = Depends(get_db),
):
    try:
        return clean_and_save_dataset(
            db=db,
            dataset_id=dataset_id,
            user_id=request.user_id,
            name=request.name,
            drop_duplicates=request.drop_duplicates,
            missing_strategy=request.missing_strategy,
            columns=request.columns,
        )
    except FileExistsError as error:
        raise HTTPException(409, str(error)) from error
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except IntegrityError as error:
        code = getattr(error.orig, "sqlstate", None)

        if code == "23505":
            raise HTTPException(
                409,
                "Dataset name or storage location already registered",
            ) from error

        if code == "23503":
            raise HTTPException(
                409,
                "A referenced user is no longer available",
            ) from error

        raise


@router.get("/{dataset_id}/download")
def download_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = get_dataset_by_id(db, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found",
        )

    if dataset.storage_bucket != "datasets":
        raise HTTPException(
            status_code=422,
            detail="This download only supports hosted datasets",
        )

    contents = download_file(
        bucket=dataset.storage_bucket,
        path=dataset.storage_path,
    )

    return Response(
        content=contents,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; "
                f'filename="dataset_{dataset_id}.csv"'
            ),
        },
    )