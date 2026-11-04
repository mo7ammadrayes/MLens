import pandas as pd
from sklearn.model_selection import train_test_split,cross_val_score, KFold,StratifiedKFold, cross_validate
from sklearn import preprocessing
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,confusion_matrix,
    ConfusionMatrixDisplay,
)
import matplotlib.pyplot as plt
from  sklearn.compose import ColumnTransformer
from  sklearn.pipeline import  Pipeline
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.base import clone
from joblib import Parallel, delayed
from sklearn.impute import SimpleImputer
from io import BytesIO
import joblib
import numpy as np
from sklearn.utils.multiclass import type_of_target
from backend.services.model_options import (
    MODEL_FACTORIES,
    validate_model_parameters,
)

# One-hot encoding creates one column per category. Beyond this many in total,
# the model gets huge (and usually overfits), typically because an ID, date or
# free-text column was marked categorical.
MAX_ONE_HOT_COLUMNS = 1000


def check_one_hot_size(d, categorical) -> None:
    levels = {column: int(d[column].nunique()) for column in categorical}
    total = sum(levels.values())

    if total <= MAX_ONE_HOT_COLUMNS:
        return

    worst = max(levels, key=levels.get)
    raise ValueError(
        f"The categorical features would create about {total:,} one-hot "
        f"columns (limit {MAX_ONE_HOT_COLUMNS:,}). '{worst}' alone has "
        f"{levels[worst]:,} distinct values, so it looks like an ID, date "
        "or free-text column. Leave it out of the features."
    )


def serialize_model(model_pipeline) -> bytes:
    with BytesIO() as buffer:
        joblib.dump(model_pipeline, buffer)
        return buffer.getvalue()


def predict_using_model_bytes(
    model_contents: bytes,
    df,
):
    with BytesIO(model_contents) as buffer:
        model_pipeline = joblib.load(buffer)

    return model_pipeline.predict(df)

def save_model(model_pipeline, file_name):
    artifact_path = f"{file_name}.joblib"
    joblib.dump(model_pipeline, artifact_path)
    return artifact_path
def analysing_attempt(
    target,
    features,
    categorical,
    df,
    train_size,
    algorithm,
    numerical_strategy="median",
    drop_duplicates=False,
    missing_strategy="impute",
    task_type="classification",
    model_parameters=None,
):
    
    d = df.copy()

    if task_type not in MODEL_FACTORIES:
        raise ValueError(
            "Task type must be classification or regression"
        )

    task_factories = MODEL_FACTORIES[task_type]

    if algorithm not in task_factories:
        raise ValueError(
            f"Unsupported algorithm '{algorithm}' for {task_type}"
        )

    validated_parameters = validate_model_parameters(
        algorithm=algorithm,
        supplied=(
            model_parameters
            if model_parameters is not None
            else {}
        ),
    )

    factory = task_factories[algorithm]
    estimator = factory()
    estimator.set_params(**validated_parameters)
    
    # Shared configuration validation.
    if not features:
        raise ValueError("Select at least one feature")

    if target not in d.columns:
        raise ValueError(f"Target '{target}' is not present")

    for feature in features:
        if feature not in d.columns:
            raise ValueError(f"Feature '{feature}' is not present")

    for column in categorical:
        if column not in features:
            raise ValueError(
                f"Categorical feature '{column}' is not selected"
            )

    if target in features:
        raise ValueError("Target is selected as a feature")

    if not 0 < train_size < 1:
        raise ValueError("train_size must be between 0 and 1")

    if numerical_strategy not in ("mean", "median"):
        raise ValueError("Numerical strategy must be mean or median")

    if missing_strategy not in ("impute", "drop_rows"):
        raise ValueError("Missing strategy must be impute or drop_rows")

    if d[target].isna().any():
        raise ValueError(
            "Target contains missing values; "
            "remove or label those rows before training"
        )

    # Optional row removal.
    rows_before = len(d)

    if drop_duplicates:
        d = d.drop_duplicates()

    duplicates_removed = rows_before - len(d)

    rows_before = len(d)

    if missing_strategy == "drop_rows":
        d = d.dropna(subset=features)

    missing_rows_removed = rows_before - len(d)

    if d.empty:
        raise ValueError("No rows remain after data preparation")

    check_one_hot_size(d, categorical)

    X = d[features]
    y = d[target]

    numeric_cols = [
        feature
        for feature in features
        if feature not in categorical
    ]

    numeric_df = X[numeric_cols].select_dtypes(include="number")

    for column in numeric_cols:
        if column not in numeric_df.columns:
            raise ValueError(
                f"Feature '{column}' must contain numerical data"
            )

    # Task-specific target validation.
    if task_type == "classification":
        if type_of_target(y) not in ("binary", "multiclass"):
            raise ValueError(
                "Classification requires discrete class labels"
            )

        if y.nunique() < 2:
            raise ValueError(
                "Classification requires at least two classes"
            )

        if y.value_counts().min() < 2:
            raise ValueError(
                "Each class needs at least two rows "
                "for a stratified train/test split"
            )

    else:
        if (
            not pd.api.types.is_numeric_dtype(y)
            or pd.api.types.is_bool_dtype(y)
            or pd.api.types.is_complex_dtype(y)
        ):
            raise ValueError(
                "Regression requires a real numerical target"
            )

        if not np.isfinite(y.to_numpy(dtype=float)).all():
            raise ValueError(
                "Regression target must contain finite values"
            )

    # Classification preserves class proportions.
    # Regression uses a regular random split.
    stratify_values = y if task_type == "classification" else None

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=1 - train_size,
        random_state=42,
        stratify=stratify_values,
    )

    if task_type == "regression" and len(y_test) < 2:
        raise ValueError(
            "Regression needs at least two test rows to calculate R²"
        )

    for feature in X_train.columns:
        if X_train[feature].isna().all():
            raise ValueError(
                f"Feature '{feature}' has no observed values "
                "in the training set"
            )

    # Shared preprocessing.
    numerical_steps = []
    categorical_steps = []

    if missing_strategy == "impute":
        numerical_steps.append(
            ("imputer", SimpleImputer(strategy=numerical_strategy))
        )
        categorical_steps.append(
            ("imputer", SimpleImputer(strategy="most_frequent"))
        )

    numerical_steps.append(
        ("scaler", preprocessing.StandardScaler())
    )

    categorical_steps.append(
        (
            "encoder",
            OneHotEncoder(
                drop="first",
                handle_unknown="ignore",
                sparse_output=False,
            ),
        )
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", Pipeline(categorical_steps), categorical),
            ("numerical", Pipeline(numerical_steps), numeric_cols),
        ]
    )

    model_pipeline = Pipeline([
        ("preprocessing", preprocessor),
        ("classifier", estimator),
    ])

    model_pipeline.fit(X_train, y_train)
    y_pred = model_pipeline.predict(X_test)

    # Task-specific evaluation.
    if task_type == "classification":
        results = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "macro_f1": float(
                f1_score(
                    y_test,
                    y_pred,
                    average="macro",
                    zero_division=0,
                )
            ),
            "classification_report": classification_report(
                y_test,
                y_pred,
                output_dict=True,
                zero_division=0,
            ),
        }
    else:
        results = {
            "mae": float(mean_absolute_error(y_test, y_pred)),
            "rmse": float(
                np.sqrt(mean_squared_error(y_test, y_pred))
            ),
            "r2": float(r2_score(y_test, y_pred)),
        }

    experiment = {
        "task_type": task_type,
        "target": target,
        "features": features,
        "categorical_features": categorical,
        "algorithm": algorithm,
        "parameters": estimator.get_params(),
        "train_size": train_size,
        "random_state": 42,
        "drop_duplicates": drop_duplicates,
        "missing_strategy": missing_strategy,
        "duplicates_removed": duplicates_removed,
        "missing_rows_removed": missing_rows_removed,
        "numerical_strategy": (
            numerical_strategy
            if missing_strategy == "impute"
            else None
        ),
        "categorical_strategy": (
            "most_frequent"
            if missing_strategy == "impute"
            else None
        ),
        "results": results,
    }

    return model_pipeline, experiment


def predict_using_existing_models(model_path, df):

    model_pipeline = joblib.load(model_path)
    return model_pipeline.predict(df)



# analysing_attempt(
#     target="sleep_debt_category",
#     features=[
#         "age",
#         "gender",
#         "occupation_type",
#         "chronotype",
#         "bedtime_phone_minutes",
#         "primary_bedtime_app",
#         "screen_brightness_pct",
#         "blue_light_filter_active",
#         "caffeine_post_5pm_mg",
#         "physical_activity_min",
#     ],
#     categorical=[
#         "gender",
#         "occupation_type",
#         "chronotype",
#         "primary_bedtime_app",
#     ],
#     dataset="bedtime_screentime_sleep_debt.csv",
#     train_size=0.7,
#     algorithm="Logistic Regression",
# )


# new_data = pd.DataFrame({
#     "age": [25],
#     "gender": ["Male"],
#     "occupation_type": ["Student"],
#     "chronotype": ["Night Owl"],
#     "bedtime_phone_minutes": [60],
#     "primary_bedtime_app": ["Instagram / Reddit"],
#     "screen_brightness_pct": [70],
#     "blue_light_filter_active": [1],
#     "caffeine_post_5pm_mg": [80],
#     "physical_activity_min": [30],
# })
# categorical_cols = [
#         "gender", "occupation_type", "chronotype", "primary_bedtime_app"
# ]

# prediction = predict_using_existing_models("test.joblib", new_data)
# print(prediction)

