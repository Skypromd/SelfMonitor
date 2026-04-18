import os
from fastapi import FastAPI

app = FastAPI(title="Security Service", description="Security hardening and audit layer")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "security-service"}


@app.get("/security/config")
async def security_config():
    return {
        "mfa_enabled": True,
        "session_timeout_minutes": 60,
        "max_login_attempts": 5,
        "allowed_origins": os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
        "mfa_issuer": os.getenv("MFA_ISSUER", "MyNetTax"),
    }


@app.get("/security/status")
async def security_status():
    return {
        "tls_enabled": False,
        "rate_limiting": True,
        "cors_enabled": True,
        "csp_enabled": True,
    }
