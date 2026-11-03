from backend.features.experiment.model import Experiment
from backend.services.model_options import get_model_options

def build_experiment_context(experiment: Experiment) -> dict:
        return {
        "experiment_id":experiment.experiment_id,
        "dataset_id":experiment.dataset_id,
        "algorithm": experiment.algorithm,
        "target": experiment.target,
        "split":experiment.split,
        "task_type": experiment.parameters.get("task_type"),
        "features":experiment.features,
        "parameters":experiment.parameters,
        "results":experiment.results



    }
def build_recommendation_context(
    experiment: Experiment,
    related_experiments: list[Experiment],
) -> dict:
    context = build_experiment_context(experiment)
    task_type = context["task_type"]

    if not task_type:
        raise ValueError("Experiment task type is missing")

    options = get_model_options()

    if task_type not in options["tasks"]:
        raise ValueError(f"Unsupported task type: {task_type}")

    return {
        "experiment": context,
        "supported_algorithms": options["tasks"][task_type]["algorithms"],
        "experiment_history": [
            build_experiment_context(previous)
            for previous in related_experiments
        ],
    }

