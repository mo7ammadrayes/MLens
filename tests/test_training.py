"""Training experiments, and saving and loading the fitted model."""
from io import BytesIO

import joblib
import pandas as pd

from tests.conftest import regression_csv, train, upload


def test_classification_training_records_an_experiment(client, alice):
    dataset_id = upload(client, alice).json()["dataset_id"]

    response = train(client, alice, dataset_id, save_model=False)

    assert response.status_code == 201
    result = response.json()
    assert result["model_id"] is None
    assert 0 <= result["results"]["accuracy"] <= 1
    assert "classification_report" in result["results"]

    experiment = client.get(f"/experiments/{result['experiment_id']}", headers=alice).json()
    assert experiment["algorithm"] == "Random Forest"
    assert experiment["parameters"]["task_type"] == "classification"
    assert experiment["parameters"]["categorical_features"] == ["school"]


def test_regression_training_reports_regression_metrics(client, alice):
    dataset_id = upload(client, alice, csv=regression_csv()).json()["dataset_id"]

    response = train(
        client, alice, dataset_id,
        target="score", features=["hours", "attendance"], categorical=[],
        task_type="regression", algorithm="Linear Regression", model_parameters={},
    )

    assert response.status_code == 201
    results = response.json()["results"]
    assert set(results) == {"mae", "rmse", "r2"}
    assert results["r2"] > 0.9  # the score is almost linear in the features


def test_unsupported_algorithm_is_rejected(client, alice):
    dataset_id = upload(client, alice).json()["dataset_id"]
    assert train(client, alice, dataset_id, algorithm="Neural Net").status_code == 422


def test_out_of_range_hyperparameter_is_rejected(client, alice):
    dataset_id = upload(client, alice).json()["dataset_id"]
    response = train(client, alice, dataset_id, model_parameters={"n_estimators": 5000})
    assert response.status_code == 422


def test_text_feature_must_be_marked_categorical(client, alice):
    dataset_id = upload(client, alice).json()["dataset_id"]
    response = train(client, alice, dataset_id, categorical=[])
    assert response.status_code == 422
    assert "school" in response.json()["detail"]


def test_cannot_train_on_another_users_dataset(client, alice, bob):
    dataset_id = upload(client, alice, public=True).json()["dataset_id"]
    assert train(client, bob, dataset_id).status_code == 404


def test_saved_model_can_be_loaded_and_used(client, alice, storage):
    dataset_id = upload(client, alice).json()["dataset_id"]

    result = train(client, alice, dataset_id).json()
    model = client.get(f"/models/{result['model_id']}", headers=alice).json()

    # The artifact in storage is a joblib pipeline that predicts on raw rows.
    artifact = storage.files[(model["storage_bucket"], model["artifact_path"])]
    pipeline = joblib.load(BytesIO(artifact))
    rows = pd.DataFrame({"hours": [9, 1], "attendance": [95, 55], "school": ["public", "private"]})
    predictions = pipeline.predict(rows)
    assert set(predictions) <= {"yes", "no"}


def test_deleting_a_model_removes_its_artifact(client, alice, storage):
    dataset_id = upload(client, alice).json()["dataset_id"]
    model_id = train(client, alice, dataset_id).json()["model_id"]
    artifacts_before = len(storage.files)

    assert client.delete(f"/models/{model_id}", headers=alice).status_code == 200
    assert len(storage.files) == artifacts_before - 1
    assert client.get(f"/models/{model_id}", headers=alice).status_code == 404


def test_model_too_large_for_storage_keeps_experiment_and_explains(client, alice, storage, monkeypatch):
    from storage3.exceptions import StorageApiError

    dataset_id = upload(client, alice).json()["dataset_id"]
    real_from = storage.from_

    def reject_models(bucket):
        target = real_from(bucket)
        if bucket == "models":
            def too_large(path, file, file_options=None):
                raise StorageApiError(
                    "The object exceeded the maximum allowed size", "Payload too large", 413,
                )
            target.upload = too_large
        return target

    monkeypatch.setattr(storage, "from_", reject_models)

    response = train(client, alice, dataset_id, save_model=True)

    assert response.status_code == 201
    result = response.json()
    assert result["model_id"] is None
    assert "larger than storage allows" in result["model_error"]
    # Training itself succeeded and the experiment is kept.
    assert client.get(f"/experiments/{result['experiment_id']}", headers=alice).status_code == 200
    assert client.get("/models", headers=alice).json() == []


def test_successful_save_reports_no_model_error(client, alice):
    dataset_id = upload(client, alice).json()["dataset_id"]
    result = train(client, alice, dataset_id, save_model=True).json()
    assert result["model_id"] is not None
    assert result["model_error"] is None


def id_column_csv(rows: int = 1200) -> str:
    lines = ["student_id,hours,school,passed"]
    for i in range(rows):
        hours = (i * 7) % 11
        lines.append(f"S{i:05d},{hours},{'public' if i % 3 else 'private'},{'yes' if hours > 5 else 'no'}")
    return "\n".join(lines) + "\n"


def test_id_like_categorical_column_is_rejected_before_training(client, alice):
    dataset_id = upload(client, alice, csv=id_column_csv()).json()["dataset_id"]

    response = train(
        client, alice, dataset_id,
        features=["student_id", "hours", "school"], categorical=["student_id", "school"],
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "student_id" in detail and "1,200 distinct values" in detail
    assert client.get("/experiments", headers=alice).json() == []  # nothing saved


def test_same_dataset_trains_without_the_id_column(client, alice):
    dataset_id = upload(client, alice, csv=id_column_csv()).json()["dataset_id"]
    response = train(client, alice, dataset_id, features=["hours", "school"], categorical=["school"])
    assert response.status_code == 201


def test_inspect_reports_distinct_values(client, alice):
    dataset_id = upload(client, alice, csv=id_column_csv(50)).json()["dataset_id"]
    unique = client.get(f"/datasets/{dataset_id}/inspect", headers=alice).json()["unique_values"]
    assert unique == {"student_id": 50, "hours": 11, "school": 2, "passed": 2}
