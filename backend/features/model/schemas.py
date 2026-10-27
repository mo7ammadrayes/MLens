from typing import Literal

from pydantic import BaseModel, Field, PositiveInt


class TrainModelRequest(BaseModel):
    user_id: PositiveInt
    dataset_id: PositiveInt
    target: str
    features: list[str] = Field(min_length=1)
    categorical: list[str]
    train_size: float = Field(gt=0, lt=1)
    task_type: Literal["classification", "regression"] = "classification"
    algorithm: str
    save_model: bool = False
    numerical_strategy: Literal["mean", "median"] = "median"
    drop_duplicates: bool = False
    missing_strategy: Literal["impute", "drop_rows"] = "impute"
    model_parameters: dict[str, object] = Field(default_factory=dict)

