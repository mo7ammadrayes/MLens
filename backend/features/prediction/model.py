from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class PredictionResult(Base):
    __tablename__ = "prediction_results"

    __table_args__ = (
        UniqueConstraint(
            "storage_bucket",
            "storage_path",
            name="uq_prediction_result_storage_location",
        ),
    )

    prediction_result_id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )

    model_id: Mapped[int] = mapped_column(
        ForeignKey("models.model_id", ondelete="RESTRICT"),
        nullable=False,
    )

    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.dataset_id", ondelete="RESTRICT"),
        nullable=False,
    )

    storage_bucket: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    prediction_column: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )