"""Login tokens and per-user access: the base everything else relies on."""
from tests.conftest import auth, upload


def test_missing_token_is_rejected(client):
    assert client.get("/datasets").status_code == 401


def test_expired_token_is_rejected(client):
    response = client.get("/datasets", headers=auth("alice@example.com", expires_in=-120))
    assert response.status_code == 401


def test_token_for_wrong_audience_is_rejected(client):
    response = client.get("/datasets", headers=auth("alice@example.com", audience="other"))
    assert response.status_code == 401


def test_first_request_creates_the_user(client, alice):
    me = client.get("/users/me", headers=alice).json()
    assert me["email"] == "alice@example.com"
    assert client.get("/users/me", headers=alice).json()["user_id"] == me["user_id"]


def test_users_only_see_their_own_private_datasets(client, alice, bob):
    dataset = upload(client, alice, public=False).json()

    assert client.get("/datasets", headers=bob).json() == []
    assert client.get(f"/datasets/{dataset['dataset_id']}", headers=bob).status_code == 404
    assert client.delete(f"/datasets/{dataset['dataset_id']}", headers=bob).status_code == 404


def test_public_dataset_is_readable_signed_out_but_not_downloadable(client, alice):
    dataset = upload(client, alice, public=True).json()
    dataset_id = dataset["dataset_id"]

    assert client.get(f"/datasets/{dataset_id}").status_code == 200
    assert client.get(f"/datasets/{dataset_id}/preview").status_code == 200
    assert client.get(f"/datasets/{dataset_id}/download").status_code == 401


def test_health_needs_no_sign_in_and_checks_the_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
