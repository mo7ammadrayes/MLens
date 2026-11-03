import logging
from collections import OrderedDict

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth.dependencies import CurrentUser, OptionalUser
from backend.auth.ownership import readable_dataset, require_dataset
from backend.database.session import get_db
from backend.features.user.model import User
from backend.features.ai.http_errors import handle_ai_errors
from backend.features.ai.schemas import Explanation
from backend.features.ai.service import explain_dataset_context
from backend.features.dataset.cleaning_service import (
    clean_and_save_dataset,
)
from backend.features.dataset.schemas import (
    CleanDatasetRequest,
    CopyDatasetRequest,
    UpdateDataset,
)
from backend.features.dataset.service import (
    MAX_CSV_SIZE,
    delete_dataset_db,
    get_user_datasets,
    update_dataset_db,
    upload_dataset,
)
from backend.services.data_analysis_service import (
    inspect_dataset,
    load_dataset_by_id,
)
from backend.storage.service import download_file

logger = logging.getLogger(__name__)

PREVIEW_ROWS = 15

router = APIRouter(prefix="/datasets", tags=["Datasets"])


def dataset_response(dataset):
    return {
        "dataset_id": dataset.dataset_id,
        "name": dataset.name,
        "rows": dataset.rows,
        "cols": dataset.cols,
        "added_by": dataset.added_by,
        "original_filename": dataset.original_filename,
        "created_at": dataset.created_at,
        "is_public": dataset.is_public,
        "is_featured": dataset.is_featured,
        "description": dataset.description,
        "source": dataset.source,
        "tags": dataset.tags or [],
        "cleaning_metadata": dataset.cleaning_metadata,
    }


# Stored datasets never change (cleaning and copying create new rows), so
# inspection and preview results can be cached per dataset_id. This keeps
# public Discover pages from downloading the CSV on every visit.
_INSPECTION_CACHE: OrderedDict[int, dict] = OrderedDict()
_PREVIEW_CACHE: OrderedDict[int, dict] = OrderedDict()
_CACHE_SIZE = 64


def _cached(cache: OrderedDict, key: int, compute):
    if key in cache:
        cache.move_to_end(key)
        return cache[key]
    value = compute()
    cache[key] = value
    if len(cache) > _CACHE_SIZE:
        cache.popitem(last=False)
    return value


def _load_errors(compute):
    try:
        return compute()
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(
            500,
            "The registered dataset file is missing",
        ) from error


def _preview(df, rows: int = PREVIEW_ROWS) -> dict:
    head = df.head(rows)
    # JSON has no NaN: send missing cells as null.
    head = head.astype(object).where(head.notna(), None)
    return {
        "columns": df.columns.tolist(),
        "rows": head.values.tolist(),
        "total_rows": int(len(df)),
    }


@router.post("", status_code=201)
def adding_dataset(
    user: CurrentUser,
    name: str = Form(..., min_length=1),
    file: UploadFile = File(...),
    is_public: bool = Form(True),
    description: str | None = Form(None, max_length=2000),
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
            added_by=user.user_id,
            original_filename=file.filename or "",
            contents=contents,
            is_public=is_public,
            description=(description or "").strip() or None,
        )
    except FileExistsError as error:
        raise HTTPException(409, str(error)) from error
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise HTTPException(
                409,
                "Dataset name or storage location already registered",
            ) from error
        raise

    return dataset_response(saved_dataset)


@router.get("")
def get_datasets(user: CurrentUser, db: Session = Depends(get_db)):
    return [
        dataset_response(dataset)
        for dataset in get_user_datasets(db, user.user_id)
    ]


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: int,
    user: OptionalUser,
    db: Session = Depends(get_db),
):
    dataset = readable_dataset(db, dataset_id, user)
    owner = db.get(User, dataset.added_by)
    return {
        **dataset_response(dataset),
        "owner_name": owner.name if owner else None,
    }


@router.patch("/{dataset_id}")
def update_dataset(
    dataset_id: int,
    dataset: UpdateDataset,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    require_dataset(db, dataset_id, user)
    changes = dataset.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    if "tags" in changes and changes["tags"] is not None:
        changes["tags"] = [
            tag.strip()[:40] for tag in changes["tags"] if tag.strip()
        ]
    for field in ("description", "source"):
        if field in changes and changes[field] is not None:
            changes[field] = changes[field].strip() or None

    for field in ("name", "is_public"):
        if field in changes and changes[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"Dataset {field} cannot be null",
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
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    require_dataset(db, dataset_id, user)

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
                    "experiments or prediction results"
                ),
            ) from error
        raise

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found",
        )

    message = "Dataset and stored CSV deleted successfully"

    if result["file_cleanup_pending"]:
        message = "Dataset deleted; stored CSV cleanup is pending"

    return {
        "message": message,
        **result,
    }


@router.get("/{dataset_id}/inspect")
def inspect_dataset_endpoint(
    dataset_id: int,
    user: OptionalUser,
    db: Session = Depends(get_db),
):
    readable_dataset(db, dataset_id, user)

    return _cached(
        _INSPECTION_CACHE,
        dataset_id,
        lambda: _load_errors(
            lambda: inspect_dataset(load_dataset_by_id(db, dataset_id))
        ),
    )


@router.get("/{dataset_id}/preview")
def preview_dataset(
    dataset_id: int,
    user: OptionalUser,
    db: Session = Depends(get_db),
):
    """The first rows of a readable dataset."""
    readable_dataset(db, dataset_id, user)

    return _cached(
        _PREVIEW_CACHE,
        dataset_id,
        lambda: _load_errors(
            lambda: _preview(load_dataset_by_id(db, dataset_id))
        ),
    )


@router.post("/{dataset_id}/clean", status_code=201)
def clean_dataset(
    dataset_id: int,
    request: CleanDatasetRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    require_dataset(db, dataset_id, user)

    try:
        return clean_and_save_dataset(
            db=db,
            dataset_id=dataset_id,
            user_id=user.user_id,
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
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    dataset = readable_dataset(db, dataset_id, user)

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


@router.post("/{dataset_id}/explanation", response_model=Explanation)
def explain_dataset(
    dataset_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    readable_dataset(db, dataset_id, user)

    # Inspection facts only: the raw rows are never sent to the model.
    context = _cached(
        _INSPECTION_CACHE,
        dataset_id,
        lambda: _load_errors(
            lambda: inspect_dataset(load_dataset_by_id(db, dataset_id))
        ),
    )

    # The shared helper handles AI failures.
    with handle_ai_errors("Dataset explanation"):
        return explain_dataset_context(context)


@router.post("/{dataset_id}/copy", status_code=201)
def copy_dataset(
    dataset_id: int,
    request: CopyDatasetRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Copy a readable (e.g. another user's public) dataset into your account
    so it can be cleaned and used for training."""
    source = readable_dataset(db, dataset_id, user)

    if source.storage_bucket != "datasets":
        raise HTTPException(422, "Only hosted datasets can be copied")

    contents = download_file(
        bucket=source.storage_bucket,
        path=source.storage_path,
    )

    try:
        saved = upload_dataset(
            db=db,
            name=request.name,
            added_by=user.user_id,
            original_filename=source.original_filename,
            contents=contents,
            is_public=request.is_public,
            description=source.description,
        )
    except FileExistsError as error:
        raise HTTPException(409, str(error)) from error
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise HTTPException(
                409,
                "Dataset name or storage location already registered",
            ) from error
        raise

    # Keep attribution with the copy; it is never featured.
    saved.source = source.source or f"Copied from {source.name} (dataset #{source.dataset_id})"
    saved.tags = source.tags
    db.commit()
    db.refresh(saved)
    return dataset_response(saved)
