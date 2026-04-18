"""
HMRC fraud prevention: client-originated context + server-observed network metadata.

Connection methods (canonical, HMRC Developer Hub):
  - WEB_APP_VIA_SERVER — https://developer.service.hmrc.gov.uk/guides/fraud-prevention/connection-method/web-app-via-server/
  - MOBILE_APP_VIA_SERVER — https://developer.service.hmrc.gov.uk/guides/fraud-prevention/connection-method/mobile-app-via-server/

End-user traffic is always browser or mobile app → our API → integrations-service → HMRC (never claim DESKTOP_APP_DIRECT for those flows).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
import re
import uuid
from typing import Any, Literal

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

HMRC_CONNECTION_METHOD_WEB_VIA_SERVER = "WEB_APP_VIA_SERVER"
HMRC_CONNECTION_METHOD_MOBILE_VIA_SERVER = "MOBILE_APP_VIA_SERVER"

ClientType = Literal["web", "mobile"]


class HMRCFraudClientContext(BaseModel):
    """Sent by web or mobile; never trust client-supplied public IP for Gov-Client-Public-IP — use server-observed."""

    model_config = ConfigDict(extra="allow")

    client_type: ClientType
    user_agent: str | None = Field(
        default=None,
        max_length=2048,
        description="Browser or app user-agent string from the originating device.",
    )
    app_version: str | None = Field(default=None, max_length=64)
    build_number: str | None = Field(default=None, max_length=64)
    device_model: str | None = Field(default=None, max_length=256)
    os_name_version: str | None = Field(default=None, max_length=256)
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=64)
    request_timestamp_utc: str | None = Field(
        default=None,
        max_length=40,
        description="ISO-8601 UTC from client when the user initiated the action.",
    )
    installation_id: str | None = Field(default=None, max_length=128)
    session_id: str | None = Field(default=None, max_length=128)
    device_id: str | None = Field(
        default=None,
        max_length=128,
        description="Persistent Gov-Client-Device-ID source from the app/browser store.",
    )
    screens: str | None = Field(
        default=None,
        max_length=512,
        description="Gov-Client-Screens format: width=…&height=…&scaling-factor=…&colour-depth=…",
    )
    window_size: str | None = Field(default=None, max_length=128)
    client_ip_guess: str | None = Field(
        default=None,
        max_length=64,
        description="Optional; for diagnostics only — not used for Gov-Client-Public-IP.",
    )


def connection_method_for_client_type(client_type: ClientType) -> str:
    if client_type == "web":
        return HMRC_CONNECTION_METHOD_WEB_VIA_SERVER
    return HMRC_CONNECTION_METHOD_MOBILE_VIA_SERVER


def _first_public_ip_from_forwarded(forwarded: str | None) -> str:
    if not forwarded:
        return ""
    parts = [p.strip() for p in forwarded.split(",") if p.strip()]
    for p in parts:
        host = p.split("%")[0].strip()
        if host.startswith("[") and "]" in host:
            host = host[1 : host.index("]")]
        host = re.sub(r":\d+$", "", host)
        if host and host.lower() not in {"unknown", "null"}:
            return host
    return ""


def observed_inbound_client_metadata(request: Request) -> dict[str, Any]:
    """Values observed at integrations-service (after gateway)."""
    fwd = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    real_ip = request.headers.get("x-real-ip") or request.headers.get("X-Real-IP")
    observed_ip = _first_public_ip_from_forwarded(fwd) or (real_ip or "").strip()
    if not observed_ip and request.client:
        observed_ip = request.client.host or ""
    port_hdr = request.headers.get("x-forwarded-port") or request.headers.get("X-Forwarded-Port")
    try:
        port_val = int(port_hdr) if port_hdr and str(port_hdr).isdigit() else None
    except ValueError:
        port_val = None
    return {
        "forwarded_for_raw": (fwd or "")[:2048],
        "observed_client_ip": observed_ip[:128],
        "observed_forwarded_port": port_val,
        "path": str(request.url.path),
    }


def fraud_headers_fingerprint(headers: dict[str, str]) -> str:
    canonical = json.dumps(dict(sorted(headers.items())), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def validate_client_context_for_direct(
    *,
    client_context: HMRCFraudClientContext | None,
    hmrc_direct_submission_enabled: bool,
) -> None:
    """When ``hmrc_direct_submission_enabled`` is True, require full fraud context (Pro/Business + live HMRC)."""
    if not hmrc_direct_submission_enabled:
        return
    if client_context is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "HMRC direct submission requires client_context on the quarterly payload "
                "(client_type web|mobile, user_agent, and for mobile device_id). "
                "Forward hmrc_fraud_client_context from tax-engine / web / mobile."
            ),
        )
    if client_context.client_type == "web":
        if not (client_context.user_agent or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HMRC direct submission (web): user_agent is required in client_context.",
            )
    if client_context.client_type == "mobile":
        if not (client_context.device_id or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HMRC direct submission (mobile): device_id is required in client_context.",
            )
        if not (client_context.user_agent or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HMRC direct submission (mobile): user_agent is required in client_context.",
            )


def build_fraud_prevention_headers(
    *,
    user_id: str,
    client_context: HMRCFraudClientContext | None,
    inbound: Request,
    default_client_type_if_missing: ClientType = "web",
) -> tuple[dict[str, str], str]:
    """
    Returns (headers dict for HMRC, connection_method string used).
    Server fills Gov-Client-Public-IP (and port when known) from observed inbound metadata.
    """
    vendor_product_name = os.getenv("HMRC_VENDOR_PRODUCT_NAME", "MyNetTax")
    vendor_version = os.getenv("HMRC_VENDOR_VERSION", "1.0.0")
    vendor_public_ip = (os.getenv("HMRC_VENDOR_PUBLIC_IP") or "").strip()

    meta = observed_inbound_client_metadata(inbound)
    observed_ip = meta.get("observed_client_ip") or ""
    observed_port = meta.get("observed_forwarded_port")

    if client_context is None:
        logger.warning(
            "hmrc_fraud_client_context missing; using default_client_type=%s (simulation OK; direct submit should send context)",
            default_client_type_if_missing,
        )
        ctype: ClientType = default_client_type_if_missing
        ctx = HMRCFraudClientContext(client_type=ctype)
    else:
        ctx = client_context
        ctype = ctx.client_type

    connection_method = connection_method_for_client_type(ctype)
    now = datetime.datetime.now(datetime.UTC)
    tz = (ctx.timezone or "").strip() or f"UTC{now.astimezone().strftime('%z')[:3]}:00"

    device_id = (ctx.device_id or "").strip()
    if not device_id:
        device_id = (ctx.installation_id or "").strip() or (ctx.session_id or "").strip()
    if not device_id:
        device_id = str(uuid.uuid4())
        logger.warning(
            "Gov-Client-Device-ID was missing in client_context; generated ephemeral UUID (not suitable for production direct submit)"
        )

    headers: dict[str, str] = {
        "Gov-Client-Connection-Method": connection_method,
        "Gov-Vendor-Product-Name": vendor_product_name,
        "Gov-Vendor-Version": f"MyNetTax={vendor_version}",
        "Gov-Vendor-License-IDs": "",
        "Gov-Client-User-IDs": f"mynettax={user_id}" if user_id else "",
        "Gov-Client-Timezone": tz,
        "Gov-Client-Device-ID": device_id[:128],
        "Gov-Client-Multi-Factor": "",
    }

    if observed_ip:
        headers["Gov-Client-Public-IP"] = observed_ip
        headers["Gov-Client-Public-IP-Timestamp"] = now.isoformat().replace("+00:00", "Z")
    if observed_port and 1 <= observed_port <= 65535:
        headers["Gov-Client-Public-Port"] = str(observed_port)

    if ctype == "web":
        ua = (ctx.user_agent or "").strip()
        if ua:
            headers["Gov-Client-Browser-JS-User-Agent"] = ua[:2048]
            headers["Gov-Client-User-Agent"] = f"product=MyNetTaxWeb&version={vendor_version}"
        else:
            headers["Gov-Client-User-Agent"] = f"product=MyNetTaxWeb&version={vendor_version}"
    else:
        ua = (ctx.user_agent or "").strip()
        parts = [f"product=MyNetTaxMobile&version={vendor_version}"]
        if ctx.app_version:
            parts.append(f"app_version={ctx.app_version}")
        if ctx.build_number:
            parts.append(f"build={ctx.build_number}")
        if ctx.os_name_version:
            parts.append(f"os={ctx.os_name_version}")
        if ctx.device_model:
            parts.append(f"device={ctx.device_model}")
        headers["Gov-Client-User-Agent"] = "&".join(parts)[:1024]
        if ua:
            headers["Gov-Client-Browser-JS-User-Agent"] = ua[:2048]

    if (ctx.screens or "").strip():
        headers["Gov-Client-Screens"] = ctx.screens.strip()[:512]
    if (ctx.window_size or "").strip():
        headers["Gov-Client-Window-Size"] = ctx.window_size.strip()[:128]

    if vendor_public_ip and observed_ip:
        headers["Gov-Vendor-Forwarded"] = (
            f"by={vendor_public_ip}&for={observed_ip}".replace(" ", "")
        )
    if vendor_public_ip:
        headers["Gov-Vendor-Public-IP"] = vendor_public_ip

    return {k: v for k, v in headers.items() if v}, connection_method
