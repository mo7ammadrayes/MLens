"""Shared test setup.

The tests never touch real services:
- Postgres  -> a temporary SQLite database, recreated for every test
- Supabase Storage -> an in-memory dict
- Supabase Auth    -> access tokens signed here with a throwaway key
- Gemini           -> a fake that returns whatever each test queues up

The environment variables below are set before any backend module is
imported, so your real .env (which load_dotenv never overrides) is ignored.
"""
import os
import tempfile
import time
import uuid
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="mlens-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["SUPABASE_URL"] = "https://test-project.supabase.co"
os.environ["SUPABASE_SECRET_KEY"] = "test-secret-key"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ.pop("SUPABASE_JWT_SECRET", None)
os.environ.pop("CORS_ORIGINS", None)

import jwt  # noqa: E402
import pytest  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.auth.supabase_jwt as supabase_jwt  # noqa: E402
import backend.features.ai.service as ai_service  # noqa: E402
import backend.features.dataset.router as dataset_router  # noqa: E402
import backend.storage.service as storage_service  # noqa: E402
from backend.database.models import Base  # noqa: E402
from backend.database.session import engine  # noqa: E402
from backend.main import app  # noqa: E402

ISSUER = "https://test-project.supabase.co/auth/v1"
SIGNING_KEY = ec.generate_private_key(ec.SECP256R1())


# ---------------------------------------------------------------- fakes

class FakeStorage:
    """Mimics client.storage.from_(bucket).upload/download/remove."""

    def __init__(self):
        self.files: dict[tuple[str, str], bytes] = {}

    @property
    def storage(self):
        return self

    def from_(self, bucket):
        files = self.files

        class Bucket:
            def upload(self, path, file, file_options=None):
                files[(bucket, path)] = file

            def download(self, path):
                if (bucket, path) not in files:
                    raise FileNotFoundError(path)
                return files[(bucket, path)]

            def remove(self, paths):
                for path in paths:
                    files.pop((bucket, path), None)

        return Bucket()


class FakeGemini:
    """Stands in for request_structured_output.

    Tests queue responses with .reply(...) or errors with .fail(...); every
    call is recorded in .calls so tests can check what was sent.
    """

    def __init__(self):
        self.calls: list[dict] = []
        self.responses: list = []

    def reply(self, data: dict):
        self.responses.append(data)

    def fail(self, error: Exception):
        self.responses.append(error)

    def __call__(self, *, instructions, context, response_schema):
        self.calls.append({"instructions": instructions, "context": context})
        if not self.responses:
            raise AssertionError("Gemini was called but no response was queued")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response_schema.model_validate(response)


class _FakeJWKS:
    def get_signing_key_from_jwt(self, token):
        class Key:
            key = SIGNING_KEY.public_key()

        return Key()


# ------------------------------------------------------------- fixtures

@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    # IDs restart in each fresh database, so per-dataset caches must too.
    dataset_router._INSPECTION_CACHE.clear()
    dataset_router._PREVIEW_CACHE.clear()
    yield


@pytest.fixture(autouse=True)
def storage(monkeypatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr(storage_service, "get_storage_client", lambda: fake)
    return fake


@pytest.fixture(autouse=True)
def gemini(monkeypatch) -> FakeGemini:
    fake = FakeGemini()
    monkeypatch.setattr(ai_service, "request_structured_output", fake)
    return fake


@pytest.fixture(autouse=True)
def fake_jwks(monkeypatch):
    monkeypatch.setattr(supabase_jwt, "_jwks_client", lambda: _FakeJWKS())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def make_token(
    email: str,
    *,
    sub: str | None = None,
    name: str | None = None,
    verified: bool = True,
    expires_in: int = 3600,
    audience: str = "authenticated",
    role: str = "authenticated",
) -> str:
    now = int(time.time())
    claims = {
        "sub": sub or str(uuid.uuid5(uuid.NAMESPACE_URL, email)),
        "email": email,
        "aud": audience,
        "role": role,
        "iss": ISSUER,
        "iat": now,
        "exp": now + expires_in,
        "user_metadata": {
            "name": name or email.split("@")[0].title(),
            "email_verified": verified,
        },
    }
    return jwt.encode(claims, SIGNING_KEY, algorithm="ES256", headers={"kid": "test"})


def auth(email: str, **kwargs) -> dict:
    return {"Authorization": f"Bearer {make_token(email, **kwargs)}"}


@pytest.fixture
def alice() -> dict:
    return auth("alice@example.com")


@pytest.fixture
def bob() -> dict:
    return auth("bob@example.com")


# ---------------------------------------------------------------- data

def classification_csv(rows: int = 80) -> str:
    """Numeric + text features, a two-class target and one missing value."""
    lines = ["hours,attendance,school,passed"]
    for i in range(rows):
        hours = (i * 7) % 11
        attendance = 50 + (i * 13) % 50
        school = "public" if i % 3 else "private"
        passed = "yes" if hours + attendance / 20 > 8 else "no"
        lines.append(f"{hours},{attendance},{school},{passed}")
    lines[5] = "3,,public,no"  # a missing attendance value
    return "\n".join(lines) + "\n"


def regression_csv(rows: int = 80) -> str:
    lines = ["hours,attendance,score"]
    for i in range(rows):
        hours = (i * 7) % 11
        attendance = 50 + (i * 13) % 50
        score = 20 + hours * 5 + attendance * 0.4 + (i % 5)
        lines.append(f"{hours},{attendance},{score:.1f}")
    return "\n".join(lines) + "\n"


def upload(client, headers, name="students", csv=None, public=False, filename="data.csv"):
    return client.post(
        "/datasets",
        headers=headers,
        data={"name": name, "is_public": str(public).lower()},
        files={"file": (filename, csv if csv is not None else classification_csv(), "text/csv")},
    )


def train(client, headers, dataset_id, **overrides):
    body = {
        "dataset_id": dataset_id,
        "target": "passed",
        "features": ["hours", "attendance", "school"],
        "categorical": ["school"],
        "train_size": 0.75,
        "task_type": "classification",
        "algorithm": "Random Forest",
        "model_parameters": {"n_estimators": 20},
        "save_model": True,
    }
    body.update(overrides)
    return client.post("/models/train", headers=headers, json=body)
