import uuid
import datetime
import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["AUTH_SECRET_KEY"] = "test-secret"
os.environ["INTERNAL_SERVICE_SECRET"] = "test-internal-secret"

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
    async def override_get_db():
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=None)
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data.get("database") == "connected"
    finally:
        app.dependency_overrides.pop(get_db, None)


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

@patch("app.main.post_audit_event", new_callable=AsyncMock)
@patch("app.main.ocr_processing_task")
@patch("app.main.s3_client")
@patch("app.main.crud")
def test_upload_document_success(mock_crud, mock_s3, mock_ocr_task, mock_post_audit):
    fake_doc = _fake_document()
    mock_crud.total_file_size_bytes_for_user = AsyncMock(return_value=0)
    mock_crud.count_documents_for_user = AsyncMock(return_value=0)
    mock_crud.create_document = AsyncMock(return_value=fake_doc)
    mock_s3.upload_fileobj = MagicMock()
    mock_ocr_task.delay = MagicMock()
    mock_post_audit.return_value = True

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    import app.main as main_mod

    prev_compliance = main_mod.COMPLIANCE_SERVICE_URL
    main_mod.COMPLIANCE_SERVICE_URL = "http://compliance-service:80"
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
        mock_post_audit.assert_awaited_once()
        aud = mock_post_audit.await_args.kwargs
        assert aud["action"] == "document_uploaded"
        assert aud["user_id"] == USER_ID
        assert aud["details"]["filename"] == "receipt.pdf"
    finally:
        main_mod.COMPLIANCE_SERVICE_URL = prev_compliance
        app.dependency_overrides.clear()


@patch("app.main.ocr_processing_task")
@patch("app.main.s3_client")
@patch("app.main.crud")
def test_upload_document_s3_failure(mock_crud, mock_s3, mock_ocr_task):
    from botocore.exceptions import ClientError

    mock_crud.total_file_size_bytes_for_user = AsyncMock(return_value=0)
    mock_crud.count_documents_for_user = AsyncMock(return_value=0)
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


def test_list_documents_requires_authentication():
    client = TestClient(app)
    response = client.get("/documents")
    assert response.status_code == 401


def test_upload_requires_authentication():
    client = TestClient(app)
    response = client.post(
        "/documents/upload",
        files={"file": ("receipt.pdf", b"x", "application/pdf")},
    )
    assert response.status_code == 401


@patch("app.main.post_audit_event", new_callable=AsyncMock)
@patch("app.main.crud")
def test_review_document_posts_compliance_audit(mock_crud, mock_post_audit):
    mock_post_audit.return_value = True
    doc_id = uuid.uuid4()
    reviewed = MagicMock(
        id=doc_id,
        user_id=USER_ID,
        filename="receipt.pdf",
        filepath=f"{USER_ID}/{doc_id}.pdf",
        status="completed",
        uploaded_at=datetime.datetime.now(datetime.UTC),
        extracted_data={"review_status": "ignored", "total_amount": 10.0},
    )
    mock_crud.update_document_review = AsyncMock(return_value=reviewed)

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db
    import app.main as main_mod

    prev = main_mod.COMPLIANCE_SERVICE_URL
    main_mod.COMPLIANCE_SERVICE_URL = "http://compliance:80"
    try:
        client = TestClient(app)
        response = client.patch(
            f"/documents/{doc_id}/review",
            headers=AUTH_HEADER,
            json={"review_status": "ignored"},
        )
    finally:
        main_mod.COMPLIANCE_SERVICE_URL = prev
        app.dependency_overrides.clear()

    assert response.status_code == 200
    mock_post_audit.assert_awaited_once()
    aud = mock_post_audit.await_args.kwargs
    assert aud["action"] == "document_review_updated"
    assert aud["details"]["review_status"] == "ignored"
