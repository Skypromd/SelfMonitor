import asyncio
import datetime
import hashlib
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

for parent in Path(__file__).resolve().parents:
    if (parent / "libs").exists():
        parent_str = str(parent)
        if parent_str not in sys.path:
            sys.path.append(parent_str)
        break

from libs.shared_auth.jwt_fastapi import build_jwt_auth_dependencies
from libs.shared_http.retry import get_json_with_retry, post_json_with_retry

DOCUMENTS_REVIEW_QUEUE_URL = os.getenv(
    "DOCUMENTS_REVIEW_QUEUE_URL",
    "http://documents-service/documents/review-queue",
)
TRANSACTIONS_RECEIPT_DRAFTS_URL = os.getenv(
    "TRANSACTIONS_RECEIPT_DRAFTS_URL",
    "http://transactions-service/transactions/receipt-drafts/unmatched",
)
TRANSACTIONS_ME_URL = os.getenv(
    "TRANSACTIONS_ME_URL",
    "http://transactions-service/transactions/me",
)
TAX_ENGINE_CALCULATE_URL = os.getenv(
    "TAX_ENGINE_CALCULATE_URL",
    "http://tax-engine/calculate",
)
DEFAULT_TAX_LOOKBACK_DAYS = int(os.getenv("AGENT_DEFAULT_TAX_LOOKBACK_DAYS", "365"))
AGENT_REDIS_URL = os.getenv("AGENT_REDIS_URL", "redis://redis:6379/0")
AGENT_SESSION_TTL_SECONDS = int(os.getenv("AGENT_SESSION_TTL_SECONDS", "86400"))
AGENT_CONFIRMATION_TOKEN_TTL_SECONDS = int(os.getenv("AGENT_CONFIRMATION_TOKEN_TTL_SECONDS", "900"))
AGENT_AUDIT_MAX_EVENTS = int(os.getenv("AGENT_AUDIT_MAX_EVENTS", "500"))
AGENT_AUDIT_TTL_SECONDS = int(os.getenv("AGENT_AUDIT_TTL_SECONDS", "604800"))
AGENT_WRITE_ACTIONS_ENABLED = os.getenv("AGENT_WRITE_ACTIONS_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DOCUMENTS_REVIEW_UPDATE_URL_TEMPLATE = os.getenv(
    "DOCUMENTS_REVIEW_UPDATE_URL_TEMPLATE",
    "http://documents-service/documents/{document_id}/review",
)
TRANSACTIONS_RECONCILE_URL_TEMPLATE = os.getenv(
    "TRANSACTIONS_RECONCILE_URL_TEMPLATE",
    "http://transactions-service/transactions/receipt-drafts/{draft_transaction_id}/reconcile",
)
TRANSACTIONS_IGNORE_URL_TEMPLATE = os.getenv(
    "TRANSACTIONS_IGNORE_URL_TEMPLATE",
    "http://transactions-service/transactions/receipt-drafts/{draft_transaction_id}/ignore",
)
TAX_CALCULATE_AND_SUBMIT_URL = os.getenv(
    "TAX_CALCULATE_AND_SUBMIT_URL",
    "http://tax-engine/calculate-and-submit",
)

get_bearer_token, get_current_user_id = build_jwt_auth_dependencies()

app = FastAPI(
    title="Agent Service",
    description="Self-Assessment Copilot with read-only guided actions.",
    version="1.0.0",
)


AgentIntent = Literal[
    "readiness_check",
    "ocr_review_assist",
    "reconciliation_assist",
    "tax_pre_submit",
]
INTENT_VALUES: tuple[AgentIntent, ...] = (
    "readiness_check",
    "ocr_review_assist",
    "reconciliation_assist",
    "tax_pre_submit",
)

_redis_client: Any | None = None
_in_memory_session_store: dict[str, dict[str, Any]] = {}
_in_memory_confirmation_store: dict[str, dict[str, Any]] = {}
_in_memory_audit_store: dict[str, list[dict[str, Any]]] = {}

WRITE_ACTION_ALLOWLIST: set[str] = {
    "documents.review_document",
    "transactions.reconcile_receipt_draft",
    "transactions.ignore_receipt_draft",
    "tax.calculate_and_submit",
}
UNTRUSTED_TEXT_MAX_LENGTH = int(os.getenv("AGENT_UNTRUSTED_TEXT_MAX_LENGTH", "300"))
PROMPT_INJECTION_PATTERN = re.compile(
    r"(?i)(ignore\s+(?:all\s+|any\s+)?(?:previous\s+|prior\s+)?instructions|"
    r"system\s+prompt|developer\s+message|"
    r"you\s+are\s+chatgpt|act\s+as\s+an?\s+assistant|"
    r"tool\s+call|function\s+call|"
    r"<script|```|jailbreak|do\s+anything\s+now)",
)
AGENT_ACTION_EXECUTIONS_TOTAL = Counter(
    "agent_action_executions_total",
    "Total confirmed action execution attempts.",
    labelnames=("action_id", "result"),
)
AGENT_HUMAN_OVERRIDE_ACTIONS_TOTAL = Counter(
    "agent_human_override_actions_total",
    "Total successful agent actions classified as human override operations.",
    labelnames=("action_id",),
)


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


class AgentEvidence(BaseModel):
    source_service: str
    source_endpoint: str
    record_ids: list[str] = Field(default_factory=list)
    summary: str


class AgentSuggestedAction(BaseModel):
    action_id: str
    label: str
    description: str
    requires_confirmation: bool = False
    action_payload: dict[str, Any] | None = None


class AgentChatResponse(BaseModel):
    session_id: str
    session_turn_count: int
    last_intent_from_memory: AgentIntent | None = None
    intent: AgentIntent
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_band: Literal["low", "medium", "high"]
    intent_reason: str
    answer: str
    evidence: list[AgentEvidence]
    suggested_actions: list[AgentSuggestedAction]


class AgentConfirmationTokenRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    action_id: str = Field(min_length=1, max_length=128)
    action_payload: dict[str, Any] = Field(default_factory=dict)


class AgentConfirmationTokenResponse(BaseModel):
    session_id: str
    action_id: str
    confirmation_token: str
    expires_at: datetime.datetime


class AgentConfirmationValidationRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    action_id: str = Field(min_length=1, max_length=128)
    confirmation_token: str = Field(min_length=1, max_length=256)
    action_payload: dict[str, Any] = Field(default_factory=dict)
    consume: bool = True


class AgentConfirmationValidationResponse(BaseModel):
    valid: bool
    reason: str | None = None
    action_id: str
    session_id: str
    expires_at: datetime.datetime | None = None
    consumed: bool = False


class AgentExecuteActionRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    action_id: str = Field(min_length=1, max_length=128)
    confirmation_token: str = Field(min_length=1, max_length=256)
    action_payload: dict[str, Any] = Field(default_factory=dict)


class AgentExecuteActionResponse(BaseModel):
    session_id: str
    action_id: str
    executed: bool
    valid_confirmation: bool
    confirmation_reason: str | None = None
    downstream_endpoint: str | None = None
    downstream_status_code: int | None = None
    result: dict[str, Any] | list[Any] | None = None
    message: str


class AgentToolCallLog(BaseModel):
    service: str
    endpoint: str
    status: Literal["success", "error"]
    error: str | None = None


class AgentAuditEvent(BaseModel):
    event_id: str
    timestamp: datetime.datetime
    event_type: str
    session_id: str | None = None
    action_id: str | None = None
    prompt_hash: str | None = None
    tool_calls: list[AgentToolCallLog] = Field(default_factory=list)
    payload_summary: dict[str, Any] = Field(default_factory=dict)
    action_result: dict[str, Any] = Field(default_factory=dict)


class AgentAuditLogResponse(BaseModel):
    total: int
    items: list[AgentAuditEvent]


def _to_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _extract_record_ids(items: list[dict[str, Any]], key: str, limit: int = 5) -> list[str]:
    ids: list[str] = []
    for item in items:
        value = item.get(key)
        if value is None:
            continue
        value_text = str(value).strip()
        if not value_text:
            continue
        ids.append(value_text)
        if len(ids) >= limit:
            break
    return ids


def _get_redis_client() -> Any | None:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis.asyncio as redis
    except ModuleNotFoundError:
        return None
    _redis_client = redis.from_url(AGENT_REDIS_URL, decode_responses=True)
    return _redis_client


def _build_session_key(user_id: str, session_id: str) -> str:
    return f"agent-session:{user_id}:{session_id}"


def _build_confirmation_key(user_id: str, confirmation_token: str) -> str:
    return f"agent-confirmation:{user_id}:{confirmation_token}"


def _build_audit_key(user_id: str) -> str:
    return f"agent-audit:{user_id}"


def _hash_action_payload(payload: dict[str, Any]) -> str:
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def _hash_prompt_text(prompt: str) -> str:
    normalized = prompt.strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize_untrusted_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.replace("\r", "\n")
    normalized = "".join(
        character if character.isprintable() or character in {"\n", "\t"} else " "
        for character in normalized
    )
    normalized = " ".join(normalized.split())
    if len(normalized) > UNTRUSTED_TEXT_MAX_LENGTH:
        normalized = normalized[:UNTRUSTED_TEXT_MAX_LENGTH]
    return normalized.strip()


def _sanitize_untrusted_document_text(value: Any) -> tuple[str, bool]:
    normalized = _normalize_untrusted_text(value)
    if not normalized:
        return "", False
    if PROMPT_INJECTION_PATTERN.search(normalized):
        return "[redacted suspicious OCR text]", True
    return normalized, False


def _scan_document_context_for_prompt_injection(items: list[dict[str, Any]]) -> tuple[int, int]:
    scanned_fields = 0
    suspicious_fields = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        extracted_data_raw = item.get("extracted_data")
        extracted_data = extracted_data_raw if isinstance(extracted_data_raw, dict) else {}
        candidates = (
            item.get("filename"),
            extracted_data.get("vendor_name"),
            extracted_data.get("suggested_category"),
            extracted_data.get("expense_article"),
            extracted_data.get("review_reason"),
            extracted_data.get("text_excerpt"),
        )
        for candidate in candidates:
            sanitized, flagged = _sanitize_untrusted_document_text(candidate)
            if sanitized:
                scanned_fields += 1
            if flagged:
                suspicious_fields += 1
    return scanned_fields, suspicious_fields


def _parse_datetime_iso(value: Any) -> datetime.datetime | None:
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized.replace("Z", "+00:00")
        try:
            return datetime.datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


async def _load_session_memory(user_id: str, session_id: str) -> dict[str, Any]:
    key = _build_session_key(user_id, session_id)
    client = _get_redis_client()
    if client is not None:
        try:
            payload_raw = await client.get(key)
            if payload_raw:
                payload = json.loads(payload_raw)
                if isinstance(payload, dict):
                    _in_memory_session_store[key] = payload
                    return payload
        except Exception:
            pass
    if key in _in_memory_session_store:
        return _in_memory_session_store[key]
    return {"turns": [], "last_intent": None}


async def _save_session_memory(user_id: str, session_id: str, memory: dict[str, Any]) -> None:
    key = _build_session_key(user_id, session_id)
    _in_memory_session_store[key] = memory
    client = _get_redis_client()
    if client is None:
        return
    try:
        await client.set(key, json.dumps(memory, ensure_ascii=False), ex=AGENT_SESSION_TTL_SECONDS)
    except Exception:
        pass


async def _save_confirmation_record(user_id: str, confirmation_token: str, payload: dict[str, Any]) -> None:
    key = _build_confirmation_key(user_id, confirmation_token)
    _in_memory_confirmation_store[key] = payload
    client = _get_redis_client()
    if client is None:
        return
    try:
        await client.set(
            key,
            json.dumps(payload, ensure_ascii=False),
            ex=AGENT_CONFIRMATION_TOKEN_TTL_SECONDS,
        )
    except Exception:
        pass


async def _load_confirmation_record(user_id: str, confirmation_token: str) -> dict[str, Any] | None:
    key = _build_confirmation_key(user_id, confirmation_token)
    client = _get_redis_client()
    if client is not None:
        try:
            payload_raw = await client.get(key)
            if payload_raw:
                payload = json.loads(payload_raw)
                if isinstance(payload, dict):
                    _in_memory_confirmation_store[key] = payload
                    return payload
        except Exception:
            pass

    payload = _in_memory_confirmation_store.get(key)
    if payload is None:
        return None

    expires_at = _parse_datetime_iso(payload.get("expires_at"))
    if expires_at is None:
        return None
    now = datetime.datetime.now(datetime.UTC)
    if expires_at < now:
        _in_memory_confirmation_store.pop(key, None)
        return None
    return payload


async def _append_audit_event(user_id: str, event: AgentAuditEvent) -> None:
    key = _build_audit_key(user_id)
    event_payload = event.model_dump(mode="json")

    in_memory_rows = _in_memory_audit_store.get(key, [])
    in_memory_rows.append(event_payload)
    if len(in_memory_rows) > AGENT_AUDIT_MAX_EVENTS:
        in_memory_rows = in_memory_rows[-AGENT_AUDIT_MAX_EVENTS:]
    _in_memory_audit_store[key] = in_memory_rows

    client = _get_redis_client()
    if client is None:
        return
    try:
        await client.rpush(key, json.dumps(event_payload, ensure_ascii=False))
        await client.ltrim(key, -AGENT_AUDIT_MAX_EVENTS, -1)
        await client.expire(key, AGENT_AUDIT_TTL_SECONDS)
    except Exception:
        pass


async def _load_audit_events(user_id: str, limit: int) -> list[AgentAuditEvent]:
    key = _build_audit_key(user_id)
    client = _get_redis_client()
    if client is not None:
        try:
            raw_items = await client.lrange(key, -limit, -1)
            events: list[AgentAuditEvent] = []
            for raw in raw_items:
                try:
                    payload = json.loads(raw)
                except (TypeError, json.JSONDecodeError):
                    continue
                if isinstance(payload, dict):
                    events.append(AgentAuditEvent(**payload))
            if events:
                return list(reversed(events))
        except Exception:
            pass

    in_memory_items = _in_memory_audit_store.get(key, [])
    sliced = in_memory_items[-limit:]
    events: list[AgentAuditEvent] = []
    for payload in sliced:
        if isinstance(payload, dict):
            events.append(AgentAuditEvent(**payload))
    return list(reversed(events))


def _confidence_band(value: float) -> Literal["low", "medium", "high"]:
    if value >= 0.85:
        return "high"
    if value >= 0.7:
        return "medium"
    return "low"


def _detect_intent(message: str, last_intent: AgentIntent | None = None) -> tuple[AgentIntent, float, str]:
    normalized = message.lower()
    if normalized in {"continue", "continue.", "дальше", "продолжай", "go on"} and last_intent is not None:
        return last_intent, 0.71, "Continued prior intent from session memory."
    if any(keyword in normalized for keyword in ("hmrc", "tax", "налог", "декларац", "submission")):
        return "tax_pre_submit", 0.89, "Detected tax/HMRC submission wording."
    if any(keyword in normalized for keyword in ("reconcile", "match", "duplicate", "сопостав", "дубликат")):
        return "reconciliation_assist", 0.86, "Detected reconciliation or duplicate-resolution wording."
    if any(keyword in normalized for keyword in ("ocr", "receipt", "чек", "документ", "review")):
        return "ocr_review_assist", 0.84, "Detected OCR/document review wording."
    if any(keyword in normalized for keyword in ("readiness", "готов", "mortgage", "ипотек", "pack")):
        return "readiness_check", 0.82, "Detected readiness or mortgage-pack wording."
    return "readiness_check", 0.60, "No explicit keyword match; used default readiness intent."


def _ensure_supported_write_action(action_id: str) -> None:
    if action_id not in WRITE_ACTION_ALLOWLIST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported action_id '{action_id}'",
        )


def _validate_action_payload_shape(action_id: str, action_payload: dict[str, Any]) -> None:
    if action_id == "transactions.ignore_receipt_draft":
        required = {"draft_transaction_id"}
        allowed = required
    elif action_id == "transactions.reconcile_receipt_draft":
        required = {"draft_transaction_id", "target_transaction_id"}
        allowed = required
    elif action_id == "tax.calculate_and_submit":
        required = {"start_date", "end_date", "jurisdiction"}
        allowed = required
    elif action_id == "documents.review_document":
        required = {"document_id"}
        allowed = {
            "document_id",
            "review_payload",
            "total_amount",
            "vendor_name",
            "transaction_date",
            "suggested_category",
            "expense_article",
            "is_potentially_deductible",
            "review_status",
            "review_notes",
        }
    else:
        return

    payload_keys = set(action_payload.keys())
    missing = sorted(required - payload_keys)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required payload fields: {', '.join(missing)}",
        )
    unexpected = sorted(payload_keys - allowed)
    if unexpected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unexpected payload fields: {', '.join(unexpected)}",
        )
    if action_id == "documents.review_document" and "review_payload" in action_payload:
        review_payload = action_payload.get("review_payload")
        if not isinstance(review_payload, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="review_payload must be an object",
            )
        allowed_review_keys = {
            "total_amount",
            "vendor_name",
            "transaction_date",
            "suggested_category",
            "expense_article",
            "is_potentially_deductible",
            "review_status",
            "review_notes",
        }
        review_payload_keys = set(review_payload.keys())
        unexpected_review = sorted(review_payload_keys - allowed_review_keys)
        if unexpected_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unexpected review_payload fields: {', '.join(unexpected_review)}",
            )


def _is_human_override_action(action_id: str, action_payload: dict[str, Any]) -> bool:
    if action_id == "transactions.ignore_receipt_draft":
        return True
    if action_id != "documents.review_document":
        return False
    review_payload = action_payload.get("review_payload")
    if isinstance(review_payload, dict):
        status_value = str(review_payload.get("review_status") or "").strip().lower()
    else:
        status_value = str(action_payload.get("review_status") or "").strip().lower()
    return status_value in {"corrected", "ignored"}


def _build_confirmation_validation_response(
    *,
    valid: bool,
    session_id: str,
    action_id: str,
    reason: str | None = None,
    expires_at: datetime.datetime | None = None,
    consumed: bool = False,
) -> AgentConfirmationValidationResponse:
    return AgentConfirmationValidationResponse(
        valid=valid,
        reason=reason,
        action_id=action_id,
        session_id=session_id,
        expires_at=expires_at,
        consumed=consumed,
    )


async def _validate_confirmation_token_for_action(
    *,
    user_id: str,
    session_id: str,
    action_id: str,
    confirmation_token: str,
    action_payload: dict[str, Any],
    consume: bool,
) -> AgentConfirmationValidationResponse:
    record = await _load_confirmation_record(user_id, confirmation_token)
    if record is None:
        return _build_confirmation_validation_response(
            valid=False,
            reason="token_not_found_or_expired",
            action_id=action_id,
            session_id=session_id,
        )

    expires_at = _parse_datetime_iso(record.get("expires_at"))
    if expires_at is None:
        return _build_confirmation_validation_response(
            valid=False,
            reason="token_not_found_or_expired",
            action_id=action_id,
            session_id=session_id,
        )

    if str(record.get("session_id") or "") != session_id:
        return _build_confirmation_validation_response(
            valid=False,
            reason="session_mismatch",
            action_id=action_id,
            session_id=session_id,
            expires_at=expires_at,
        )
    if str(record.get("action_id") or "") != action_id:
        return _build_confirmation_validation_response(
            valid=False,
            reason="action_mismatch",
            action_id=action_id,
            session_id=session_id,
            expires_at=expires_at,
        )
    if bool(record.get("consumed")):
        return _build_confirmation_validation_response(
            valid=False,
            reason="token_already_used",
            action_id=action_id,
            session_id=session_id,
            expires_at=expires_at,
        )

    expected_payload_hash = str(record.get("action_payload_hash") or "")
    provided_payload_hash = _hash_action_payload(action_payload)
    if expected_payload_hash != provided_payload_hash:
        return _build_confirmation_validation_response(
            valid=False,
            reason="payload_mismatch",
            action_id=action_id,
            session_id=session_id,
            expires_at=expires_at,
        )

    now = datetime.datetime.now(datetime.UTC)
    if expires_at < now:
        return _build_confirmation_validation_response(
            valid=False,
            reason="token_not_found_or_expired",
            action_id=action_id,
            session_id=session_id,
            expires_at=expires_at,
        )

    if consume:
        updated_record = dict(record)
        updated_record["consumed"] = True
        updated_record["consumed_at"] = now.isoformat()
        await _save_confirmation_record(user_id, confirmation_token, updated_record)

    return _build_confirmation_validation_response(
        valid=True,
        action_id=action_id,
        session_id=session_id,
        expires_at=expires_at,
        consumed=consume,
    )


async def _request_json(
    *,
    method: Literal["POST", "PATCH"],
    url: str,
    bearer_token: str,
    json_body: dict[str, Any] | None,
) -> tuple[int, dict[str, Any] | list[Any] | None]:
    headers = {"Authorization": f"Bearer {bearer_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            url,
            headers=headers,
            json=json_body,
            timeout=15.0,
        )
        status_code = response.status_code
        response.raise_for_status()
        if not response.content:
            return status_code, None
        try:
            payload = response.json()
        except ValueError:
            return status_code, {"raw": response.text}
    if isinstance(payload, (dict, list)):
        return status_code, payload
    return status_code, {"raw": str(payload)}


async def _execute_write_action(
    *,
    action_id: str,
    bearer_token: str,
    action_payload: dict[str, Any],
) -> tuple[str, int, dict[str, Any] | list[Any] | None]:
    if action_id == "documents.review_document":
        document_id = str(action_payload.get("document_id") or "").strip()
        if not document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing document_id in action_payload",
            )
        review_payload = action_payload.get("review_payload")
        if isinstance(review_payload, dict):
            payload_body = review_payload
        else:
            payload_body = {
                key: value
                for key, value in action_payload.items()
                if key != "document_id"
            }
        if not payload_body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing review_payload for documents.review_document",
            )
        endpoint = DOCUMENTS_REVIEW_UPDATE_URL_TEMPLATE.format(document_id=document_id)
        status_code, payload = await _request_json(
            method="PATCH",
            url=endpoint,
            bearer_token=bearer_token,
            json_body=payload_body,
        )
        return endpoint, status_code, payload

    if action_id == "transactions.reconcile_receipt_draft":
        draft_transaction_id = str(action_payload.get("draft_transaction_id") or "").strip()
        target_transaction_id = str(action_payload.get("target_transaction_id") or "").strip()
        if not draft_transaction_id or not target_transaction_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing draft_transaction_id or target_transaction_id in action_payload",
            )
        endpoint = TRANSACTIONS_RECONCILE_URL_TEMPLATE.format(
            draft_transaction_id=draft_transaction_id
        )
        status_code, payload = await _request_json(
            method="POST",
            url=endpoint,
            bearer_token=bearer_token,
            json_body={"target_transaction_id": target_transaction_id},
        )
        return endpoint, status_code, payload

    if action_id == "transactions.ignore_receipt_draft":
        draft_transaction_id = str(action_payload.get("draft_transaction_id") or "").strip()
        if not draft_transaction_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing draft_transaction_id in action_payload",
            )
        endpoint = TRANSACTIONS_IGNORE_URL_TEMPLATE.format(
            draft_transaction_id=draft_transaction_id
        )
        status_code, payload = await _request_json(
            method="POST",
            url=endpoint,
            bearer_token=bearer_token,
            json_body=None,
        )
        return endpoint, status_code, payload

    if action_id == "tax.calculate_and_submit":
        required_fields = ("start_date", "end_date", "jurisdiction")
        missing_fields = [field for field in required_fields if not action_payload.get(field)]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields in action_payload: {', '.join(missing_fields)}",
            )
        payload_body = {
            "start_date": str(action_payload["start_date"]),
            "end_date": str(action_payload["end_date"]),
            "jurisdiction": str(action_payload["jurisdiction"]),
        }
        status_code, payload = await _request_json(
            method="POST",
            url=TAX_CALCULATE_AND_SUBMIT_URL,
            bearer_token=bearer_token,
            json_body=payload_body,
        )
        return TAX_CALCULATE_AND_SUBMIT_URL, status_code, payload

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported action_id '{action_id}'",
    )


async def _fetch_documents_review_queue(bearer_token: str, limit: int = 25) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {bearer_token}"}
    return await get_json_with_retry(
        f"{DOCUMENTS_REVIEW_QUEUE_URL}?limit={limit}&offset=0",
        headers=headers,
        timeout=10.0,
    )


async def _fetch_unmatched_receipt_drafts(bearer_token: str, limit: int = 15) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {bearer_token}"}
    return await get_json_with_retry(
        f"{TRANSACTIONS_RECEIPT_DRAFTS_URL}?limit={limit}&offset=0&candidate_limit=3",
        headers=headers,
        timeout=10.0,
    )


async def _fetch_transactions_me(bearer_token: str) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {bearer_token}"}
    payload = await get_json_with_retry(
        TRANSACTIONS_ME_URL,
        headers=headers,
        timeout=10.0,
    )
    return payload if isinstance(payload, list) else []


async def _fetch_tax_snapshot(bearer_token: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {bearer_token}"}
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=DEFAULT_TAX_LOOKBACK_DAYS)
    calculation = await post_json_with_retry(
        TAX_ENGINE_CALCULATE_URL,
        headers=headers,
        json_body={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "jurisdiction": "UK",
        },
        timeout=12.0,
    )
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "calculation": calculation if isinstance(calculation, dict) else {},
    }


async def _safe_call(coroutine: Any) -> tuple[Any | None, str | None]:
    try:
        return await coroutine, None
    except httpx.HTTPError as exc:
        return None, str(exc)


def _build_ocr_review_assist_response(payload: dict[str, Any] | None, error: str | None) -> tuple[str, list[AgentEvidence], list[AgentSuggestedAction]]:
    if error or payload is None:
        return (
            "I could not load the OCR review queue right now. Please retry in a minute.",
            [
                AgentEvidence(
                    source_service="documents-service",
                    source_endpoint="/documents/review-queue",
                    summary=f"Downstream error: {error or 'unknown'}",
                )
            ],
            [
                AgentSuggestedAction(
                    action_id="retry_ocr_queue",
                    label="Retry OCR review queue check",
                    description="Refresh the OCR queue and resume manual review workflow.",
                )
            ],
        )

    items_raw = payload.get("items")
    items = items_raw if isinstance(items_raw, list) else []
    total = _to_int(payload.get("total"), len(items))
    scanned_fields, suspicious_fields = _scan_document_context_for_prompt_injection(
        [item for item in items if isinstance(item, dict)]
    )
    guard_summary = (
        f"Prompt guard scanned {scanned_fields} OCR text field(s) and "
        f"filtered {suspicious_fields} suspicious snippet(s)."
    )
    evidence = [
        AgentEvidence(
            source_service="documents-service",
            source_endpoint="/documents/review-queue",
            record_ids=_extract_record_ids(
                [item for item in items if isinstance(item, dict)],
                key="id",
                limit=8,
            ),
            summary=f"{total} documents currently require OCR confirmation or correction. {guard_summary}",
        )
    ]
    if total == 0:
        answer = "Great news: no documents are currently waiting in the OCR review queue."
    else:
        answer = f"OCR review queue has {total} document(s). Start with the oldest low-confidence receipts first."
        if suspicious_fields > 0:
            answer += " Guardrails detected suspicious OCR text and excluded it from agent context."
    actions = [
        AgentSuggestedAction(
            action_id="open_documents_review_queue",
            label="Open manual OCR review queue",
            description="Confirm or correct vendor, date, amount, and category for flagged receipts.",
        )
    ]
    if items:
        first_item = items[0]
        if isinstance(first_item, dict):
            first_document_id = str(first_item.get("id") or "").strip()
            if first_document_id:
                actions.append(
                    AgentSuggestedAction(
                        action_id="documents.review_document",
                        label="Confirm first OCR item directly",
                        description="Submit a confirmed review for the first queued document.",
                        requires_confirmation=True,
                        action_payload={
                            "document_id": first_document_id,
                            "review_payload": {
                                "review_status": "confirmed",
                                "review_notes": "Confirmed via AI Copilot action.",
                            },
                        },
                    )
                )
    if suspicious_fields > 0:
        actions.append(
            AgentSuggestedAction(
                action_id="review_prompt_injection_flags",
                label="Review suspicious OCR snippets manually",
                description="Open flagged documents and verify text fields before trusting extracted context.",
            )
        )
    return answer, evidence, actions


def _build_reconciliation_assist_response(
    payload: dict[str, Any] | None,
    error: str | None,
) -> tuple[str, list[AgentEvidence], list[AgentSuggestedAction]]:
    if error or payload is None:
        return (
            "I could not load unmatched receipt drafts right now. Please retry shortly.",
            [
                AgentEvidence(
                    source_service="transactions-service",
                    source_endpoint="/transactions/receipt-drafts/unmatched",
                    summary=f"Downstream error: {error or 'unknown'}",
                )
            ],
            [
                AgentSuggestedAction(
                    action_id="retry_reconciliation_snapshot",
                    label="Retry reconciliation snapshot",
                    description="Fetch unmatched drafts again and continue manual matching.",
                )
            ],
        )

    items_raw = payload.get("items")
    items = items_raw if isinstance(items_raw, list) else []
    total = _to_int(payload.get("total"), len(items))
    draft_ids: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        draft = item.get("draft_transaction")
        if isinstance(draft, dict):
            draft_id = draft.get("id")
            if draft_id:
                draft_ids.append(str(draft_id))
    evidence = [
        AgentEvidence(
            source_service="transactions-service",
            source_endpoint="/transactions/receipt-drafts/unmatched",
            record_ids=draft_ids[:8],
            summary=f"{total} unmatched receipt draft(s) currently need reconciliation.",
        )
    ]
    answer = (
        "No unmatched receipt drafts found. Auto-reconciliation is keeping up."
        if total == 0
        else f"Found {total} unmatched receipt draft(s). Resolve top candidates to prevent duplicate expenses."
    )
    actions = [
        AgentSuggestedAction(
            action_id="open_unmatched_receipt_drafts",
            label="Review unmatched receipt drafts",
            description="Match drafts to bank transactions or ignore low-quality candidates.",
        )
    ]
    if items:
        first_item = items[0]
        if isinstance(first_item, dict):
            draft = first_item.get("draft_transaction")
            draft_id = str(draft.get("id") or "").strip() if isinstance(draft, dict) else ""
            candidates = first_item.get("candidates")
            first_candidate = candidates[0] if isinstance(candidates, list) and candidates else None
            candidate_transaction_id = (
                str(first_candidate.get("transaction_id") or "").strip()
                if isinstance(first_candidate, dict)
                else ""
            )
            if draft_id and candidate_transaction_id:
                actions.append(
                    AgentSuggestedAction(
                        action_id="transactions.reconcile_receipt_draft",
                        label="Confirm top reconciliation candidate",
                        description="Reconcile the first draft with its highest-ranked candidate.",
                        requires_confirmation=True,
                        action_payload={
                            "draft_transaction_id": draft_id,
                            "target_transaction_id": candidate_transaction_id,
                        },
                    )
                )
            if draft_id:
                actions.append(
                    AgentSuggestedAction(
                        action_id="transactions.ignore_receipt_draft",
                        label="Ignore first unmatched draft",
                        description="Mark the first unmatched draft as ignored when evidence is weak.",
                        requires_confirmation=True,
                        action_payload={"draft_transaction_id": draft_id},
                    )
                )
    return answer, evidence, actions


def _build_tax_pre_submit_response(
    tax_snapshot: dict[str, Any] | None,
    tax_error: str | None,
    transactions: list[dict[str, Any]] | None,
    transactions_error: str | None,
) -> tuple[str, list[AgentEvidence], list[AgentSuggestedAction]]:
    evidence: list[AgentEvidence] = []
    actions = [
        AgentSuggestedAction(
            action_id="run_tax_calculation_review",
            label="Review tax calculation inputs",
            description="Validate income and deductible categories before submission.",
        ),
    ]

    if transactions_error:
        evidence.append(
            AgentEvidence(
                source_service="transactions-service",
                source_endpoint="/transactions/me",
                summary=f"Downstream error: {transactions_error}",
            )
        )
    else:
        tx_rows = transactions or []
        evidence.append(
            AgentEvidence(
                source_service="transactions-service",
                source_endpoint="/transactions/me",
                record_ids=_extract_record_ids(tx_rows, key="id", limit=8),
                summary=f"{len(tx_rows)} transaction(s) were considered for tax pre-check.",
            )
        )

    if tax_error or tax_snapshot is None:
        evidence.append(
            AgentEvidence(
                source_service="tax-engine",
                source_endpoint="/calculate",
                summary=f"Downstream error: {tax_error or 'unknown'}",
            )
        )
        answer = "I could not calculate a tax snapshot right now. Retry after services recover."
        return answer, evidence, actions

    calculation = tax_snapshot.get("calculation")
    calculation_dict = calculation if isinstance(calculation, dict) else {}
    estimated_tax_due = float(calculation_dict.get("estimated_tax_due", 0.0))
    total_income = float(calculation_dict.get("total_income", 0.0))
    total_expenses = float(calculation_dict.get("total_expenses", 0.0))
    start_date = str(tax_snapshot.get("start_date", ""))
    end_date = str(tax_snapshot.get("end_date", ""))
    evidence.append(
        AgentEvidence(
            source_service="tax-engine",
            source_endpoint="/calculate",
            summary=(
                f"Estimated tax due £{estimated_tax_due:.2f} for period {start_date} to {end_date}; "
                f"income £{total_income:.2f}, deductible expenses £{total_expenses:.2f}."
            ),
        )
    )
    answer = (
        f"Tax pre-submit snapshot ready: estimated due is £{estimated_tax_due:.2f}. "
        "Review category accuracy, then proceed to submission."
    )
    actions.append(
        AgentSuggestedAction(
            action_id="tax.calculate_and_submit",
            label="Confirm calculate-and-submit",
            description="Submit calculate-and-submit for this same tax period.",
            requires_confirmation=True,
            action_payload={
                "start_date": start_date,
                "end_date": end_date,
                "jurisdiction": "UK",
            },
        )
    )
    return answer, evidence, actions


def _build_readiness_check_response(
    docs_payload: dict[str, Any] | None,
    docs_error: str | None,
    unmatched_payload: dict[str, Any] | None,
    unmatched_error: str | None,
    transactions_payload: list[dict[str, Any]] | None,
    transactions_error: str | None,
    tax_snapshot: dict[str, Any] | None,
    tax_error: str | None,
) -> tuple[str, list[AgentEvidence], list[AgentSuggestedAction]]:
    evidence: list[AgentEvidence] = []
    actions: list[AgentSuggestedAction] = []

    ocr_total = 0
    if docs_error or docs_payload is None:
        evidence.append(
            AgentEvidence(
                source_service="documents-service",
                source_endpoint="/documents/review-queue",
                summary=f"Downstream error: {docs_error or 'unknown'}",
            )
        )
    else:
        docs_items_raw = docs_payload.get("items")
        docs_items = docs_items_raw if isinstance(docs_items_raw, list) else []
        docs_records = [item for item in docs_items if isinstance(item, dict)]
        scanned_fields, suspicious_fields = _scan_document_context_for_prompt_injection(docs_records)
        guard_summary = (
            f"Prompt guard scanned {scanned_fields} OCR text field(s), "
            f"filtered {suspicious_fields} suspicious snippet(s)."
        )
        ocr_total = _to_int(docs_payload.get("total"), len(docs_items))
        evidence.append(
            AgentEvidence(
                source_service="documents-service",
                source_endpoint="/documents/review-queue",
                record_ids=_extract_record_ids(
                    docs_records,
                    key="id",
                    limit=6,
                ),
                summary=f"OCR review queue: {ocr_total} item(s). {guard_summary}",
            )
        )
        if ocr_total > 0:
            actions.append(
                AgentSuggestedAction(
                    action_id="resolve_ocr_queue",
                    label="Resolve OCR review queue",
                    description="Confirm/correct extracted receipt fields before further automation.",
                )
            )
        if suspicious_fields > 0:
            actions.append(
                AgentSuggestedAction(
                    action_id="review_prompt_injection_flags",
                    label="Review suspicious OCR snippets manually",
                    description="Verify flagged OCR text fields before relying on agent recommendations.",
                )
            )

    unmatched_total = 0
    if unmatched_error or unmatched_payload is None:
        evidence.append(
            AgentEvidence(
                source_service="transactions-service",
                source_endpoint="/transactions/receipt-drafts/unmatched",
                summary=f"Downstream error: {unmatched_error or 'unknown'}",
            )
        )
    else:
        unmatched_items_raw = unmatched_payload.get("items")
        unmatched_items = unmatched_items_raw if isinstance(unmatched_items_raw, list) else []
        unmatched_total = _to_int(unmatched_payload.get("total"), len(unmatched_items))
        draft_ids: list[str] = []
        for item in unmatched_items:
            if not isinstance(item, dict):
                continue
            draft = item.get("draft_transaction")
            if isinstance(draft, dict) and draft.get("id"):
                draft_ids.append(str(draft["id"]))
        evidence.append(
            AgentEvidence(
                source_service="transactions-service",
                source_endpoint="/transactions/receipt-drafts/unmatched",
                record_ids=draft_ids[:6],
                summary=f"Unmatched receipt drafts: {unmatched_total}.",
            )
        )
        if unmatched_total > 0:
            actions.append(
                AgentSuggestedAction(
                    action_id="reconcile_unmatched_drafts",
                    label="Reconcile unmatched receipt drafts",
                    description="Run manual matching to avoid duplicate expenses.",
                )
            )

    transaction_count = 0
    if transactions_error:
        evidence.append(
            AgentEvidence(
                source_service="transactions-service",
                source_endpoint="/transactions/me",
                summary=f"Downstream error: {transactions_error}",
            )
        )
    else:
        tx_rows = transactions_payload or []
        transaction_count = len(tx_rows)
        evidence.append(
            AgentEvidence(
                source_service="transactions-service",
                source_endpoint="/transactions/me",
                record_ids=_extract_record_ids(tx_rows, key="id", limit=6),
                summary=f"Transactions available for planning: {transaction_count}.",
            )
        )

    estimated_tax_due = 0.0
    if tax_error or tax_snapshot is None:
        evidence.append(
            AgentEvidence(
                source_service="tax-engine",
                source_endpoint="/calculate",
                summary=f"Downstream error: {tax_error or 'unknown'}",
            )
        )
    else:
        calc = tax_snapshot.get("calculation")
        calc_dict = calc if isinstance(calc, dict) else {}
        estimated_tax_due = float(calc_dict.get("estimated_tax_due", 0.0))
        evidence.append(
            AgentEvidence(
                source_service="tax-engine",
                source_endpoint="/calculate",
                summary=f"Estimated tax due snapshot: £{estimated_tax_due:.2f}.",
            )
        )
        actions.append(
            AgentSuggestedAction(
                action_id="review_tax_snapshot",
                label="Review tax pre-submit snapshot",
                description="Validate totals and deductible categories before formal submission.",
            )
        )

    if not actions:
        actions.append(
            AgentSuggestedAction(
                action_id="refresh_readiness_snapshot",
                label="Refresh readiness snapshot",
                description="Retry a full health check across OCR, reconciliation, and tax readiness.",
            )
        )

    answer = (
        f"Readiness snapshot: OCR queue {ocr_total}, unmatched drafts {unmatched_total}, "
        f"transactions {transaction_count}, estimated tax due £{estimated_tax_due:.2f}."
    )
    return answer, evidence, actions


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/agent/audit/events", response_model=AgentAuditLogResponse)
async def list_agent_audit_events(
    limit: int = Query(default=50, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
):
    items = await _load_audit_events(user_id, limit)
    return AgentAuditLogResponse(total=len(items), items=items)


@app.post("/agent/actions/request-confirmation", response_model=AgentConfirmationTokenResponse)
async def request_action_confirmation_token(
    request: AgentConfirmationTokenRequest,
    user_id: str = Depends(get_current_user_id),
):
    _ensure_supported_write_action(request.action_id)
    _validate_action_payload_shape(request.action_id, request.action_payload)
    now = datetime.datetime.now(datetime.UTC)
    expires_at = now + datetime.timedelta(seconds=AGENT_CONFIRMATION_TOKEN_TTL_SECONDS)
    confirmation_token = uuid.uuid4().hex
    payload_hash = _hash_action_payload(request.action_payload)
    record = {
        "session_id": request.session_id,
        "action_id": request.action_id,
        "action_payload_hash": payload_hash,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "consumed": False,
    }
    await _save_confirmation_record(user_id, confirmation_token, record)
    await _append_audit_event(
        user_id,
        AgentAuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=now,
            event_type="confirmation_token_issued",
            session_id=request.session_id,
            action_id=request.action_id,
            payload_summary={
                "action_payload_keys": sorted(request.action_payload.keys()),
                "action_payload_hash": payload_hash,
            },
            action_result={
                "issued": True,
                "expires_at": expires_at.isoformat(),
            },
        ),
    )
    return AgentConfirmationTokenResponse(
        session_id=request.session_id,
        action_id=request.action_id,
        confirmation_token=confirmation_token,
        expires_at=expires_at,
    )


@app.post("/agent/actions/validate-confirmation", response_model=AgentConfirmationValidationResponse)
async def validate_action_confirmation_token(
    request: AgentConfirmationValidationRequest,
    user_id: str = Depends(get_current_user_id),
):
    _ensure_supported_write_action(request.action_id)
    _validate_action_payload_shape(request.action_id, request.action_payload)
    validation_result = await _validate_confirmation_token_for_action(
        user_id=user_id,
        session_id=request.session_id,
        action_id=request.action_id,
        confirmation_token=request.confirmation_token,
        action_payload=request.action_payload,
        consume=request.consume,
    )
    await _append_audit_event(
        user_id,
        AgentAuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now(datetime.UTC),
            event_type="confirmation_token_validated",
            session_id=request.session_id,
            action_id=request.action_id,
            payload_summary={
                "consume": request.consume,
                "action_payload_keys": sorted(request.action_payload.keys()),
            },
            action_result={
                "valid": validation_result.valid,
                "reason": validation_result.reason,
                "consumed": validation_result.consumed,
            },
        ),
    )
    return validation_result


@app.post("/agent/actions/execute", response_model=AgentExecuteActionResponse)
async def execute_confirmed_action(
    request: AgentExecuteActionRequest,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    _ensure_supported_write_action(request.action_id)
    _validate_action_payload_shape(request.action_id, request.action_payload)
    if not AGENT_WRITE_ACTIONS_ENABLED:
        AGENT_ACTION_EXECUTIONS_TOTAL.labels(
            action_id=request.action_id,
            result="write_actions_disabled",
        ).inc()
        return AgentExecuteActionResponse(
            session_id=request.session_id,
            action_id=request.action_id,
            executed=False,
            valid_confirmation=False,
            confirmation_reason="write_actions_disabled",
            message="Agent write actions are disabled by feature flag.",
        )

    validation_result = await _validate_confirmation_token_for_action(
        user_id=user_id,
        session_id=request.session_id,
        action_id=request.action_id,
        confirmation_token=request.confirmation_token,
        action_payload=request.action_payload,
        consume=True,
    )
    if not validation_result.valid:
        failed_result = AgentExecuteActionResponse(
            session_id=request.session_id,
            action_id=request.action_id,
            executed=False,
            valid_confirmation=False,
            confirmation_reason=validation_result.reason,
            message="Confirmation token validation failed.",
        )
        await _append_audit_event(
            user_id,
            AgentAuditEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.datetime.now(datetime.UTC),
                event_type="confirmed_action_execution",
                session_id=request.session_id,
                action_id=request.action_id,
                payload_summary={
                    "action_payload_keys": sorted(request.action_payload.keys()),
                },
                action_result={
                    "executed": False,
                    "valid_confirmation": False,
                    "confirmation_reason": validation_result.reason,
                },
            ),
        )
        AGENT_ACTION_EXECUTIONS_TOTAL.labels(
            action_id=request.action_id,
            result="confirmation_failed",
        ).inc()
        return failed_result

    try:
        endpoint, status_code, result = await _execute_write_action(
            action_id=request.action_id,
            bearer_token=bearer_token,
            action_payload=request.action_payload,
        )
    except HTTPException as exc:
        AGENT_ACTION_EXECUTIONS_TOTAL.labels(
            action_id=request.action_id,
            result="invalid_payload",
        ).inc()
        raise exc
    except httpx.HTTPStatusError as exc:
        failed_result = AgentExecuteActionResponse(
            session_id=request.session_id,
            action_id=request.action_id,
            executed=False,
            valid_confirmation=True,
            downstream_endpoint=str(exc.request.url),
            downstream_status_code=exc.response.status_code,
            message=f"Downstream service rejected execution: {exc.response.text}",
        )
        await _append_audit_event(
            user_id,
            AgentAuditEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.datetime.now(datetime.UTC),
                event_type="confirmed_action_execution",
                session_id=request.session_id,
                action_id=request.action_id,
                tool_calls=[
                    AgentToolCallLog(
                        service="downstream",
                        endpoint=str(exc.request.url),
                        status="error",
                        error=str(exc),
                    )
                ],
                payload_summary={
                    "action_payload_keys": sorted(request.action_payload.keys()),
                },
                action_result={
                    "executed": False,
                    "valid_confirmation": True,
                    "downstream_status_code": exc.response.status_code,
                },
            ),
        )
        AGENT_ACTION_EXECUTIONS_TOTAL.labels(
            action_id=request.action_id,
            result="downstream_rejected",
        ).inc()
        return failed_result
    except httpx.HTTPError as exc:
        failed_result = AgentExecuteActionResponse(
            session_id=request.session_id,
            action_id=request.action_id,
            executed=False,
            valid_confirmation=True,
            message=f"Downstream service unavailable: {exc}",
        )
        await _append_audit_event(
            user_id,
            AgentAuditEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.datetime.now(datetime.UTC),
                event_type="confirmed_action_execution",
                session_id=request.session_id,
                action_id=request.action_id,
                tool_calls=[
                    AgentToolCallLog(
                        service="downstream",
                        endpoint="unknown",
                        status="error",
                        error=str(exc),
                    )
                ],
                payload_summary={
                    "action_payload_keys": sorted(request.action_payload.keys()),
                },
                action_result={
                    "executed": False,
                    "valid_confirmation": True,
                },
            ),
        )
        AGENT_ACTION_EXECUTIONS_TOTAL.labels(
            action_id=request.action_id,
            result="downstream_unavailable",
        ).inc()
        return failed_result

    success_result = AgentExecuteActionResponse(
        session_id=request.session_id,
        action_id=request.action_id,
        executed=True,
        valid_confirmation=True,
        downstream_endpoint=endpoint,
        downstream_status_code=status_code,
        result=result,
        message="Confirmed action executed successfully.",
    )
    await _append_audit_event(
        user_id,
        AgentAuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now(datetime.UTC),
            event_type="confirmed_action_execution",
            session_id=request.session_id,
            action_id=request.action_id,
            tool_calls=[
                AgentToolCallLog(
                    service="downstream",
                    endpoint=endpoint,
                    status="success",
                )
            ],
            payload_summary={
                "action_payload_keys": sorted(request.action_payload.keys()),
            },
            action_result={
                "executed": True,
                "valid_confirmation": True,
                "downstream_status_code": status_code,
            },
        ),
    )
    AGENT_ACTION_EXECUTIONS_TOTAL.labels(
        action_id=request.action_id,
        result="success",
    ).inc()
    if _is_human_override_action(request.action_id, request.action_payload):
        AGENT_HUMAN_OVERRIDE_ACTIONS_TOTAL.labels(action_id=request.action_id).inc()
    return success_result


@app.post("/agent/chat", response_model=AgentChatResponse)
async def agent_chat(
    request: AgentChatRequest,
    user_id: str = Depends(get_current_user_id),
    bearer_token: str = Depends(get_bearer_token),
):
    session_id = request.session_id or str(uuid.uuid4())
    memory = await _load_session_memory(user_id, session_id)
    last_intent_raw = memory.get("last_intent")
    last_intent: AgentIntent | None = None
    if isinstance(last_intent_raw, str) and last_intent_raw in INTENT_VALUES:
        last_intent = last_intent_raw
    intent, confidence, intent_reason = _detect_intent(request.message, last_intent)
    confidence_band = _confidence_band(confidence)
    tool_calls: list[AgentToolCallLog] = []

    if intent == "ocr_review_assist":
        docs_payload, docs_error = await _safe_call(_fetch_documents_review_queue(bearer_token))
        tool_calls = [
            AgentToolCallLog(
                service="documents-service",
                endpoint="/documents/review-queue",
                status="error" if docs_error else "success",
                error=docs_error,
            )
        ]
        answer, evidence, suggested_actions = _build_ocr_review_assist_response(docs_payload, docs_error)
    elif intent == "reconciliation_assist":
        unmatched_payload, unmatched_error = await _safe_call(_fetch_unmatched_receipt_drafts(bearer_token))
        tool_calls = [
            AgentToolCallLog(
                service="transactions-service",
                endpoint="/transactions/receipt-drafts/unmatched",
                status="error" if unmatched_error else "success",
                error=unmatched_error,
            )
        ]
        answer, evidence, suggested_actions = _build_reconciliation_assist_response(
            unmatched_payload,
            unmatched_error,
        )
    elif intent == "tax_pre_submit":
        transactions_payload, transactions_error = await _safe_call(_fetch_transactions_me(bearer_token))
        tax_snapshot, tax_error = await _safe_call(_fetch_tax_snapshot(bearer_token))
        tool_calls = [
            AgentToolCallLog(
                service="transactions-service",
                endpoint="/transactions/me",
                status="error" if transactions_error else "success",
                error=transactions_error,
            ),
            AgentToolCallLog(
                service="tax-engine",
                endpoint="/calculate",
                status="error" if tax_error else "success",
                error=tax_error,
            ),
        ]
        answer, evidence, suggested_actions = _build_tax_pre_submit_response(
            tax_snapshot,
            tax_error,
            transactions_payload,
            transactions_error,
        )
    else:
        docs_task = _safe_call(_fetch_documents_review_queue(bearer_token))
        unmatched_task = _safe_call(_fetch_unmatched_receipt_drafts(bearer_token))
        transactions_task = _safe_call(_fetch_transactions_me(bearer_token))
        tax_task = _safe_call(_fetch_tax_snapshot(bearer_token))
        (docs_payload, docs_error), (unmatched_payload, unmatched_error), (
            transactions_payload,
            transactions_error,
        ), (tax_snapshot, tax_error) = await asyncio.gather(
            docs_task,
            unmatched_task,
            transactions_task,
            tax_task,
        )
        tool_calls = [
            AgentToolCallLog(
                service="documents-service",
                endpoint="/documents/review-queue",
                status="error" if docs_error else "success",
                error=docs_error,
            ),
            AgentToolCallLog(
                service="transactions-service",
                endpoint="/transactions/receipt-drafts/unmatched",
                status="error" if unmatched_error else "success",
                error=unmatched_error,
            ),
            AgentToolCallLog(
                service="transactions-service",
                endpoint="/transactions/me",
                status="error" if transactions_error else "success",
                error=transactions_error,
            ),
            AgentToolCallLog(
                service="tax-engine",
                endpoint="/calculate",
                status="error" if tax_error else "success",
                error=tax_error,
            ),
        ]
        answer, evidence, suggested_actions = _build_readiness_check_response(
            docs_payload,
            docs_error,
            unmatched_payload,
            unmatched_error,
            transactions_payload,
            transactions_error,
            tax_snapshot,
            tax_error,
        )

    turns_raw = memory.get("turns")
    turns = turns_raw if isinstance(turns_raw, list) else []
    turns.append(
        {
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "message": request.message,
            "intent": intent,
            "answer": answer,
        }
    )
    turns = turns[-20:]
    updated_memory = {
        "turns": turns,
        "last_intent": intent,
    }
    await _save_session_memory(user_id, session_id, updated_memory)
    await _append_audit_event(
        user_id,
        AgentAuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now(datetime.UTC),
            event_type="chat_read_only",
            session_id=session_id,
            action_id=intent,
            prompt_hash=_hash_prompt_text(request.message),
            tool_calls=tool_calls,
            payload_summary={
                "message_length": len(request.message),
                "detected_intent": intent,
                "intent_reason": intent_reason,
                "confidence_band": confidence_band,
                "session_turn_count_before_response": len(turns),
            },
            action_result={
                "suggested_actions_count": len(suggested_actions),
                "evidence_count": len(evidence),
            },
        ),
    )

    return AgentChatResponse(
        session_id=session_id,
        session_turn_count=len(turns),
        last_intent_from_memory=last_intent,
        intent=intent,
        confidence=confidence,
        confidence_band=confidence_band,
        intent_reason=intent_reason,
        answer=answer,
        evidence=evidence,
        suggested_actions=suggested_actions,
    )
