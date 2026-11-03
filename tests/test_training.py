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
