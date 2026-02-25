import os
import sys

import pytest
from fastapi.testclient import TestClient
from jose import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import main as qna_main

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "a_very_secret_key_that_should_be_in_an_env_var")
AUTH_ALGORITHM = "HS256"


def _auth_headers(user_id: str) -> dict[str, str]:
    token = jwt.encode({"sub": user_id}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


class _FakeEmbeddingVector(list):
    def tolist(self) -> list[float]:
        return [float(value) for value in self]


class _FakeEmbeddingModel:
    def encode(self, _text: str) -> _FakeEmbeddingVector:
        return _FakeEmbeddingVector([0.01, 0.02, 0.03])


class _FakeSchemaAPI:
    def exists(self, _class_name: str) -> bool:
        return True

    def create_class(self, _document_schema: dict) -> None:
        return None


class _FakeDataObjectAPI:
    def __init__(self, store: list[dict]):
        self._store = store

    def create(self, *, data_object: dict, class_name: str, vector: list[float]) -> None:
        self._store.append(
            {
                "class_name": class_name,
                "data_object": data_object,
                "vector": vector,
            }
        )


class _FakeQueryBuilder:
    def __init__(self, store: list[dict]):
        self._store = store
        self._user_filter: str | None = None
        self._limit = 5

    def get(self, _class_name: str, _fields: list[str]):
        return self

    def with_near_vector(self, _payload: dict):
        return self

    def with_where(self, payload: dict):
        self._user_filter = str(payload.get("valueText"))
        return self

    def with_limit(self, limit: int):
        self._limit = limit
        return self

    def with_additional(self, _fields: list[str]):
        return self

    def do(self) -> dict:
        hits = []
        for item in self._store:
            data_object = item["data_object"]
            if data_object.get("user_id") != self._user_filter:
                continue
            hits.append(
                {
                    "document_id": data_object.get("document_id"),
                    "filename": data_object.get("filename"),
                    "content": data_object.get("content"),
                    "_additional": {"distance": 0.1234},
                }
            )
        return {"data": {"Get": {"DocumentChunk": hits[: self._limit]}}}


class _FakeQueryAPI:
    def __init__(self, store: list[dict]):
        self._store = store

    def get(self, class_name: str, fields: list[str]) -> _FakeQueryBuilder:
        return _FakeQueryBuilder(self._store).get(class_name, fields)


class _FakeWeaviateClient:
    def __init__(self):
        self._store: list[dict] = []
        self.schema = _FakeSchemaAPI()
        self.data_object = _FakeDataObjectAPI(self._store)
        self.query = _FakeQueryAPI(self._store)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    fake_client = _FakeWeaviateClient()
    fake_embedding_model = _FakeEmbeddingModel()
    monkeypatch.setattr(qna_main, "_weaviate_client", fake_client)
    monkeypatch.setattr(qna_main, "_embedding_model", fake_embedding_model)
    monkeypatch.setattr(qna_main, "_get_weaviate_client", lambda: fake_client)
    monkeypatch.setattr(qna_main, "_get_embedding_model", lambda: fake_embedding_model)
    with TestClient(qna_main.app) as test_client:
        yield test_client


def test_search_requires_auth(client: TestClient):
    response = client.post("/search", json={"query": "coffee"})
    assert response.status_code == 401


def test_index_requires_auth(client: TestClient):
    response = client.post(
        "/index",
        json={
            "document_id": "doc-no-auth",
            "filename": "missing-auth.pdf",
            "text_content": "No auth should be rejected",
        },
    )
    assert response.status_code == 401


def test_index_and_search_are_scoped_by_authenticated_user(client: TestClient):
    user_a = "alice@example.com"
    user_b = "bob@example.com"

    index_response = client.post(
        "/index",
        headers=_auth_headers(user_a),
        json={
            "document_id": "doc-alice-1",
            "filename": "alice-receipt.pdf",
            "text_content": "Coffee expenses for February",
            # This should be ignored. User identity must come only from JWT.
            "user_id": "malicious-overwrite",
        },
    )
    assert index_response.status_code == 200

    bob_search_response = client.post(
        "/search",
        headers=_auth_headers(user_b),
        json={"query": "coffee"},
    )
    assert bob_search_response.status_code == 200
    assert bob_search_response.json() == []

    alice_search_response = client.post(
        "/search",
        headers=_auth_headers(user_a),
        json={"query": "coffee"},
    )
    assert alice_search_response.status_code == 200
    payload = alice_search_response.json()
    assert len(payload) == 1
    assert payload[0]["document_id"] == "doc-alice-1"
    assert payload[0]["filename"] == "alice-receipt.pdf"
