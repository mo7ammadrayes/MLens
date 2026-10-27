from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

MODEL_FACTORIES = {
    "classification": {
        "Logistic Regression": lambda: LogisticRegression(
            max_iter=10000
        ),
        "Decision Tree": lambda: DecisionTreeClassifier(
            random_state=42
        ),
        "Random Forest": lambda: RandomForestClassifier(
            random_state=42
        ),
        "Gradient Boosting": lambda: GradientBoostingClassifier(
            random_state=42
        ),
    },
    "regression": {
        "Linear Regression": LinearRegression,
        "Decision Tree": lambda: DecisionTreeRegressor(
            random_state=42
        ),
        "Random Forest": lambda: RandomForestRegressor(
            random_state=42
        ),
        "Gradient Boosting": lambda: GradientBoostingRegressor(
            random_state=42
        ),
    },
}

PARAMETER_RULES = {
    "Logistic Regression": {
        "C": {
            "type": "number",
            "default": 1.0,
            "min": 0.001,
            "max": 100.0,
        },
    },
    "Linear Regression": {
        "fit_intercept": {
            "type": "boolean",
            "default": True,
        },
    },
    "Decision Tree": {
        "max_depth": {
            "type": "integer",
            "default": None,
            "nullable": True,
            "min": 1,
            "max": 30,
        },
        "min_samples_split": {
            "type": "integer",
            "default": 2,
            "min": 2,
            "max": 50,
        },
    },
    "Random Forest": {
        "n_estimators": {
            "type": "integer",
            "default": 100,
            "min": 10,
            "max": 300,
        },
        "max_depth": {
            "type": "integer",
            "default": None,
            "nullable": True,
            "min": 1,
            "max": 30,
        },
        "min_samples_split": {
            "type": "integer",
            "default": 2,
            "min": 2,
            "max": 50,
        },
    },
    "Gradient Boosting": {
        "n_estimators": {
            "type": "integer",
            "default": 100,
            "min": 10,
            "max": 300,
        },
        "learning_rate": {
            "type": "number",
            "default": 0.1,
            "min": 0.01,
            "max": 1.0,
        },
        "max_depth": {
            "type": "integer",
            "default": 3,
            "min": 1,
            "max": 10,
        },
    },
}


import math


def validate_model_parameters(
    algorithm: str,
    supplied: dict,
) -> dict:
    if algorithm not in PARAMETER_RULES:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    rules = PARAMETER_RULES[algorithm]

    unknown = set(supplied) - set(rules)

    if unknown:
        raise ValueError(
            f"Unsupported parameters for {algorithm}: "
            f"{', '.join(sorted(unknown))}"
        )

    validated = {}

    for name, rule in rules.items():
        value = supplied.get(name, rule["default"])

        if value is None:
            if rule.get("nullable", False):
                validated[name] = None
                continue

            raise ValueError(f"Parameter '{name}' cannot be null")

        expected_type = rule["type"]

        if expected_type == "boolean":
            valid_type = type(value) is bool
        elif expected_type == "integer":
            valid_type = type(value) is int
        elif expected_type == "number":
            valid_type = type(value) in (int, float)
        else:
            raise RuntimeError(
                f"Unknown parameter rule type: {expected_type}"
            )

        if not valid_type:
            raise ValueError(
                f"Parameter '{name}' must be {expected_type}"
            )

        if expected_type in ("integer", "number"):
            if not math.isfinite(value):
                raise ValueError(
                    f"Parameter '{name}' must be finite"
                )

            if not rule["min"] <= value <= rule["max"]:
                raise ValueError(
                    f"Parameter '{name}' must be between "
                    f"{rule['min']} and {rule['max']}"
                )

        validated[name] = value

    return validated



def get_model_options() -> dict:
    tasks = {}

    for task_type, factories in MODEL_FACTORIES.items():
        algorithms = {}

        for algorithm in factories:
            algorithms[algorithm] = {
                "parameters": PARAMETER_RULES[algorithm],
            }

        tasks[task_type] = {
            "algorithms": algorithms,
        }

    return {
        "tasks": tasks,
        "preprocessing": {
            "numerical_strategy": {
                "allowed": ["mean", "median"],
                "default": "median",
            },
            "missing_strategy": {
                "allowed": ["impute", "drop_rows"],
                "default": "impute",
            },
            "drop_duplicates": {
                "type": "boolean",
                "default": False,
            },
        },
    }