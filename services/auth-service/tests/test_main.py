import os
import sys
import datetime
import hashlib
import hmac
import json
from unittest.mock import patch

import pyotp
from fastapi.testclient import TestClient
from jose import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import main


client = TestClient(main.app)


def _register(email: str, password: str = "averysecurepassword123!") -> None:
    response = client.post("/register", data={"username": email, "password": password})
    assert response.status_code == 201


def _login(email: str, password: str = "averysecurepassword123!", scope: str | None = None) -> dict:
    form_data = {"username": email, "password": password}
    if scope is not None:
        form_data["scope"] = scope
    response = client.post("/token", data=form_data)
    assert response.status_code == 200
    return response.json()


def setup_function() -> None:
    main.fake_users_db.clear()
    main.refresh_token_sessions.clear()
    main.refresh_tokens_by_user.clear()
    main.revoked_refresh_tokens.clear()
    main.security_events_by_user.clear()
    main.login_attempts_by_ip.clear()
    main.security_alert_cooldowns_by_user.clear()
    main.security_alert_dispatch_log.clear()
    main.security_alert_deliveries_by_id.clear()
    main.security_push_tokens_by_user.clear()

    main.MAX_FAILED_LOGIN_ATTEMPTS = 5
    main.ACCOUNT_LOCKOUT_MINUTES = 15
    main.REQUIRE_VERIFIED_EMAIL_FOR_LOGIN = False
    main.EMAIL_VERIFICATION_DEBUG_RETURN_CODE = True
    main.EMAIL_VERIFICATION_MAX_ATTEMPTS = 5
    main.PASSWORD_MIN_LENGTH = 12
    main.STEP_UP_MAX_AGE_MINUTES = 10
    main.REQUIRE_ADMIN_2FA = False
    main.AUTH_SECURITY_ALERTS_ENABLED = False
    main.AUTH_SECURITY_ALERT_EMAIL_ENABLED = False
    main.AUTH_SECURITY_ALERT_PUSH_ENABLED = False
    main.AUTH_SECURITY_ALERT_EMAIL_PROVIDER = "webhook"
    main.AUTH_SECURITY_ALERT_PUSH_PROVIDER = "webhook"
    main.AUTH_SECURITY_ALERT_EMAIL_DISPATCH_URL = ""
    main.AUTH_SECURITY_ALERT_PUSH_DISPATCH_URL = ""
    main.AUTH_SECURITY_ALERT_WEBHOOK_SIGNING_SECRET = ""
    main.AUTH_SECURITY_ALERT_WEBHOOK_SIGNATURE_TTL_SECONDS = 300
    main.AUTH_SECURITY_ALERT_SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"
    main.AUTH_SECURITY_ALERT_SENDGRID_API_KEY = ""
    main.AUTH_SECURITY_ALERT_EXPO_PUSH_API_URL = "https://exp.host/--/api/v2/push/send"
    main.AUTH_SECURITY_ALERT_FCM_API_URL = "https://fcm.googleapis.com/fcm/send"
    main.AUTH_SECURITY_ALERT_FCM_SERVER_KEY = ""
    main.AUTH_SECURITY_ALERT_COOLDOWN_MINUTES = 30
    main.AUTH_SECURITY_ALERT_RECEIPTS_ENABLED = False
    main.AUTH_SECURITY_ALERT_RECEIPT_WEBHOOK_SECRET = ""
    main.AUTH_MOBILE_ATTESTATION_ENABLED = True
    main.AUTH_MOBILE_ATTESTATION_TOKEN_TTL_MINUTES = 10
    main.AUTH_MOBILE_ATTESTATION_REQUIRE_RECENT_AUTH = True
    main.AUTH_LEGAL_CURRENT_VERSION = "2026-Q1"
    main.AUTH_LEGAL_TERMS_URL = "/terms"
    main.AUTH_LEGAL_EULA_URL = "/eula"
    main.AUTH_REQUIRE_LEGAL_ACCEPTANCE = False
    main.AUTH_RUNTIME_STATE_SNAPSHOT_ENABLED = False
    main.AUTH_RUNTIME_STATE_BACKEND = "file"
    main.AUTH_RUNTIME_STATE_REDIS_URL = ""
    main.AUTH_RUNTIME_STATE_REDIS_KEY = "selfmonitor:auth:runtime_state"
    main.AUTH_RUNTIME_STATE_REDIS_TIMEOUT_SECONDS = 0.5
    main.AUTH_RUNTIME_REDIS_SEGMENTED_ENABLED = True
    main.AUTH_RUNTIME_RETENTION_EVENTS_DAYS = 30
    main.AUTH_RUNTIME_RETENTION_DISPATCH_DAYS = 30
    main.AUTH_RUNTIME_RETENTION_DELIVERIES_DAYS = 30
    main.AUTH_RUNTIME_RETENTION_PUSH_REVOKED_DAYS = 90
    main.AUTH_RUNTIME_RETENTION_REFRESH_REVOKED_DAYS = 30
    main.AUTH_RUNTIME_CLEANUP_ENABLED = False
    main.AUTH_RUNTIME_CLEANUP_INTERVAL_SECONDS = 300
    main.runtime_state_redis_client = None
    main.runtime_state_redis_client_initialized = False
    main.runtime_state_redis_warning_logged = False

    main.fake_users_db["admin@example.com"] = main._build_user_record(
        email="admin@example.com",
        hashed_password=main.get_password_hash("admin_password"),
        is_admin=True,
        email_verified=True,
    )


def test_register_user_success() -> None:
    response = client.post(
        "/register",
        data={"username": "test@example.com", "password": "averysecurepassword123!"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "test@example.com"
    assert payload["is_active"] is True
    assert payload["email_verified"] is False
    assert "hashed_password" in main.fake_users_db["test@example.com"]


def test_register_rejects_weak_password() -> None:
    response = client.post(
        "/register",
        data={"username": "weak@example.com", "password": "short"},
    )
    assert response.status_code == 400
    assert "Password must be at least" in response.json()["detail"]


def test_register_user_already_exists() -> None:
    _register("existing@example.com")
    response = client.post(
        "/register",
        data={"username": "existing@example.com", "password": "anotherverysecurepass123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


def test_login_and_get_me_returns_token_pair() -> None:
    email = "login-test@example.com"
    password = "averysecurepassword123!"
    _register(email, password)

    token_payload = _login(email, password)
    assert "access_token" in token_payload
    assert "refresh_token" in token_payload
    assert token_payload["token_type"] == "bearer"
    assert token_payload["expires_in_seconds"] > 0

    me_response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email


def test_login_lockout_after_repeated_failures() -> None:
    email = "lockout@example.com"
    password = "averysecurepassword123!"
    _register(email, password)
    main.MAX_FAILED_LOGIN_ATTEMPTS = 3

    first = client.post("/token", data={"username": email, "password": "wrong-pass"})
    second = client.post("/token", data={"username": email, "password": "wrong-pass"})
    third = client.post("/token", data={"username": email, "password": "wrong-pass"})
    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 423

    locked_response = client.post("/token", data={"username": email, "password": password})
    assert locked_response.status_code == 423


def test_risk_alerts_dispatch_on_failed_login_spike() -> None:
    email = "alerts-spike@example.com"
    password = "averysecurepassword123!"
    _register(email, password)
    main.MAX_FAILED_LOGIN_ATTEMPTS = 4
    main.AUTH_SECURITY_ALERTS_ENABLED = True
    main.AUTH_SECURITY_ALERT_EMAIL_ENABLED = True
    main.AUTH_SECURITY_ALERT_PUSH_ENABLED = True
    main.AUTH_SECURITY_ALERT_EMAIL_DISPATCH_URL = "https://alerts.local/email"
    main.AUTH_SECURITY_ALERT_PUSH_DISPATCH_URL = "https://alerts.local/push"

    captured_calls: list[tuple[str, dict]] = []

    def _capture_dispatch(url: str, payload: dict) -> tuple[str, str]:
        captured_calls.append((url, payload))
        return "sent", "ok"

    with patch.object(main, "_post_json_with_retry", side_effect=_capture_dispatch):
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401

    assert len(captured_calls) == 2
    assert {item[0] for item in captured_calls} == {
        "https://alerts.local/email",
        "https://alerts.local/push",
    }
    assert len(main.security_alert_dispatch_log[email]) >= 1


def test_risk_alert_webhook_dispatch_can_be_signed() -> None:
    email = "alerts-signed-webhook@example.com"
    password = "averysecurepassword123!"
    _register(email, password)
    main.MAX_FAILED_LOGIN_ATTEMPTS = 4
    main.AUTH_SECURITY_ALERTS_ENABLED = True
    main.AUTH_SECURITY_ALERT_EMAIL_ENABLED = True
    main.AUTH_SECURITY_ALERT_PUSH_ENABLED = False
    main.AUTH_SECURITY_ALERT_EMAIL_PROVIDER = "webhook"
    main.AUTH_SECURITY_ALERT_EMAIL_DISPATCH_URL = "https://alerts.local/email"
    main.AUTH_SECURITY_ALERT_WEBHOOK_SIGNING_SECRET = "outbound-signing-secret"

    captured_calls: list[tuple[str, dict, dict | None]] = []

    def _capture_dispatch(url: str, payload: dict, headers: dict | None = None) -> tuple[str, str, dict]:
        captured_calls.append((url, payload, headers))
        return "sent", "ok", {"ack": True}

    with patch.object(main, "_post_json_with_retry_extended", side_effect=_capture_dispatch):
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401

    assert len(captured_calls) == 1
    _, payload, headers = captured_calls[0]
    assert headers
    timestamp = headers["X-SelfMonitor-Signature-Timestamp"]
    signature = headers["X-SelfMonitor-Signature"]
    canonical_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    expected = hmac.new(
        main.AUTH_SECURITY_ALERT_WEBHOOK_SIGNING_SECRET.encode("utf-8"),
        f"{timestamp}.{canonical_payload}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert signature == expected


def test_risk_alert_sendgrid_provider_dispatches_payload() -> None:
    email = "alerts-sendgrid@example.com"
    password = "averysecurepassword123!"
    _register(email, password)
    main.MAX_FAILED_LOGIN_ATTEMPTS = 4
    main.AUTH_SECURITY_ALERTS_ENABLED = True
    main.AUTH_SECURITY_ALERT_EMAIL_ENABLED = True
    main.AUTH_SECURITY_ALERT_PUSH_ENABLED = False
    main.AUTH_SECURITY_ALERT_EMAIL_PROVIDER = "sendgrid"
    main.AUTH_SECURITY_ALERT_SENDGRID_API_KEY = "sendgrid-test-key"

    captured_calls: list[tuple[str, dict, dict | None]] = []

    def _capture_dispatch(url: str, payload: dict, headers: dict | None = None) -> tuple[str, str, None]:
        captured_calls.append((url, payload, headers))
        return "sent", "ok", None

    with patch.object(main, "_post_json_with_retry_extended", side_effect=_capture_dispatch):
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401

    assert len(captured_calls) == 1
    url, payload, headers = captured_calls[0]
    assert url == main.AUTH_SECURITY_ALERT_SENDGRID_API_URL
    assert headers and headers["Authorization"] == f"Bearer {main.AUTH_SECURITY_ALERT_SENDGRID_API_KEY}"
    assert "personalizations" in payload
    custom_args = payload["personalizations"][0]["custom_args"]
    dispatch_id = custom_args["dispatch_id"]
    latest_delivery = main.security_alert_dispatch_log[email][-1]
    assert latest_delivery["dispatch_id"] == dispatch_id


def test_security_push_token_registration_and_expo_push_dispatch() -> None:
    email = "alerts-expo@example.com"
    password = "averysecurepassword123!"
    _register(email, password)
    login_payload = _login(email, password)
    auth_headers = {"Authorization": f"Bearer {login_payload['access_token']}"}

    register_response = client.post(
        "/security/push-tokens",
        headers=auth_headers,
        json={"push_token": "ExponentPushToken[testTokenValue]", "provider": "expo"},
    )
    assert register_response.status_code == 200
    assert register_response.json()["total_active_tokens"] == 1

    main.MAX_FAILED_LOGIN_ATTEMPTS = 4
    main.AUTH_SECURITY_ALERTS_ENABLED = True
    main.AUTH_SECURITY_ALERT_EMAIL_ENABLED = False
    main.AUTH_SECURITY_ALERT_PUSH_ENABLED = True
    main.AUTH_SECURITY_ALERT_PUSH_PROVIDER = "expo"

    captured_calls: list[tuple[str, dict | list, dict | None]] = []

    def _capture_dispatch(
        url: str, payload: dict | list, headers: dict | None = None
    ) -> tuple[str, str, dict]:
        captured_calls.append((url, payload, headers))
        return "sent", "ok", {"data": [{"status": "ok", "id": "expo-ticket-1"}]}

    with patch.object(main, "_post_json_with_retry_extended", side_effect=_capture_dispatch):
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401

    assert len(captured_calls) == 1
    url, payload, _headers = captured_calls[0]
    assert url == main.AUTH_SECURITY_ALERT_EXPO_PUSH_API_URL
    payload_item = payload[0] if isinstance(payload, list) else payload
    assert payload_item["to"] == "ExponentPushToken[testTokenValue]"
    latest_delivery = main.security_alert_dispatch_log[email][-1]
    assert latest_delivery["channels"]["push"]["provider_message_id"] == "expo-ticket-1"

    tokens_response = client.get("/security/push-tokens", headers=auth_headers)
    assert tokens_response.status_code == 200
    tokens_payload = tokens_response.json()
    assert tokens_payload["total_tokens"] == 1
    assert tokens_payload["items"][0]["last_used_at"] is not None


def test_security_alert_delivery_receipt_endpoint_updates_delivery_status() -> None:
    email = "alerts-receipt@example.com"
    password = "averysecurepassword123!"
    _register(email, password)
    login_payload = _login(email, password)
    auth_headers = {"Authorization": f"Bearer {login_payload['access_token']}"}
    main.MAX_FAILED_LOGIN_ATTEMPTS = 4
    main.AUTH_SECURITY_ALERTS_ENABLED = True
    main.AUTH_SECURITY_ALERT_EMAIL_ENABLED = True
    main.AUTH_SECURITY_ALERT_PUSH_ENABLED = False
    main.AUTH_SECURITY_ALERT_EMAIL_PROVIDER = "webhook"
    main.AUTH_SECURITY_ALERT_EMAIL_DISPATCH_URL = "https://alerts.local/email"

    with patch.object(main, "_post_json_with_retry", return_value=("sent", "ok")):
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401
        assert client.post("/token", data={"username": email, "password": "wrong-pass"}).status_code == 401

    dispatch_id = main.security_alert_dispatch_log[email][-1]["dispatch_id"]
    main.AUTH_SECURITY_ALERT_RECEIPTS_ENABLED = True
    main.AUTH_SECURITY_ALERT_RECEIPT_WEBHOOK_SECRET = "receipt-ingress-secret"

    receipt_payload = {
        "dispatch_id": dispatch_id,
        "channel": "email",
        "status": "delivered",
        "provider_message_id": "msg-123",
    }
    raw_body = json.dumps(receipt_payload)
    timestamp = str(int(datetime.datetime.now(datetime.UTC).timestamp()))
    signature = hmac.new(
        main.AUTH_SECURITY_ALERT_RECEIPT_WEBHOOK_SECRET.encode("utf-8"),
        f"{timestamp}.{raw_body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    receipt_response = client.post(
        "/security/alerts/delivery-receipts",
        data=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-SelfMonitor-Signature-Timestamp": timestamp,
            "X-SelfMonitor-Signature": signature,
        },
    )
    assert receipt_response.status_code == 200
    assert receipt_response.json()["updated"] is True

    delivery_item = main.security_alert_deliveries_by_id[dispatch_id]
    assert delivery_item["channels"]["email"]["receipt_status"] == "delivered"
    assert delivery_item["status"] in {"delivered", "partial_delivery"}

    deliveries_response = client.get("/security/alerts/deliveries?limit=5", headers=auth_headers)
    assert deliveries_response.status_code == 200
    assert any(item["dispatch_id"] == dispatch_id for item in deliveries_response.json()["items"])


def test_refresh_token_rotation_rejects_reuse() -> None:
    email = "refresh@example.com"
    password = "averysecurepassword123!"
    _register(email, password)
    token_payload = _login(email, password)
    refresh_1 = token_payload["refresh_token"]

    rotate_response = client.post("/token/refresh", json={"refresh_token": refresh_1})
    assert rotate_response.status_code == 200
    refresh_2 = rotate_response.json()["refresh_token"]
    assert refresh_2 != refresh_1

    reused = client.post("/token/refresh", json={"refresh_token": refresh_1})
    assert reused.status_code == 401

    second_rotation = client.post("/token/refresh", json={"refresh_token": refresh_2})
    assert second_rotation.status_code == 200


def test_password_change_invalidates_old_tokens() -> None:
    email = "password-change@example.com"
    old_password = "oldverysecurepassword123!"
    new_password = "newverysecurepassword123!"
    _register(email, old_password)
    token_payload = _login(email, old_password)

    change_response = client.post(
        "/password/change",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
        json={"current_password": old_password, "new_password": new_password},
    )
    assert change_response.status_code == 200

    old_me = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )
    assert old_me.status_code == 401

    old_refresh = client.post("/token/refresh", json={"refresh_token": token_payload["refresh_token"]})
    assert old_refresh.status_code == 401

    wrong_login = client.post("/token", data={"username": email, "password": old_password})
    assert wrong_login.status_code == 401

    new_login = client.post("/token", data={"username": email, "password": new_password})
    assert new_login.status_code == 200


def test_email_verification_flow() -> None:
    email = "verify@example.com"
    password = "averysecurepassword123!"
    _register(email, password)
    token_payload = _login(email, password)

    request_response = client.post(
        "/verify-email/request",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )
    assert request_response.status_code == 200
    debug_code = request_response.json()["debug_code"]
    assert debug_code

    confirm_response = client.post(
        "/verify-email/confirm",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
        json={"code": debug_code},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["email_verified"] is True

    me_response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email_verified"] is True


def test_security_state_and_events_endpoints() -> None:
    email = "security-events@example.com"
    password = "averysecurepassword123!"
    _register(email, password)
    token_payload = _login(email, password)

    state_response = client.get(
        "/security/state",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )
    assert state_response.status_code == 200
    assert state_response.json()["email"] == email
    assert state_response.json()["max_failed_login_attempts"] == main.MAX_FAILED_LOGIN_ATTEMPTS

    events_response = client.get(
        "/security/events?limit=10",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )
    assert events_response.status_code == 200
    events_payload = events_response.json()
    assert events_payload["total"] >= 1
    assert any(item["event_type"] == "auth.login_succeeded" for item in events_payload["items"])


def test_legal_policy_current_and_acceptance_flow() -> None:
    email = "legal-accept@example.com"
    password = "stronglegalpassword123!"
    _register(email, password)
    login_payload = _login(email, password)
    headers = {"Authorization": f"Bearer {login_payload['access_token']}"}

    current_response = client.get("/legal/current")
    assert current_response.status_code == 200
    current_payload = current_response.json()
    assert current_payload["current_version"] == main.AUTH_LEGAL_CURRENT_VERSION
    assert current_payload["terms_url"] == main.AUTH_LEGAL_TERMS_URL
    assert current_payload["eula_url"] == main.AUTH_LEGAL_EULA_URL

    state_before = client.get("/security/state", headers=headers)
    assert state_before.status_code == 200
    assert state_before.json()["has_accepted_current_legal"] is False

    accept_response = client.post(
        "/legal/accept",
        headers=headers,
        json={"version": main.AUTH_LEGAL_CURRENT_VERSION, "source": "web_security_center"},
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["has_accepted_current_legal"] is True

    state_after = client.get("/security/state", headers=headers)
    assert state_after.status_code == 200
    assert state_after.json()["legal_accepted_version"] == main.AUTH_LEGAL_CURRENT_VERSION
    assert state_after.json()["has_accepted_current_legal"] is True


def test_runtime_cleanup_cycle_prunes_stale_records() -> None:
    email = "cleanup@example.com"
    _register(email, "vaultstrongpassword123!")

    main.AUTH_RUNTIME_RETENTION_EVENTS_DAYS = 1
    main.AUTH_RUNTIME_RETENTION_DISPATCH_DAYS = 1
    main.AUTH_RUNTIME_RETENTION_DELIVERIES_DAYS = 1
    main.AUTH_RUNTIME_RETENTION_PUSH_REVOKED_DAYS = 1
    main.AUTH_RUNTIME_RETENTION_REFRESH_REVOKED_DAYS = 1
    main.AUTH_SECURITY_ALERT_COOLDOWN_MINUTES = 1
    main.LOGIN_IP_WINDOW_SECONDS = 60

    now = datetime.datetime.now(datetime.UTC)
    stale = now - datetime.timedelta(days=2)
    fresh = now - datetime.timedelta(seconds=30)

    main.security_events_by_user[email].append(
        main.SecurityEvent(event_type="auth.login_failed", occurred_at=stale, details={"failed_attempts": 1})
    )
    main.security_events_by_user[email].append(
        main.SecurityEvent(event_type="auth.login_succeeded", occurred_at=fresh, details={})
    )

    main.login_attempts_by_ip["203.0.113.10"].append(stale)
    main.login_attempts_by_ip["203.0.113.10"].append(fresh)

    main.security_alert_cooldowns_by_user[email]["failed_login_spike"] = stale
    main.security_alert_cooldowns_by_user[email]["recent_login_ip"] = fresh

    main.security_alert_dispatch_log[email].append({"dispatch_id": "dispatch-old", "occurred_at": stale.isoformat()})
    main.security_alert_dispatch_log[email].append({"dispatch_id": "dispatch-fresh", "occurred_at": fresh.isoformat()})

    main.security_alert_deliveries_by_id["dispatch-old"] = {"dispatch_id": "dispatch-old", "occurred_at": stale.isoformat()}
    main.security_alert_deliveries_by_id["dispatch-fresh"] = {
        "dispatch_id": "dispatch-fresh",
        "occurred_at": fresh.isoformat(),
    }

    main.security_push_tokens_by_user[email]["ExponentPushToken[stale]"] = {
        "provider": "expo",
        "registered_at": stale,
        "last_used_at": stale,
        "revoked_at": stale,
    }
    main.security_push_tokens_by_user[email]["ExponentPushToken[fresh]"] = {
        "provider": "expo",
        "registered_at": fresh,
        "last_used_at": fresh,
        "revoked_at": None,
    }

    main.refresh_token_sessions["refresh-stale"] = {
        "email": email,
        "issued_at": stale,
        "expires_at": stale,
        "revoked_at": stale,
    }
    main.refresh_token_sessions["refresh-fresh"] = {
        "email": email,
        "issued_at": fresh,
        "expires_at": now + datetime.timedelta(days=7),
        "revoked_at": None,
    }
    main.refresh_tokens_by_user[email].update({"refresh-stale", "refresh-fresh"})
    main.revoked_refresh_tokens.update({"refresh-stale"})

    changed = main._run_runtime_state_cleanup_cycle(now_utc=now)
    assert changed is True

    assert "refresh-stale" not in main.refresh_token_sessions
    assert "refresh-fresh" in main.refresh_token_sessions
    assert "refresh-stale" not in main.revoked_refresh_tokens
    assert main.refresh_tokens_by_user[email] == {"refresh-fresh"}

    assert len(main.security_events_by_user[email]) == 1
    assert main.security_events_by_user[email][0].event_type == "auth.login_succeeded"
    assert list(main.login_attempts_by_ip["203.0.113.10"]) == [fresh]
    assert set(main.security_alert_cooldowns_by_user[email].keys()) == {"recent_login_ip"}
    assert len(main.security_alert_dispatch_log[email]) == 1
    assert "dispatch-old" not in main.security_alert_deliveries_by_id
    assert "dispatch-fresh" in main.security_alert_deliveries_by_id
    assert "ExponentPushToken[stale]" not in main.security_push_tokens_by_user[email]


def test_security_sessions_management_endpoints() -> None:
    email = "sessions@example.com"
    password = "walletshieldpassword123!"
    _register(email, password)
    login_one = _login(email, password)
    login_two = _login(email, password)
    auth_headers = {"Authorization": f"Bearer {login_two['access_token']}"}

    sessions_response = client.get("/security/sessions", headers=auth_headers)
    assert sessions_response.status_code == 200
    sessions_payload = sessions_response.json()
    assert sessions_payload["active_sessions"] >= 2
    assert sessions_payload["total_sessions"] >= 2

    refresh_1_payload = jwt.decode(login_one["refresh_token"], main.SECRET_KEY, algorithms=[main.ALGORITHM])
    session_id = refresh_1_payload["jti"]
    revoke_one = client.delete(f"/security/sessions/{session_id}", headers=auth_headers)
    assert revoke_one.status_code == 200
    assert revoke_one.json()["revoked_sessions"] == 1

    refresh_with_revoked = client.post("/token/refresh", json={"refresh_token": login_one["refresh_token"]})
    assert refresh_with_revoked.status_code == 401

    revoke_all = client.post("/security/sessions/revoke-all", headers=auth_headers)
    assert revoke_all.status_code == 200
    assert revoke_all.json()["revoked_sessions"] >= 1

    refresh_after_revoke_all = client.post("/token/refresh", json={"refresh_token": login_two["refresh_token"]})
    assert refresh_after_revoke_all.status_code == 401


def test_emergency_security_lockdown_revokes_sessions_and_blocks_login() -> None:
    email = "panic-lock@example.com"
    password = "fortresssecurepassword123!"
    _register(email, password)
    login_payload = _login(email, password)
    access_token = login_payload["access_token"]
    refresh_token = login_payload["refresh_token"]

    lockdown_response = client.post(
        "/security/lockdown",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"lock_minutes": 30},
    )
    assert lockdown_response.status_code == 200
    payload = lockdown_response.json()
    assert payload["lock_minutes"] == 30
    assert payload["revoked_sessions"] >= 1
    assert payload["locked_until"]

    old_refresh = client.post("/token/refresh", json={"refresh_token": refresh_token})
    assert old_refresh.status_code == 401

    old_access = client.get("/security/state", headers={"Authorization": f"Bearer {access_token}"})
    assert old_access.status_code == 401

    blocked_login = client.post("/token", data={"username": email, "password": password})
    assert blocked_login.status_code == 423


def test_mobile_attestation_session_gates_mobile_sensitive_endpoints() -> None:
    email = "mobile-attest@example.com"
    password = "shieldedpassword123!"
    _register(email, password)
    login_payload = _login(email, password)
    auth_headers = {"Authorization": f"Bearer {login_payload['access_token']}"}

    missing_attestation = client.post(
        "/mobile/security/push-tokens",
        headers=auth_headers,
        json={"push_token": "ExponentPushToken[mobileAttestValue]", "provider": "expo"},
    )
    assert missing_attestation.status_code == 401

    installation_id = "mobile-installation-1234"
    attestation_response = client.post(
        "/mobile/attestation/session",
        headers=auth_headers,
        json={"installation_id": installation_id},
    )
    assert attestation_response.status_code == 200
    attestation_payload = attestation_response.json()
    assert attestation_payload["installation_id"] == installation_id
    assert attestation_payload["attestation_token"]

    mobile_headers = {
        "Authorization": f"Bearer {login_payload['access_token']}",
        "X-SelfMonitor-Mobile-Attestation": attestation_payload["attestation_token"],
        "X-SelfMonitor-Mobile-Installation-Id": installation_id,
    }
    register_response = client.post(
        "/mobile/security/push-tokens",
        headers=mobile_headers,
        json={"push_token": "ExponentPushToken[mobileAttestValue]", "provider": "expo"},
    )
    assert register_response.status_code == 200
    assert register_response.json()["total_active_tokens"] == 1

    wrong_installation_headers = dict(mobile_headers)
    wrong_installation_headers["X-SelfMonitor-Mobile-Installation-Id"] = "other-installation"
    denied_response = client.post(
        "/mobile/security/push-tokens",
        headers=wrong_installation_headers,
        json={"push_token": "ExponentPushToken[mobileAttestValue2]", "provider": "expo"},
    )
    assert denied_response.status_code == 403

    lockdown_response = client.post(
        "/mobile/security/lockdown",
        headers=mobile_headers,
        json={"lock_minutes": 30},
    )
    assert lockdown_response.status_code == 200
    assert lockdown_response.json()["lock_minutes"] == 30


def test_risk_alerts_dispatch_on_emergency_lockdown() -> None:
    email = "alerts-lockdown@example.com"
    password = "fortresssecurepassword123!"
    _register(email, password)
    login_payload = _login(email, password)
    main.AUTH_SECURITY_ALERTS_ENABLED = True
    main.AUTH_SECURITY_ALERT_EMAIL_ENABLED = True
    main.AUTH_SECURITY_ALERT_PUSH_ENABLED = True
    main.AUTH_SECURITY_ALERT_EMAIL_DISPATCH_URL = "https://alerts.local/email"
    main.AUTH_SECURITY_ALERT_PUSH_DISPATCH_URL = "https://alerts.local/push"

    captured_calls: list[tuple[str, dict]] = []

    def _capture_dispatch(url: str, payload: dict) -> tuple[str, str]:
        captured_calls.append((url, payload))
        return "sent", "ok"

    with patch.object(main, "_post_json_with_retry", side_effect=_capture_dispatch):
        lockdown_response = client.post(
            "/security/lockdown",
            headers={"Authorization": f"Bearer {login_payload['access_token']}"},
            json={"lock_minutes": 30},
        )
        assert lockdown_response.status_code == 200

    assert len(captured_calls) == 2
    events = list(main.security_events_by_user[email])
    lockdown_events = [event for event in events if event.event_type == "auth.account_lockdown_activated"]
    assert lockdown_events
    delivery = lockdown_events[-1].details.get("risk_alert_delivery")
    assert isinstance(delivery, dict)
    assert delivery.get("status") == "dispatched"


def test_step_up_required_for_sensitive_action_with_stale_token() -> None:
    email = "stepup@example.com"
    password = "guardianpassword123!"
    new_password = "freshguardianpassword123!"
    _register(email, password)

    token_version = int(main.fake_users_db[email]["user_data"]["token_version"])
    stale_iat = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=main.STEP_UP_MAX_AGE_MINUTES + 5)
    stale_token = jwt.encode(
        {
            "sub": email,
            "roles": ["user"],
            "scopes": [],
            "is_admin": False,
            "tv": token_version,
            "typ": "access",
            "iat": stale_iat,
            "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=20),
        },
        main.SECRET_KEY,
        algorithm=main.ALGORITHM,
    )
    response = client.post(
        "/password/change",
        headers={"Authorization": f"Bearer {stale_token}"},
        json={"current_password": password, "new_password": new_password},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Step-up authentication required."


def test_admin_endpoint_can_require_2fa() -> None:
    main.REQUIRE_ADMIN_2FA = True
    target_email = "target@example.com"
    _register(target_email, "vaultsecurepassword123!")

    admin_login = _login("admin@example.com", "admin_password")
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}
    blocked = client.post(f"/users/{target_email}/deactivate", headers=admin_headers)
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Admin action requires 2FA to be enabled."

    setup_response = client.get("/2fa/setup", headers=admin_headers)
    assert setup_response.status_code == 200
    admin_secret = main.fake_users_db["admin@example.com"]["user_data"]["two_factor_secret"]
    admin_totp = pyotp.TOTP(admin_secret)
    verify_response = client.post(f"/2fa/verify?totp_code={admin_totp.now()}", headers=admin_headers)
    assert verify_response.status_code == 200

    admin_login_with_2fa = _login(
        "admin@example.com",
        "admin_password",
        scope=f"totp:{admin_totp.now()}",
    )
    admin_headers_with_2fa = {"Authorization": f"Bearer {admin_login_with_2fa['access_token']}"}
    allowed = client.post(f"/users/{target_email}/deactivate", headers=admin_headers_with_2fa)
    assert allowed.status_code == 200


def test_two_factor_flow_requires_code_on_login_and_disable() -> None:
    email = "twofa@example.com"
    password = "averysecurepassword123!"
    _register(email, password)
    login_payload = _login(email, password)
    auth_headers = {"Authorization": f"Bearer {login_payload['access_token']}"}

    request_response = client.post("/verify-email/request", headers=auth_headers)
    code = request_response.json()["debug_code"]
    confirm_response = client.post("/verify-email/confirm", headers=auth_headers, json={"code": code})
    assert confirm_response.status_code == 200

    setup_response = client.get("/2fa/setup", headers=auth_headers)
    assert setup_response.status_code == 200
    assert setup_response.headers["content-type"].startswith("image/png")

    secret = main.fake_users_db[email]["user_data"]["two_factor_secret"]
    totp = pyotp.TOTP(secret)
    verify_response = client.post(f"/2fa/verify?totp_code={totp.now()}", headers=auth_headers)
    assert verify_response.status_code == 200

    missing_2fa = client.post("/token", data={"username": email, "password": password})
    assert missing_2fa.status_code == 401

    login_with_2fa = client.post(
        "/token",
        data={"username": email, "password": password, "scope": f"totp:{totp.now()}"},
    )
    assert login_with_2fa.status_code == 200
    login_with_2fa_token = login_with_2fa.json()["access_token"]

    disable_missing = client.delete(
        "/2fa/disable",
        headers={"Authorization": f"Bearer {login_with_2fa_token}"},
    )
    assert disable_missing.status_code == 400

    disable_ok = client.delete(
        f"/2fa/disable?totp_code={totp.now()}",
        headers={"Authorization": f"Bearer {login_with_2fa_token}"},
    )
    assert disable_ok.status_code == 204


def test_deactivate_user_revokes_old_tokens() -> None:
    user_email = "user@example.com"
    user_pass = "verysecurefintechpassword123!"
    _register(user_email, user_pass)
    user_login_response = _login(user_email, user_pass)
    user_access_token = user_login_response["access_token"]
    user_refresh_token = user_login_response["refresh_token"]

    admin_login_response = _login("admin@example.com", "admin_password")
    admin_token = admin_login_response["access_token"]
    admin_auth_headers = {"Authorization": f"Bearer {admin_token}"}

    deactivate_response = client.post(f"/users/{user_email}/deactivate", headers=admin_auth_headers)
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    old_access_me_response = client.get("/me", headers={"Authorization": f"Bearer {user_access_token}"})
    assert old_access_me_response.status_code == 401

    old_refresh_response = client.post("/token/refresh", json={"refresh_token": user_refresh_token})
    assert old_refresh_response.status_code == 401


def test_non_admin_cannot_deactivate() -> None:
    user1_email = "user1@example.com"
    user2_email = "user2@example.com"
    user2_pass = "verysecurepassword5678!"
    _register(user1_email, "verysecurepassword1234!")
    _register(user2_email, user2_pass)

    user2_login_response = _login(user2_email, user2_pass)
    user2_auth_headers = {"Authorization": f"Bearer {user2_login_response['access_token']}"}

    deactivate_response = client.post(f"/users/{user1_email}/deactivate", headers=user2_auth_headers)
    assert deactivate_response.status_code == 403
    assert deactivate_response.json()["detail"] == "Admin access required"


def test_admin_token_contains_billing_claims() -> None:
    login_response = client.post("/token", data={"username": "admin@example.com", "password": "admin_password"})
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    payload = jwt.decode(token, main.SECRET_KEY, algorithms=[main.ALGORITHM])

    assert payload["sub"] == "admin@example.com"
    assert payload["is_admin"] is True
    assert "admin" in payload["roles"]
    assert "billing:read" in payload["scopes"]


def test_regular_user_token_has_no_billing_scope() -> None:
    email = "regular@example.com"
    password = "strongfinancepassword123!"
    _register(email, password)

    login_response = client.post("/token", data={"username": email, "password": password})
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    payload = jwt.decode(token, main.SECRET_KEY, algorithms=[main.ALGORITHM])

    assert payload["sub"] == email
    assert payload["is_admin"] is False
    assert payload["roles"] == ["user"]
    assert payload["scopes"] == []
