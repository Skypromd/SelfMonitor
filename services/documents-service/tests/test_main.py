import uuid
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app, AUTH_SECRET_KEY, AUTH_ALGORITHM, get_current_user_id
from app.database import get_db

USER_ID = "user-123"


def _make_token(sub: str = USER_ID) -> str:
    return jwt.encode({"sub": sub}, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)


AUTH_HEADER = {"Authorization": f"Bearer {_make_token()}"}


def _fake_document(user_id: str = USER_ID, filename: str = "receipt.pdf"):
    doc_id = uuid.uuid4()
    return MagicMock(
        id=doc_id,
        user_id=user_id,
        filename=filename,
        filepath=f"{user_id}/{doc_id}.pdf",
        status="processing",
        uploaded_at=datetime.datetime.now(datetime.UTC),
        extracted_data=None,
    )


# --- Health endpoint ---

def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- Auth ---

def test_upload_returns_401_without_token():
    client = TestClient(app)
    response = client.post("/documents/upload", files={"file": ("f.pdf", b"data")})
    assert response.status_code == 401


def test_list_returns_401_without_token():
    client = TestClient(app)
    response = client.get("/documents")
    assert response.status_code == 401


def test_get_document_returns_401_without_token():
    client = TestClient(app)
    response = client.get(f"/documents/{uuid.uuid4()}")
    assert response.status_code == 401


# --- Upload document ---

@patch("app.main.ocr_processing_task")
@patch("app.main.s3_client")
@patch("app.main.crud")
def test_upload_document_success(mock_crud, mock_s3, mock_ocr_task):
    fake_doc = _fake_document()
    mock_crud.create_document = AsyncMock(return_value=fake_doc)
    mock_s3.upload_fileobj = MagicMock()
    mock_ocr_task.delay = MagicMock()

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        response = client.post(
            "/documents/upload",
            files={"file": ("receipt.pdf", b"fake-pdf-content", "application/pdf")},
            headers=AUTH_HEADER,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "receipt.pdf"
        assert data["status"] == "processing"

        mock_s3.upload_fileobj.assert_called_once()
        mock_crud.create_document.assert_awaited_once()
        mock_ocr_task.delay.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@patch("app.main.ocr_processing_task")
@patch("app.main.s3_client")
@patch("app.main.crud")
def test_upload_document_s3_failure(mock_crud, mock_s3, mock_ocr_task):
    from botocore.exceptions import ClientError

    mock_s3.upload_fileobj.side_effect = ClientError(
        {"Error": {"Code": "500", "Message": "S3 error"}}, "PutObject"
    )

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        response = client.post(
            "/documents/upload",
            files={"file": ("receipt.pdf", b"fake-pdf-content", "application/pdf")},
            headers=AUTH_HEADER,
        )
        assert response.status_code == 500
        assert "S3" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# --- List documents ---

@patch("app.main.crud")
def test_list_documents(mock_crud):
    fake_docs = [_fake_document(filename="a.pdf"), _fake_document(filename="b.pdf")]
    mock_crud.get_documents_by_user = AsyncMock(return_value=fake_docs)

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        response = client.get("/documents", headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["filename"] == "a.pdf"
    finally:
        app.dependency_overrides.clear()


# --- Get single document ---

@patch("app.main.crud")
def test_get_document_success(mock_crud):
    fake_doc = _fake_document()
    mock_crud.get_document_by_id = AsyncMock(return_value=fake_doc)

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        response = client.get(f"/documents/{fake_doc.id}", headers=AUTH_HEADER)
        assert response.status_code == 200
        assert response.json()["filename"] == "receipt.pdf"
    finally:
        app.dependency_overrides.clear()


@patch("app.main.crud")
def test_get_document_not_found(mock_crud):
    mock_crud.get_document_by_id = AsyncMock(return_value=None)

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        response = client.get(f"/documents/{uuid.uuid4()}", headers=AUTH_HEADER)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
