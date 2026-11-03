"""Running saved models on new data, and saving/downloading the results."""
import csv
import io

from tests.conftest import train, upload


def make_model(client, headers, public=False):
    dataset_id = upload(client, headers, name="training", public=public).json()["dataset_id"]
    return train(client, headers, dataset_id, is_public=public).json()["model_id"]


def test_prediction_saves_a_downloadable_csv(client, alice):
    model_id = make_model(client, alice)
    new_data = upload(client, alice, name="new_students").json()["dataset_id"]

    response = client.post(
        "/predictions",
        headers=alice,
        json={"model_id": model_id, "dataset_id": new_data, "save_results": True},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["rows"] == 80 == len(result["predictions"])
    assert result["prediction_column"] == "prediction"

    listed = client.get("/predictions", headers=alice).json()
    assert [r["prediction_result_id"] for r in listed] == [result["prediction_result_id"]]

    download = client.get(f"/predictions/{result['prediction_result_id']}/download", headers=alice)
    assert download.status_code == 200
    rows = list(csv.DictReader(io.StringIO(download.text)))
    assert len(rows) == 80
    assert rows[0]["prediction"] in {"yes", "no"}


def test_prediction_without_saving_returns_values_only(client, alice):
    model_id = make_model(client, alice)
    data = upload(client, alice, name="new").json()["dataset_id"]

    result = client.post("/predictions", headers=alice, json={"model_id": model_id, "dataset_id": data}).json()

    assert result["prediction_result_id"] is None
    assert client.get("/predictions", headers=alice).json() == []


def test_missing_feature_column_is_rejected(client, alice):
    model_id = make_model(client, alice)
    data = upload(client, alice, name="wrong", csv="hours,school\n1,public\n2,private\n").json()["dataset_id"]

    response = client.post("/predictions", headers=alice, json={"model_id": model_id, "dataset_id": data})

    assert response.status_code == 422
    assert "attendance" in response.json()["detail"]


def test_others_can_use_a_public_model_but_not_a_private_one(client, alice, bob):
    public_model = make_model(client, alice, public=True)
    private_dataset = upload(client, alice, name="private_training").json()["dataset_id"]
    private_model = train(client, alice, private_dataset).json()["model_id"]
    bobs_data = upload(client, bob, name="bobs_data").json()["dataset_id"]

    ok = client.post("/predictions", headers=bob, json={"model_id": public_model, "dataset_id": bobs_data})
    denied = client.post("/predictions", headers=bob, json={"model_id": private_model, "dataset_id": bobs_data})

    assert ok.status_code == 200
    assert denied.status_code == 404


def test_prediction_results_are_private(client, alice, bob):
    model_id = make_model(client, alice)
    data = upload(client, alice, name="new").json()["dataset_id"]
    result_id = client.post(
        "/predictions", headers=alice,
        json={"model_id": model_id, "dataset_id": data, "save_results": True},
    ).json()["prediction_result_id"]

    assert client.get(f"/predictions/{result_id}/download", headers=bob).status_code == 404
    assert client.get("/predictions", headers=bob).json() == []
    assert client.post("/predictions", json={"model_id": model_id, "dataset_id": data}).status_code == 401
