from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class Experiment(Base):
    __tablename__ = "experiments"

    experiment_id: Mapped[int] = mapped_column(primary_key=True)

    algorithm: Mapped[str] = mapped_column(String, nullable=False)

    split: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    results: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    target: Mapped[str] = mapped_column(String, nullable=False)
    features: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )

    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.dataset_id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )