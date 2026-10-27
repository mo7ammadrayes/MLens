from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class Model(Base):
    __tablename__ = "models"

    __table_args__ = (
        UniqueConstraint(
            "storage_bucket",
            "artifact_path",
            name="uq_model_storage_location",
        ),
    )

    model_id: Mapped[int] = mapped_column(primary_key=True)

    storage_bucket: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    artifact_path: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.experiment_id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )