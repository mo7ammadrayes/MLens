"""Uploading, inspecting and cleaning datasets."""
from tests.conftest import classification_csv, upload


def test_upload_registers_and_stores_the_csv(client, alice, storage):
    response = upload(client, alice, name="students")

    assert response.status_code == 201
    dataset = response.json()
    assert dataset["name"] == "students"
    assert (dataset["rows"], dataset["cols"]) == (80, 4)
    assert dataset["is_public"] is False
    assert len(storage.files) == 1
    assert next(iter(storage.files.values())) == classification_csv().encode()


def test_non_csv_file_is_rejected(client, alice, storage):
    response = upload(client, alice, filename="data.txt")
    assert response.status_code == 422
    assert storage.files == {}


def test_empty_csv_is_rejected(client, alice):
    assert upload(client, alice, csv="").status_code == 422


def test_duplicate_name_for_same_user_is_rejected(client, alice, bob):
    assert upload(client, alice, name="students").status_code == 201
    assert upload(client, alice, name="students").status_code == 409
    # Another user may use the same name.
    assert upload(client, bob, name="students").status_code == 201


def test_inspect_reports_types_missing_values_and_duplicates(client, alice):
    dataset_id = upload(client, alice).json()["dataset_id"]

    profile = client.get(f"/datasets/{dataset_id}/inspect", headers=alice).json()

    assert profile["rows"] == 80
    assert profile["column_names"] == ["hours", "attendance", "school", "passed"]
    assert profile["missing_values"]["attendance"] == 1
    assert profile["total_missing_values"] == 1


def test_preview_returns_first_rows_with_missing_as_null(client, alice):
    dataset_id = upload(client, alice).json()["dataset_id"]

    preview = client.get(f"/datasets/{dataset_id}/preview", headers=alice).json()

    assert preview["total_rows"] == 80
    assert len(preview["rows"]) == 15
    assert preview["rows"][4][1] is None  # the missing attendance value (CSV line 5)


def test_cleaning_creates_a_new_dataset_and_keeps_the_original(client, alice):
    original = upload(client, alice).json()

    response = client.post(
        f"/datasets/{original['dataset_id']}/clean",
        headers=alice,
        json={"name": "students_clean", "missing_strategy": "drop"},
    )

    assert response.status_code == 201
    cleaned = response.json()
    assert cleaned["dataset_id"] != original["dataset_id"]
    assert cleaned["rows"] == 79
    assert cleaned["cleaning_metadata"]["missing_values_after"] == 0
    assert client.get(f"/datasets/{original['dataset_id']}", headers=alice).json()["rows"] == 80
