"""Comparing experiments on the same dataset and target."""
from tests.conftest import regression_csv, train, upload


def two_runs(client, headers, public=False):
    dataset_id = upload(client, headers, public=public).json()["dataset_id"]
    first = train(client, headers, dataset_id, save_model=False).json()["experiment_id"]
    second = train(
        client, headers, dataset_id, algorithm="Logistic Regression", model_parameters={}, save_model=False,
    ).json()["experiment_id"]
    return dataset_id, first, second


def test_compare_returns_metrics_and_directions(client, alice):
    _, first, second = two_runs(client, alice)

    response = client.post("/experiments/compare", headers=alice, json={"experiment_ids": [first, second]})

    assert response.status_code == 200
    comparison = response.json()
    assert comparison["task_type"] == "classification"
    assert comparison["metric_directions"] == {"accuracy": "higher", "macro_f1": "higher"}
    assert [e["experiment_id"] for e in comparison["experiments"]] == [first, second]
    assert all(e["metrics"]["accuracy"] is not None for e in comparison["experiments"])


def test_different_targets_cannot_be_compared(client, alice):
    _, first, _ = two_runs(client, alice)
    other = upload(client, alice, name="scores", csv=regression_csv()).json()["dataset_id"]
    regression = train(
        client, alice, other, target="score", features=["hours", "attendance"], categorical=[],
        task_type="regression", algorithm="Linear Regression", model_parameters={}, save_model=False,
    ).json()["experiment_id"]

    response = client.post("/experiments/compare", headers=alice, json={"experiment_ids": [first, regression]})
    assert response.status_code == 422


def test_compare_needs_two_distinct_experiments(client, alice):
    _, first, _ = two_runs(client, alice)
    one = client.post("/experiments/compare", headers=alice, json={"experiment_ids": [first]})
    duplicate = client.post("/experiments/compare", headers=alice, json={"experiment_ids": [first, first]})
    assert one.status_code == 422
    assert duplicate.status_code == 422


def test_private_experiments_cannot_be_compared_by_others(client, alice, bob):
    _, first, second = two_runs(client, alice, public=False)
    response = client.post("/experiments/compare", headers=bob, json={"experiment_ids": [first, second]})
    assert response.status_code == 404


def test_public_experiments_can_be_compared_signed_out(client, alice):
    _, first, second = two_runs(client, alice, public=True)
    response = client.post("/experiments/compare", json={"experiment_ids": [first, second]})
    assert response.status_code == 200
