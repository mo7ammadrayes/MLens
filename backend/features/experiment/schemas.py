from pydantic import BaseModel, Field, PositiveInt


class AddExperiment(BaseModel):
    algorithm: str
    split: float = Field(gt=0, lt=1)
    parameters: dict
    results: dict
    dataset_id: PositiveInt
    target: str
    features: list[str] = Field(min_length=1)
    is_public: bool | None = None


class CompareExperimentsRequest(BaseModel):
    experiment_ids: list[PositiveInt] = Field(
        min_length=2,
        max_length=10,
    )

class UpdateExperiment(BaseModel):
    is_public: bool
