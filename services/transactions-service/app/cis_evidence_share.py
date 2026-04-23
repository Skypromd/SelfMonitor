import datetime
import io
import json
import os
import uuid
import zipfile
from typing import Any

from jose import JWTError, jwt

_PURPOSE = "cis_evidence_zip"
_ALGO = "HS256"


def zip_bytes_from_manifest(manifest: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "cis-evidence-manifest.json",
            json.dumps(manifest, indent=2, default=str).encode("utf-8"),
        )
        notice = (
            (manifest.get("watermark_unverified_cis") or "")
            + "\n\n"
            + (manifest.get("export_legal_notice") or "")
        )
        zf.writestr("NOTICE.txt", notice.encode("utf-8"))
    buf.seek(0)
    return buf.read()


def encode_share_token(*, user_id: str, tier: str, ttl_hours: int) -> tuple[str, datetime.datetime]:
    secret = os.environ["INTERNAL_SERVICE_SECRET"].strip()
    exp_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=ttl_hours)
    claims = {
        "sub": user_id,
        "tier": tier,
        "pur": _PURPOSE,
        "jti": str(uuid.uuid4()),
        "exp": int(exp_dt.timestamp()),
    }
    return jwt.encode(claims, secret, algorithm=_ALGO), exp_dt


def decode_share_token(token: str) -> dict[str, Any]:
    secret = os.environ["INTERNAL_SERVICE_SECRET"].strip()
    try:
        claims = jwt.decode(token, secret, algorithms=[_ALGO])
    except JWTError as exc:
        raise ValueError("invalid_share_token") from exc
    if claims.get("pur") != _PURPOSE:
        raise ValueError("invalid_share_token")
    tier = claims.get("tier")
    if tier not in ("basic", "full"):
        raise ValueError("invalid_share_token")
    user_id = claims.get("sub")
    if not user_id or not isinstance(user_id, str):
        raise ValueError("invalid_share_token")
    return {"user_id": user_id, "tier": str(tier), "jti": claims.get("jti")}
