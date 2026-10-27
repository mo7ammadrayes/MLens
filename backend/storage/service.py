from backend.storage.client import get_storage_client


def upload_file(
    bucket: str,
    path: str,
    contents: bytes,
    content_type: str,
) -> None:
    client = get_storage_client()

    client.storage.from_(bucket).upload(
        path=path,
        file=contents,
        file_options={
            "content-type": content_type,
            "upsert": "false",
        },
    )


def download_file(bucket: str, path: str) -> bytes:
    client = get_storage_client()

    return client.storage.from_(bucket).download(path)


def delete_file(bucket: str, path: str) -> None:
    client = get_storage_client()

    client.storage.from_(bucket).remove([path])