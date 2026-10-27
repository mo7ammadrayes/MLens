from pydantic import BaseModel, PositiveInt


class PredictRequest(BaseModel):
    user_id: PositiveInt
    model_id: PositiveInt
    dataset_id: PositiveInt
    save_results: bool = False