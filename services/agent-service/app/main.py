import asyncio
import datetime
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI
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


class AgentChatResponse(BaseModel):
    session_id: str
    session_turn_count: int
    last_intent_from_memory: AgentIntent | None = None
    intent: AgentIntent
    confidence: float = Field(ge=0.0, le=1.0)
    answer: str
    evidence: list[AgentEvidence]
    suggested_actions: list[AgentSuggestedAction]


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


def _detect_intent(message: str, last_intent: AgentIntent | None = None) -> tuple[AgentIntent, float]:
    normalized = message.lower()
    if normalized in {"continue", "continue.", "дальше", "продолжай", "go on"} and last_intent is not None:
        return last_intent, 0.71
    if any(keyword in normalized for keyword in ("hmrc", "tax", "налог", "декларац", "submission")):
        return "tax_pre_submit", 0.89
    if any(keyword in normalized for keyword in ("reconcile", "match", "duplicate", "сопостав", "дубликат")):
        return "reconciliation_assist", 0.86
    if any(keyword in normalized for keyword in ("ocr", "receipt", "чек", "документ", "review")):
        return "ocr_review_assist", 0.84
    if any(keyword in normalized for keyword in ("readiness", "готов", "mortgage", "ипотек", "pack")):
        return "readiness_check", 0.82
    return "readiness_check", 0.60


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
    evidence = [
        AgentEvidence(
            source_service="documents-service",
            source_endpoint="/documents/review-queue",
            record_ids=_extract_record_ids(
                [item for item in items if isinstance(item, dict)],
                key="id",
                limit=8,
            ),
            summary=f"{total} documents currently require OCR confirmation or correction.",
        )
    ]
    if total == 0:
        answer = "Great news: no documents are currently waiting in the OCR review queue."
    else:
        answer = f"OCR review queue has {total} document(s). Start with the oldest low-confidence receipts first."
    actions = [
        AgentSuggestedAction(
            action_id="open_documents_review_queue",
            label="Open manual OCR review queue",
            description="Confirm or correct vendor, date, amount, and category for flagged receipts.",
        )
    ]
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
        AgentSuggestedAction(
            action_id="prepare_calculate_and_submit",
            label="Prepare calculate-and-submit",
            description="Proceed to final HMRC submission after review and confirmation.",
            requires_confirmation=True,
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
        ocr_total = _to_int(docs_payload.get("total"), len(docs_items))
        evidence.append(
            AgentEvidence(
                source_service="documents-service",
                source_endpoint="/documents/review-queue",
                record_ids=_extract_record_ids(
                    [item for item in docs_items if isinstance(item, dict)],
                    key="id",
                    limit=6,
                ),
                summary=f"OCR review queue: {ocr_total} item(s).",
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
    intent, confidence = _detect_intent(request.message, last_intent)

    if intent == "ocr_review_assist":
        docs_payload, docs_error = await _safe_call(_fetch_documents_review_queue(bearer_token))
        answer, evidence, suggested_actions = _build_ocr_review_assist_response(docs_payload, docs_error)
    elif intent == "reconciliation_assist":
        unmatched_payload, unmatched_error = await _safe_call(_fetch_unmatched_receipt_drafts(bearer_token))
        answer, evidence, suggested_actions = _build_reconciliation_assist_response(
            unmatched_payload,
            unmatched_error,
        )
    elif intent == "tax_pre_submit":
        transactions_payload, transactions_error = await _safe_call(_fetch_transactions_me(bearer_token))
        tax_snapshot, tax_error = await _safe_call(_fetch_tax_snapshot(bearer_token))
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

    return AgentChatResponse(
        session_id=session_id,
        session_turn_count=len(turns),
        last_intent_from_memory=last_intent,
        intent=intent,
        confidence=confidence,
        answer=answer,
        evidence=evidence,
        suggested_actions=suggested_actions,
    )
