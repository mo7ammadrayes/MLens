from sqlalchemy import select
from sqlalchemy.orm import Session

# Dataset service
from backend.features.dataset.model import Dataset
from io import BytesIO
from pathlib import Path

import pandas as pd
import logging
from uuid import uuid4

from backend.features.user.model import User
from backend.storage.service import upload_file, delete_file
from backend.storage.model import PendingFileDeletion
from backend.storage.cleanup_service import process_file_deletion

logger = logging.getLogger(__name__)


MAX_CSV_SIZE = 10 * 1024 * 1024  # Our application's limit: 10 MiB


def validate_csv(
    original_filename: str,
    contents: bytes,
) -> tuple[int, int]:
    if Path(original_filename).suffix.lower() != ".csv":
        raise ValueError("Only CSV files are supported")

    if not contents:
        raise ValueError("The uploaded file is empty")

    if len(contents) > MAX_CSV_SIZE:
        raise ValueError("CSV file must not exceed 10 MiB")

    try:
        df = pd.read_csv(
            BytesIO(contents),
            encoding="utf-8-sig",
        )
    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
    ) as error:
        raise ValueError(
            "The file must be a readable UTF-8 CSV"
        ) from error

    if df.empty:
        raise ValueError(
            "The CSV must contain at least one data row and one column"
        )

    return df.shape

def get_dataset_by_id(db: Session, dataset_id: int) -> Dataset | None:
    return db.get(Dataset, dataset_id)

def get_all_datasets(db: Session) -> list[Dataset]:
    return db.scalars(select(Dataset)).all()


def get_user_datasets(db: Session, user_id: int) -> list[Dataset]:
    return list(
        db.scalars(
            select(Dataset)
            .where(Dataset.added_by == user_id)
            .order_by(Dataset.dataset_id.desc())
        ).all()
    )
def create_dataset(
    db: Session,
    name: str,
    rows: int,
    cols: int,
    added_by: int,
    original_filename: str,
    storage_bucket: str,
    storage_path: str,
    cleaning_metadata: dict | None = None,
    is_public: bool = True,
    description: str | None = None,
) -> Dataset:
    dataset = Dataset(
        is_public=is_public,
        description=description,
        name=name,
        rows=rows,
        cols=cols,
        added_by=added_by,
        original_filename=original_filename,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
        cleaning_metadata=cleaning_metadata,
    )

    try:
        db.add(dataset)
        db.flush()
        db.refresh(dataset)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return dataset


def update_dataset_db(
    db: Session,
    dataset_id: int,
    changes: dict,
    
    ) -> Dataset | None:
    dataset = db.get(Dataset, dataset_id)

    if dataset is None:
        return None

    for field, value in changes.items():
        setattr(dataset, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(dataset)
    return dataset

def delete_dataset_db(
    db: Session,
    dataset_id: int,
) -> dict | None:
    dataset = db.get(Dataset, dataset_id)

    if dataset is None:
        return None

    if dataset.storage_bucket != "datasets":
        raise ValueError(
            "This deletion workflow only supports hosted datasets"
        )

    pending = PendingFileDeletion(
        storage_bucket=dataset.storage_bucket,
        storage_path=dataset.storage_path,
    )

    try:
        db.add(pending)
        db.delete(dataset)

        db.flush()
        deletion_id = pending.deletion_id

        db.commit()
    except Exception:
        db.rollback()
        raise

    cleanup_completed = process_file_deletion(db, deletion_id)

    return {
        "dataset_id": dataset_id,
        "file_cleanup_pending": not cleanup_completed,
        "cleanup_id": None if cleanup_completed else deletion_id,
    }

def upload_dataset(
    db: Session,
    *,
    name: str,
    added_by: int,
    original_filename: str,
    contents: bytes,
    cleaning_metadata: dict | None = None,
    is_public: bool = True,
    description: str | None = None,
) -> Dataset:
    name = name.strip()

    if not name:
        raise ValueError("Dataset name cannot be blank")

    if db.get(User, added_by) is None:
        raise LookupError("Dataset owner does not exist")

    existing_dataset = db.scalar(
        select(Dataset).where(
            Dataset.name == name,
            Dataset.added_by == added_by,
        )
    )

    if existing_dataset is not None:
        raise FileExistsError(
            "You already have a dataset with that name"
        )

    rows, cols = validate_csv(original_filename, contents)

    bucket = "datasets"
    storage_path = (
        f"users/{added_by}/datasets/{uuid4().hex}.csv"
    )

    upload_file(
        bucket=bucket,
        path=storage_path,
        contents=contents,
        content_type="text/csv",
    )

    try:
        dataset = create_dataset(
            db=db,
            name=name,
            rows=rows,
            cols=cols,
            added_by=added_by,
            original_filename=original_filename,
            storage_bucket=bucket,
            storage_path=storage_path,
            cleaning_metadata=cleaning_metadata,
            is_public=is_public,
            description=description,
        )
    except Exception:
        try:
            delete_file(bucket, storage_path)
        except Exception:
            logger.exception(
                "Failed to clean up uploaded dataset: %s/%s",
                bucket,
                storage_path,
            )
        raise

    return dataset