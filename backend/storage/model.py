from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class PendingFileDeletion(Base):
    __tablename__ = "pending_file_deletions"

    deletion_id: Mapped[int] = mapped_column(primary_key=True)

    storage_bucket: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )