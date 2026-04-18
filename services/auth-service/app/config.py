"""Environment-backed settings for auth-service."""

from __future__ import annotations

import os

_ALLOW_WEAK_JWT = os.getenv("AUTH_ALLOW_WEAK_JWT_SECRET", "").strip().lower() in (
    "1",
    "true",
    "yes",
)
_raw_auth_secret = os.environ["AUTH_SECRET_KEY"].strip()
if not _raw_auth_secret:
    raise RuntimeError("AUTH_SECRET_KEY must be set and non-empty")
if not _ALLOW_WEAK_JWT and len(_raw_auth_secret) < 32:
    raise RuntimeError(
        "AUTH_SECRET_KEY must be at least 32 characters for production-like deployments. "
        "For local dev or CI, set AUTH_ALLOW_WEAK_JWT_SECRET=1."
    )
SECRET_KEY = _raw_auth_secret
ALGORITHM = "HS256"
INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET", "").strip()
ACCESS_TOKEN_EXPIRE_MINUTES = 30
AUTH_DB_PATH = os.getenv(
    "AUTH_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "auth.db"),
)
AUTH_ADMIN_EMAIL = os.getenv("AUTH_ADMIN_EMAIL", "admin@example.com")
AUTH_ADMIN_PASSWORD = os.getenv("AUTH_ADMIN_PASSWORD", "admin_password")
AUTH_BOOTSTRAP_ADMIN = os.getenv("AUTH_BOOTSTRAP_ADMIN", "false").lower() == "true"
REQUIRE_ADMIN_2FA = os.getenv("AUTH_REQUIRE_ADMIN_2FA", "true").lower() == "true"
VERIFICATION_CODES_DEBUG = os.getenv(
    "AUTH_EMAIL_VERIFICATION_DEBUG_RETURN_CODE", "false"
).lower() in ("1", "true", "yes")

_DEFAULT_ADMIN_HEALTH_TARGETS: tuple[tuple[str, str], ...] = (
    ("auth-service", "http://auth-service:80/health"),
    ("billing-service", "http://billing-service:80/health"),
    ("user-profile-service", "http://user-profile-service:80/health"),
    ("documents-service", "http://documents-service:80/health"),
    ("compliance-service", "http://compliance-service:80/health"),
    ("integrations-service", "http://integrations-service:80/health"),
    ("invoice-service", "http://invoice-service:80/health"),
    ("support-ai-service", "http://support-ai-service:8020/health"),
    ("finops-monitor", "http://finops-monitor:8021/health"),
    ("mtd-agent", "http://mtd-agent:8022/health"),
    ("voice-gateway", "http://voice-gateway:8023/health"),
    ("agent-service", "http://agent-service:80/health"),
    ("analytics-service", "http://analytics-service:80/health"),
    ("referral-service", "http://referral-service:80/health"),
)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3000")
COMPLIANCE_SERVICE_URL = os.getenv(
    "COMPLIANCE_SERVICE_URL", "http://compliance-service:8000"
)

_AUTH_CORS_BASE = ["http://localhost:3000", "http://192.168.0.248:3000"]
_AUTH_CORS_EXTRA = os.getenv("AUTH_CORS_EXTRA_ORIGINS", "").strip()
AUTH_CORS_ORIGINS = list(
    dict.fromkeys(
        _AUTH_CORS_BASE
        + [o.strip() for o in _AUTH_CORS_EXTRA.split(",") if o.strip()]
    )
)

LOCKOUT_THRESHOLD = int(os.getenv("AUTH_MAX_FAILED_LOGIN_ATTEMPTS", "5"))
LOCKOUT_WINDOW_MINUTES = max(1, int(os.getenv("AUTH_ACCOUNT_LOCKOUT_MINUTES", "15")))
LOCKOUT_WINDOW_SECONDS = LOCKOUT_WINDOW_MINUTES * 60
