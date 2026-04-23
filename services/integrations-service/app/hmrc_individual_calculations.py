"""
HMRC Individual Calculations (Self Assessment) — list, trigger, retrieve.

Spec: https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-calculations-api/8.0

Uses the same server OAuth (client_credentials) as MTD quarterly when direct mode is on.
Sandbox may require Gov-Test-Scenario; production typically needs user-delegated tokens — if HMRC
returns 403, the JSON error explains next steps.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import re
import uuid
from typing import Any, Literal

import httpx

from .hmrc_mtd import _fetch_hmrc_oauth_access_token, _should_retry_http_status

logger = logging.getLogger(__name__)

_TAX_YEAR_HYPHEN = re.compile(r"^\d{4}-\d{2}$")


def normalize_nino(nino: str) -> str:
    compact = "".join((nino or "").split()).upper()
    if len(compact) != 9:
        raise ValueError("NINO must be exactly 9 characters (spaces allowed in input).")
    return compact


def validate_tax_year_hyphen(tax_year: str) -> str:
    ty = (tax_year or "").strip()
    if not _TAX_YEAR_HYPHEN.match(ty):
        raise ValueError("tax_year must be hyphenated like 2024-25 (HMRC Individual Calculations path format).")
    return ty


def _list_url(api_base: str, nino: str, tax_year: str) -> str:
    return f"{api_base.rstrip('/')}/individuals/calculations/{nino}/self-assessment/{tax_year}"


def _trigger_url(api_base: str, nino: str, tax_year: str) -> str:
    return f"{api_base.rstrip('/')}/individuals/calculations/{nino}/self-assessment/{tax_year}/trigger"


def _retrieve_url(api_base: str, nino: str, tax_year: str, calculation_id: str) -> str:
    return (
        f"{api_base.rstrip('/')}/individuals/calculations/{nino}/self-assessment/{tax_year}/{calculation_id}"
    )


def _simulated_list(tax_year: str, nino: str) -> dict[str, Any]:
    cid = str(uuid.uuid4())
    return {
        "mode": "simulated",
        "disclaimer": "HMRC_DIRECT_SUBMISSION_ENABLED is off or OAuth is not configured. No call to HMRC.",
        "tax_year": tax_year,
        "nino": nino,
        "calculations": [
            {
                "calculationId": cid,
                "calculationTimestamp": datetime.datetime.now(datetime.UTC)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
                "calculationType": "in-year",
                "triggeredBy": "software",
            }
        ],
    }


def _simulated_trigger(tax_year: str, nino: str, calculation_type: str) -> dict[str, Any]:
    cid = str(uuid.uuid4())
    return {
        "mode": "simulated",
        "disclaimer": "HMRC_DIRECT_SUBMISSION_ENABLED is off or OAuth is not configured.",
        "tax_year": tax_year,
        "nino": nino,
        "calculationId": cid,
        "calculationType": calculation_type,
    }


def _simulated_retrieve(
    tax_year: str,
    nino: str,
    calculation_id: str,
) -> dict[str, Any]:
    return {
        "mode": "simulated",
        "disclaimer": "Not an official HMRC Tax Calculation JSON. Use HMRC Personal Tax Account for PDFs.",
        "tax_year": tax_year,
        "nino": nino,
        "calculationId": calculation_id,
        "calculation": {
            "summary": {
                "totalIncome": 0.0,
                "totalDeductions": 0.0,
                "taxableIncome": 0.0,
            },
            "message": "Simulated shell only. Enable direct mode and call trigger/list against HMRC sandbox for real payloads.",
        },
    }


async def _hmrc_json_request(
    method: str,
    url: str,
    *,
    access_token: str,
    accept: str,
    timeout: float,
    json_body: dict[str, Any] | None,
    max_retries: int,
    retry_backoff: float,
) -> httpx.Response:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": accept,
        "Content-Type": "application/json",
        "Gov-Client-Connection-Method": "WEB_APP_VIA_SERVER",
    }
    for attempt in range(1, max(1, max_retries) + 1):
        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    resp = await client.get(url, headers=headers, timeout=timeout)
                elif method.upper() == "POST":
                    resp = await client.post(url, headers=headers, json=json_body or {}, timeout=timeout)
                else:
                    raise ValueError(f"unsupported method {method}")
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError):
            if attempt >= max_retries:
                raise
            await asyncio.sleep(retry_backoff * (2 ** (attempt - 1)))
            continue
        if resp.status_code < 400:
            return resp
        if _should_retry_http_status(resp.status_code) and attempt < max_retries:
            await asyncio.sleep(retry_backoff * (2 ** (attempt - 1)))
            continue
        return resp
    raise RuntimeError("HMRC request retry loop exhausted")


async def list_self_assessment_calculations(
    *,
    tax_year: str,
    nino: str,
    hmrc_direct_submission_enabled: bool,
    hmrc_direct_api_base_url: str,
    hmrc_oauth_token_url: str,
    hmrc_oauth_client_id: str,
    hmrc_oauth_client_secret: str,
    hmrc_oauth_scope: str,
    request_timeout_seconds: float,
    hmrc_http_max_retries: int,
    hmrc_http_retry_backoff_seconds: float,
    accept_header: str,
) -> dict[str, Any]:
    ty = validate_tax_year_hyphen(tax_year)
    nn = normalize_nino(nino)
    if not hmrc_direct_submission_enabled:
        return _simulated_list(ty, nn)
    if not hmrc_oauth_client_id or not hmrc_oauth_client_secret:
        return _simulated_list(ty, nn)

    access_token = await _fetch_hmrc_oauth_access_token(
        token_url=hmrc_oauth_token_url,
        client_id=hmrc_oauth_client_id,
        client_secret=hmrc_oauth_client_secret,
        scope=hmrc_oauth_scope,
        timeout_seconds=request_timeout_seconds,
        max_retries=hmrc_http_max_retries,
        retry_backoff_seconds=hmrc_http_retry_backoff_seconds,
    )
    url = _list_url(hmrc_direct_api_base_url, nn, ty)
    resp = await _hmrc_json_request(
        "GET",
        url,
        access_token=access_token,
        accept=accept_header,
        timeout=request_timeout_seconds,
        json_body=None,
        max_retries=hmrc_http_max_retries,
        retry_backoff=hmrc_http_retry_backoff_seconds,
    )
    if resp.status_code >= 400:
        detail: dict[str, Any]
        try:
            detail = resp.json() if resp.content else {}
        except ValueError:
            detail = {"raw": resp.text[:500]}
        logger.warning("HMRC list calculations HTTP %s: %s", resp.status_code, detail)
        return {
            "mode": "hmrc_error",
            "http_status": resp.status_code,
            "tax_year": ty,
            "nino": nn,
            "hmrc": detail,
            "hint": (
                "If 403: Individual Calculations may require a user-restricted OAuth token. "
                "Client-credentials works for some sandbox tests only."
            ),
        }
    try:
        body = resp.json()
    except ValueError:
        body = {"raw": resp.text[:2000]}
    if isinstance(body, dict):
        body = {**body, "mode": "hmrc", "tax_year": ty, "nino": nn}
        return body
    return {"mode": "hmrc", "tax_year": ty, "nino": nn, "body": body}


async def trigger_self_assessment_calculation(
    *,
    tax_year: str,
    nino: str,
    calculation_type: Literal["in-year", "intent-to-finalise", "end-of-year"],
    hmrc_direct_submission_enabled: bool,
    hmrc_direct_api_base_url: str,
    hmrc_oauth_token_url: str,
    hmrc_oauth_client_id: str,
    hmrc_oauth_client_secret: str,
    hmrc_oauth_scope: str,
    request_timeout_seconds: float,
    hmrc_http_max_retries: int,
    hmrc_http_retry_backoff_seconds: float,
    accept_header: str,
) -> dict[str, Any]:
    ty = validate_tax_year_hyphen(tax_year)
    nn = normalize_nino(nino)
    if not hmrc_direct_submission_enabled:
        return _simulated_trigger(ty, nn, calculation_type)
    if not hmrc_oauth_client_id or not hmrc_oauth_client_secret:
        return _simulated_trigger(ty, nn, calculation_type)

    access_token = await _fetch_hmrc_oauth_access_token(
        token_url=hmrc_oauth_token_url,
        client_id=hmrc_oauth_client_id,
        client_secret=hmrc_oauth_client_secret,
        scope=hmrc_oauth_scope,
        timeout_seconds=request_timeout_seconds,
        max_retries=hmrc_http_max_retries,
        retry_backoff_seconds=hmrc_http_retry_backoff_seconds,
    )
    url = _trigger_url(hmrc_direct_api_base_url, nn, ty)
    hmrc_type = {
        "in-year": "in-year",
        "intent-to-finalise": "intent-to-finalise",
        "end-of-year": "end-of-year",
    }[calculation_type]
    payload = {"calculationType": hmrc_type}

    resp = await _hmrc_json_request(
        "POST",
        url,
        access_token=access_token,
        accept=accept_header,
        timeout=request_timeout_seconds,
        json_body=payload,
        max_retries=hmrc_http_max_retries,
        retry_backoff=hmrc_http_retry_backoff_seconds,
    )
    if resp.status_code >= 400:
        try:
            detail = resp.json() if resp.content else {}
        except ValueError:
            detail = {"raw": resp.text[:500]}
        return {
            "mode": "hmrc_error",
            "http_status": resp.status_code,
            "tax_year": ty,
            "nino": nn,
            "hmrc": detail,
        }
    try:
        body = resp.json()
    except ValueError:
        body = {"raw": resp.text[:2000]}
    if isinstance(body, dict):
        return {**body, "mode": "hmrc", "tax_year": ty, "nino": nn}
    return {"mode": "hmrc", "tax_year": ty, "nino": nn, "body": body}


async def retrieve_self_assessment_calculation(
    *,
    tax_year: str,
    nino: str,
    calculation_id: str,
    hmrc_direct_submission_enabled: bool,
    hmrc_direct_api_base_url: str,
    hmrc_oauth_token_url: str,
    hmrc_oauth_client_id: str,
    hmrc_oauth_client_secret: str,
    hmrc_oauth_scope: str,
    request_timeout_seconds: float,
    hmrc_http_max_retries: int,
    hmrc_http_retry_backoff_seconds: float,
    accept_header: str,
) -> dict[str, Any]:
    ty = validate_tax_year_hyphen(tax_year)
    nn = normalize_nino(nino)
    cid = (calculation_id or "").strip()
    if not cid:
        raise ValueError("calculation_id is required")

    if not hmrc_direct_submission_enabled:
        return _simulated_retrieve(ty, nn, cid)
    if not hmrc_oauth_client_id or not hmrc_oauth_client_secret:
        return _simulated_retrieve(ty, nn, cid)

    access_token = await _fetch_hmrc_oauth_access_token(
        token_url=hmrc_oauth_token_url,
        client_id=hmrc_oauth_client_id,
        client_secret=hmrc_oauth_client_secret,
        scope=hmrc_oauth_scope,
        timeout_seconds=request_timeout_seconds,
        max_retries=hmrc_http_max_retries,
        retry_backoff_seconds=hmrc_http_retry_backoff_seconds,
    )
    url = _retrieve_url(hmrc_direct_api_base_url, nn, ty, cid)
    resp = await _hmrc_json_request(
        "GET",
        url,
        access_token=access_token,
        accept=accept_header,
        timeout=request_timeout_seconds,
        json_body=None,
        max_retries=hmrc_http_max_retries,
        retry_backoff=hmrc_http_retry_backoff_seconds,
    )
    if resp.status_code >= 400:
        try:
            detail = resp.json() if resp.content else {}
        except ValueError:
            detail = {"raw": resp.text[:500]}
        return {
            "mode": "hmrc_error",
            "http_status": resp.status_code,
            "tax_year": ty,
            "nino": nn,
            "calculationId": cid,
            "hmrc": detail,
        }
    try:
        body = resp.json()
    except ValueError:
        body = {"raw": resp.text[:5000]}
    if isinstance(body, dict):
        return {
            **body,
            "mode": "hmrc",
            "tax_year": ty,
            "nino": nn,
            "calculationId": cid,
            "disclaimer": (
                "Structured tax calculation from HMRC Individual Calculations API. "
                "This is not a PDF Tax Year overview; lenders may still require PTA downloads."
            ),
        }
    return {"mode": "hmrc", "tax_year": ty, "nino": nn, "calculationId": cid, "body": body}
