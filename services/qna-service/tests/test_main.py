import os
import sys
from unittest.mock import MagicMock, patch
import numpy as np

os.environ["AUTH_SECRET_KEY"] = "test-secret"

mock_weaviate = MagicMock()
mock_weaviate.Client.return_value = MagicMock()
mock_weaviate.AuthApiKey = MagicMock()
sys.modules.setdefault("weaviate", mock_weaviate)

mock_st_module = MagicMock()
mock_model_instance = MagicMock()
mock_model_instance.encode.return_value = np.zeros(384)
mock_st_module.SentenceTransformer.return_value = mock_model_instance
sys.modules.setdefault("sentence_transformers", mock_st_module)

from jose import jwt
from fastapi.testclient import TestClient

from app.main import app, AUTH_SECRET_KEY, AUTH_ALGORITHM

client = TestClient(app, raise_server_exceptions=False)

USER_ID = "user-42"
INTERNAL_TOKEN = "test-internal-token"


def _make_token(sub: str = USER_ID) -> str:
    return jwt.encode({"sub": sub}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)


AUTH_HEADER = {"Authorization": f"Bearer {_make_token()}"}


# --- Health endpoint ---

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- Auth ---

def test_search_returns_401_without_token():
    response = client.post("/search", json={"query": "coffee"})
    assert response.status_code == 401


def test_search_returns_401_with_bad_token():
    response = client.post(
        "/search",
        json={"query": "coffee"},
        headers={"Authorization": "Bearer invalid"},
    )
    assert response.status_code == 401


# --- Index endpoint ---

@patch("app.main.QNA_INTERNAL_TOKEN", INTERNAL_TOKEN)
@patch("app.main.client")
@patch("app.main.model")
def test_index_document_success(mock_model, mock_wv_client):
    mock_model.encode.return_value = MagicMock(tolist=MagicMock(return_value=[0.1] * 384))
    mock_wv_client.data_object.create.return_value = None

    response = client.post(
        "/index",
        json={
            "user_id": USER_ID,
            "document_id": "doc-1",
            "filename": "receipt.pdf",
            "text_content": "Coffee purchase at Costa",
        },
        headers={"X-Internal-Token": INTERNAL_TOKEN},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Document indexed successfully."
    mock_wv_client.data_object.create.assert_called_once()


def test_index_returns_401_with_wrong_internal_token():
    with patch("app.main.QNA_INTERNAL_TOKEN", INTERNAL_TOKEN):
        response = client.post(
            "/index",
            json={
                "user_id": USER_ID,
                "document_id": "doc-1",
                "filename": "receipt.pdf",
                "text_content": "data",
            },
            headers={"X-Internal-Token": "wrong-token"},
        )
        assert response.status_code == 401


def test_index_returns_401_without_internal_token():
    with patch("app.main.QNA_INTERNAL_TOKEN", INTERNAL_TOKEN):
        response = client.post(
            "/index",
            json={
                "user_id": USER_ID,
                "document_id": "doc-1",
                "filename": "receipt.pdf",
                "text_content": "data",
            },
        )
        assert response.status_code == 401


@patch("app.main.QNA_INTERNAL_TOKEN", None)
@patch("app.main.client")
def test_index_returns_503_when_token_not_configured(mock_wv_client):
    response = client.post(
        "/index",
        json={
            "user_id": USER_ID,
            "document_id": "doc-1",
            "filename": "receipt.pdf",
            "text_content": "data",
        },
        headers={"X-Internal-Token": "anything"},
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


@patch("app.main.client", None)
def test_index_returns_503_when_weaviate_unavailable():
    with patch("app.main.QNA_INTERNAL_TOKEN", INTERNAL_TOKEN):
        response = client.post(
            "/index",
            json={
                "user_id": USER_ID,
                "document_id": "doc-1",
                "filename": "receipt.pdf",
                "text_content": "data",
            },
            headers={"X-Internal-Token": INTERNAL_TOKEN},
        )
        assert response.status_code == 503


# --- Search endpoint ---

@patch("app.main.client")
@patch("app.main.model")
def test_search_documents_success(mock_model, mock_wv_client):
    mock_model.encode.return_value = MagicMock(tolist=MagicMock(return_value=[0.1] * 384))

    mock_query = MagicMock()
    mock_wv_client.query.get.return_value = mock_query
    mock_query.with_near_vector.return_value = mock_query
    mock_query.with_where.return_value = mock_query
    mock_query.with_limit.return_value = mock_query
    mock_query.with_additional.return_value = mock_query
    mock_query.do.return_value = {
        "data": {
            "Get": {
                "DocumentChunk": [
                    {
                        "document_id": "doc-1",
                        "filename": "receipt.pdf",
                        "content": "Coffee at Costa",
                        "_additional": {"distance": 0.15},
                    }
                ]
            }
        }
    }

    response = client.post(
        "/search",
        json={"query": "coffee"},
        headers=AUTH_HEADER,
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["document_id"] == "doc-1"
    assert results[0]["filename"] == "receipt.pdf"
    assert results[0]["score"] == 0.15


@patch("app.main.client")
@patch("app.main.model")
def test_search_returns_empty_list(mock_model, mock_wv_client):
    mock_model.encode.return_value = MagicMock(tolist=MagicMock(return_value=[0.1] * 384))

    mock_query = MagicMock()
    mock_wv_client.query.get.return_value = mock_query
    mock_query.with_near_vector.return_value = mock_query
    mock_query.with_where.return_value = mock_query
    mock_query.with_limit.return_value = mock_query
    mock_query.with_additional.return_value = mock_query
    mock_query.do.return_value = {"data": {"Get": {"DocumentChunk": []}}}

    response = client.post(
        "/search",
        json={"query": "nonexistent"},
        headers=AUTH_HEADER,
    )
    assert response.status_code == 200
    assert response.json() == []


@patch("app.main.client", None)
def test_search_returns_503_when_weaviate_unavailable():
    response = client.post(
        "/search",
        json={"query": "coffee"},
        headers=AUTH_HEADER,
    )
    assert response.status_code == 503


@patch("app.main.client", None)
def test_health_returns_503_when_weaviate_unavailable():
    response = client.get("/health")
    assert response.status_code == 503
