"""AI endpoints: what is sent to Gemini, output validation and error mapping.

Gemini is faked (see conftest.FakeGemini); no real API calls are made.
"""
import json

import httpx
from google.genai._gaos.lib.compat_errors import APITimeoutError

from tests.conftest import train, upload


def experiment(client, headers, public=False):
    dataset_id = upload(client, headers, public=public).json()["dataset_id"]
    return dataset_id, train(client, headers, dataset_id, save_model=False).json()["experiment_id"]


def test_explain_experiment_returns_the_summary(client, alice, gemini):
    _, experiment_id = experiment(client, alice)
    gemini.reply({"summary": "The forest separates the classes well."})

    response = client.post(f"/experiments/{experiment_id}/explanation", headers=alice)

    assert response.status_code == 200
    assert response.json() == {"summary": "The forest separates the classes well."}
    sent = gemini.calls[0]["context"]
    assert sent["algorithm"] == "Random Forest"
    assert "accuracy" in sent["results"]


def test_dataset_explanation_sends_the_profile_not_the_rows(client, alice, gemini):
    dataset_id, _ = experiment(client, alice)
    gemini.reply({"summary": "80 rows, one missing value."})

    assert client.post(f"/datasets/{dataset_id}/explanation", headers=alice).status_code == 200

    sent = gemini.calls[0]["context"]
    assert set(sent) == {
        "rows", "cols", "column_names", "column_types",
        "missing_values", "total_missing_values", "duplicate_rows",
    }


def test_valid_recommendations_are_returned(client, alice, gemini):
    _, experiment_id = experiment(client, alice)
    gemini.reply({
        "summary": "Try boosting.",
        "recommendations": [{
            "algorithm": "Gradient Boosting",
            "parameters": {"n_estimators": 150},
            "reason": "Often stronger on tabular data.",
            "uncertainty": "Small dataset.",
        }],
    })

    response = client.post(f"/experiments/{experiment_id}/recommendations", headers=alice)

    assert response.status_code == 200
    recommendation = response.json()["recommendations"][0]
    # Missing parameters are filled with validated defaults.
    assert recommendation["parameters"] == {"n_estimators": 150, "learning_rate": 0.1, "max_depth": 3}


def test_unsupported_recommended_algorithm_is_rejected(client, alice, gemini):
    _, experiment_id = experiment(client, alice)
    gemini.reply({
        "summary": "Try a network.",
        "recommendations": [{"algorithm": "Neural Net", "parameters": {}, "reason": "-", "uncertainty": "-"}],
    })

    response = client.post(f"/experiments/{experiment_id}/recommendations", headers=alice)
    assert response.status_code == 502


def test_out_of_range_recommended_parameter_is_rejected(client, alice, gemini):
    _, experiment_id = experiment(client, alice)
    gemini.reply({
        "summary": "More trees.",
        "recommendations": [{
            "algorithm": "Random Forest", "parameters": {"n_estimators": 100000}, "reason": "-", "uncertainty": "-",
        }],
    })

    response = client.post(f"/experiments/{experiment_id}/recommendations", headers=alice)
    assert response.status_code == 502


def test_malformed_ai_output_returns_502(client, alice, gemini):
    _, experiment_id = experiment(client, alice)
    gemini.fail(json.JSONDecodeError("bad json", "", 0))

    response = client.post(f"/experiments/{experiment_id}/explanation", headers=alice)
    assert response.status_code == 502


def test_ai_timeout_returns_504(client, alice, gemini):
    _, experiment_id = experiment(client, alice)
    gemini.fail(APITimeoutError(request=httpx.Request("POST", "https://example.invalid")))

    response = client.post(f"/experiments/{experiment_id}/explanation", headers=alice)
    assert response.status_code == 504


def test_ai_requires_sign_in_even_for_public_items(client, alice, gemini):
    dataset_id, experiment_id = experiment(client, alice, public=True)

    assert client.post(f"/experiments/{experiment_id}/explanation").status_code == 401
    assert client.post(f"/datasets/{dataset_id}/explanation").status_code == 401
    assert client.post(f"/experiments/{experiment_id}/recommendations").status_code == 401
    assert gemini.calls == []
