from backend.features.ai.client import request_structured_output
from backend.features.ai.prompts import PROMPTS
from backend.features.ai.schemas import (
    Explanation,
    ExperimentRecommendations,
)
from backend.services.model_options import (
    MODEL_FACTORIES,
    validate_model_parameters,
)
from backend.features.ai.errors import UnsupportedRecommendationError


def explain_experiment_context(context: dict) -> Explanation:
    return request_structured_output(
        instructions=PROMPTS["experiment"],
        context=context,
        response_schema=Explanation,
    )


def explain_dataset_context(context: dict) -> Explanation:
    return request_structured_output(
        instructions=PROMPTS["dataset"],
        context=context,
        response_schema=Explanation,
    )


def explain_comparison_context(context: dict) -> Explanation:
    return request_structured_output(
        instructions=PROMPTS["comparison"],
        context=context,
        response_schema=Explanation,
    )



def validate_recommendations(
    result: ExperimentRecommendations,
    task_type: str,
) -> ExperimentRecommendations:
    try:
        return _validate_recommendations(result, task_type)
    except ValueError as exc:
        raise UnsupportedRecommendationError(str(exc)) from exc
def _validate_recommendations(
    result: ExperimentRecommendations,
    task_type: str,
) -> ExperimentRecommendations:
    if task_type not in MODEL_FACTORIES:
        raise ValueError(f"Unsupported task type: {task_type}")

    supported_algorithms = MODEL_FACTORIES[task_type]

    for recommendation in result.recommendations:
        if recommendation.algorithm not in supported_algorithms:
            raise ValueError(
                f"Unsupported algorithm for {task_type}: "
                f"{recommendation.algorithm}"
            )

        recommendation.parameters = validate_model_parameters(
            algorithm=recommendation.algorithm,
            supplied=recommendation.parameters,
        )

    return result


def recommend_experiment_context(
    context: dict,
) -> ExperimentRecommendations:
    result = request_structured_output(
        instructions=PROMPTS["recommendations"],
        context=context,
        response_schema=ExperimentRecommendations,
    )

    return validate_recommendations(
        result,
        task_type=context["experiment"]["task_type"],
    )