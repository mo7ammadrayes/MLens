import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.storage.model import PendingFileDeletion
from backend.storage.service import delete_file


logger = logging.getLogger(__name__)


def process_file_deletion(
    db: Session,
    deletion_id: int,
) -> bool:
    pending = db.get(PendingFileDeletion, deletion_id)

    if pending is None:
        return True

    bucket = pending.storage_bucket
    path = pending.storage_path

    try:
        delete_file(bucket=bucket, path=path)

        db.delete(pending)
        db.commit()
    except Exception:
        db.rollback()

        logger.exception(
            "File cleanup remains pending: deletion_id=%s, %s/%s",
            deletion_id,
            bucket,
            path,
        )
        return False

    return True


def retry_pending_file_deletions(
    db: Session,
    limit: int = 100,
) -> dict[str, int]:
    deletion_ids = list(
        db.scalars(
            select(PendingFileDeletion.deletion_id)
            .order_by(PendingFileDeletion.deletion_id)
            .limit(limit)
        ).all()
    )

    completed = 0

    for deletion_id in deletion_ids:
        if process_file_deletion(db, deletion_id):
            completed += 1

    return {
        "attempted": len(deletion_ids),
        "completed": completed,
        "pending": len(deletion_ids) - completed,
    }