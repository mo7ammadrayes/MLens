from pydantic import BaseModel, Field, PositiveInt
from typing import Literal


class AddDataset(BaseModel):
    name: str
    rows: int = Field(ge=0)
    cols: int = Field(gt=0)
    added_by: PositiveInt
    original_filename: str
    storage_bucket: str
    storage_path: str


class UpdateDataset(BaseModel):
    name: str | None = Field(default=None, min_length=1)

class CleanDatasetRequest(BaseModel):
    user_id: PositiveInt
    name: str = Field(min_length=1)
    drop_duplicates: bool = False
    missing_strategy: Literal["none", "drop", "mean", "median"] = "none"
    columns: list[str] | None = Field(default=None, min_length=1)