import os
import sys

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

    main.MAX_FAILED_LOGIN_ATTEMPTS = 5
    main.ACCOUNT_LOCKOUT_MINUTES = 15
    main.REQUIRE_VERIFIED_EMAIL_FOR_LOGIN = False
    main.EMAIL_VERIFICATION_DEBUG_RETURN_CODE = True
    main.EMAIL_VERIFICATION_MAX_ATTEMPTS = 5
    main.PASSWORD_MIN_LENGTH = 12

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
