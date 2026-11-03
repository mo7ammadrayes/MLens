from pydantic import BaseModel, Field

class Explanation(BaseModel):
    summary:str


class ModelRecommendation(BaseModel):
    algorithm: str
    parameters: dict
    reason: str
    uncertainty: str

class ExperimentRecommendations(BaseModel):
    summary: str
    recommendations: list[ModelRecommendation]= Field(max_length=3)

