from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class Dataset(Base):
    __tablename__ = "datasets"

    __table_args__ = (
        UniqueConstraint(
            "name",
            "added_by",
            name="uq_dataset_name_owner",
        ),
        UniqueConstraint(
            "storage_bucket",
            "storage_path",
            name="uq_dataset_storage_location",
        ),
    )

    dataset_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    rows: Mapped[int] = mapped_column(Integer, nullable=False)
    cols: Mapped[int] = mapped_column(Integer, nullable=False)

    storage_bucket: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    added_by: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    cleaning_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )