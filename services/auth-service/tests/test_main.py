from fastapi.testclient import TestClient
# We need to adjust the path to import the app from the parent directory
import sys
import os
os.environ["AUTH_SECRET_KEY"] = "test-secret"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import (
    app, get_user_record, reset_auth_db_for_tests, set_user_admin_for_tests,
    _login_attempts,
)
import pyotp

client = TestClient(app)

STRONG_PASSWORD = "TestP@ssw0rd!"
STRONG_PASSWORD_2 = "N3wSecure!Pass"


def setup_function():
    reset_auth_db_for_tests()
    _login_attempts.clear()


def _register_and_login(email, password=STRONG_PASSWORD):
    client.post("/register", json={"email": email, "password": password})
    resp = client.post("/token", data={"username": email, "password": password})
    return resp.json()["access_token"]


def test_register_user_success():
    """
    Test that a new user can be registered successfully.
    """
    response = client.post(
        "/register",
        json={"email": "test@example.com", "password": STRONG_PASSWORD},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["is_active"] is True

    # Check that the password is not stored in plain text
    user_record = get_user_record("test@example.com")
    assert user_record is not None
    assert "password" not in user_record
    assert "hashed_password" in user_record
    assert user_record["hashed_password"] != STRONG_PASSWORD

def test_register_user_already_exists():
    """
    Test that registering a user with an email that already exists fails.
    """
    client.post(
        "/register",
        json={"email": "existing@example.com", "password": STRONG_PASSWORD},
    )
    response = client.post(
        "/register",
        json={"email": "existing@example.com", "password": STRONG_PASSWORD},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Email already registered"}

def test_login_and_get_me():
    """
    Test that a user can log in and then access a protected endpoint.
    """
    email = "login-test@example.com"
    register_response = client.post("/register", json={"email": email, "password": STRONG_PASSWORD})
    assert register_response.status_code == 201

    login_response = client.post(
        "/token",
        data={"username": email, "password": STRONG_PASSWORD}
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    access_token = token_data["access_token"]
    me_response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_response.status_code == 200
    user_data = me_response.json()
    assert user_data["email"] == email

def test_login_wrong_password():
    """
    Test that login fails with an incorrect password.
    """
    email = "wrong-pass@example.com"
    client.post("/register", json={"email": email, "password": STRONG_PASSWORD})

    response = client.post(
        "/token",
        data={"username": email, "password": "WrongP@ss1!"}
    )
    assert response.status_code == 401
    assert response.json()['detail'] == "Incorrect username or password"

def test_get_me_invalid_token():
    """
    Test that a protected endpoint cannot be accessed with an invalid token.
    """
    response = client.get(
        "/me",
        headers={"Authorization": "Bearer an-invalid-token"}
    )
    assert response.status_code == 401
    assert response.json()['detail'] == "Could not validate credentials"

def test_deactivate_user():
    admin_email = "admin@example.com"
    admin_pass = STRONG_PASSWORD
    client.post("/register", json={"email": admin_email, "password": admin_pass})
    set_user_admin_for_tests(admin_email, True)

    user_email = "user@example.com"
    user_pass = STRONG_PASSWORD
    client.post("/register", json={"email": user_email, "password": user_pass})

    admin_login_response = client.post("/token", data={"username": admin_email, "password": admin_pass})
    admin_token = admin_login_response.json()["access_token"]
    admin_auth_headers = {"Authorization": f"Bearer {admin_token}"}

    deactivate_response = client.post(f"/users/{user_email}/deactivate", headers=admin_auth_headers)
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    user_login_response = client.post("/token", data={"username": user_email, "password": user_pass})
    assert user_login_response.status_code == 200
    user_token = user_login_response.json()["access_token"]

    me_response = client.get("/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_response.status_code == 401
    assert me_response.json()["detail"] == "Inactive user"

def test_non_admin_cannot_deactivate():
    user1_email = "user1@example.com"
    client.post("/register", json={"email": user1_email, "password": STRONG_PASSWORD})

    user2_email = "user2@example.com"
    client.post("/register", json={"email": user2_email, "password": STRONG_PASSWORD})

    user2_login_response = client.post("/token", data={"username": user2_email, "password": STRONG_PASSWORD})
    user2_token = user2_login_response.json()["access_token"]
    user2_auth_headers = {"Authorization": f"Bearer {user2_token}"}

    deactivate_response = client.post(f"/users/{user1_email}/deactivate", headers=user2_auth_headers)
    assert deactivate_response.status_code == 403
    assert deactivate_response.json()["detail"] == "Admin access required"


# --- New tests ---

def test_password_strength_weak_password_rejected():
    """Weak passwords should be rejected at registration."""
    weak_passwords = [
        ("lowercase1!", "at least one uppercase letter"),
        ("UPPERCASE1!", "at least one lowercase letter"),
        ("NoDigits!!", "at least one digit"),
        ("NoSpecial1a", "at least one special character"),
        ("Sh0r!", "at least 8 characters"),
    ]
    for pwd, expected_fragment in weak_passwords:
        response = client.post(
            "/register",
            json={"email": f"weak-{pwd}@example.com", "password": pwd},
        )
        assert response.status_code in (400, 422), f"Expected 400/422 for password '{pwd}', got {response.status_code}"
        if response.status_code == 400:
            assert expected_fragment in response.json()["detail"], \
                f"Expected '{expected_fragment}' in detail for password '{pwd}'"


def test_account_lockout_after_failed_attempts():
    """After 5 failed login attempts, account should be locked."""
    email = "lockout@example.com"
    client.post("/register", json={"email": email, "password": STRONG_PASSWORD})

    for i in range(5):
        resp = client.post("/token", data={"username": email, "password": "WrongP@ss1!"})
        assert resp.status_code == 401, f"Attempt {i+1} should return 401"

    resp = client.post("/token", data={"username": email, "password": STRONG_PASSWORD})
    assert resp.status_code == 429
    assert "locked" in resp.json()["detail"].lower()


def test_successful_login_clears_failed_attempts():
    """A successful login should clear the failed attempts counter."""
    email = "clear-lockout@example.com"
    client.post("/register", json={"email": email, "password": STRONG_PASSWORD})

    for _ in range(3):
        client.post("/token", data={"username": email, "password": "WrongP@ss1!"})

    resp = client.post("/token", data={"username": email, "password": STRONG_PASSWORD})
    assert resp.status_code == 200

    for _ in range(3):
        client.post("/token", data={"username": email, "password": "WrongP@ss1!"})

    resp = client.post("/token", data={"username": email, "password": STRONG_PASSWORD})
    assert resp.status_code == 200


def test_2fa_required_response():
    """When 2FA is enabled and no code is provided, should get 403 with 2FA_REQUIRED."""
    email = "twofa@example.com"
    token = _register_and_login(email)
    headers = {"Authorization": f"Bearer {token}"}

    setup_resp = client.get("/2fa/setup-json", headers=headers)
    assert setup_resp.status_code == 200
    secret = setup_resp.json()["secret"]

    totp = pyotp.TOTP(secret)
    code = totp.now()
    verify_resp = client.post(f"/2fa/verify?totp_code={code}", headers=headers)
    assert verify_resp.status_code == 200

    login_resp = client.post("/token", data={"username": email, "password": STRONG_PASSWORD})
    assert login_resp.status_code == 403
    assert login_resp.json()["detail"] == "2FA_REQUIRED"
    assert login_resp.headers.get("X-2FA-Required") == "true"


def test_2fa_login_with_code():
    """Login with valid 2FA code should succeed."""
    email = "twofa-login@example.com"
    token = _register_and_login(email)
    headers = {"Authorization": f"Bearer {token}"}

    setup_resp = client.get("/2fa/setup-json", headers=headers)
    secret = setup_resp.json()["secret"]

    totp = pyotp.TOTP(secret)
    client.post(f"/2fa/verify?totp_code={totp.now()}", headers=headers)

    login_resp = client.post(
        "/token",
        data={"username": email, "password": STRONG_PASSWORD, "scope": f"totp:{totp.now()}"}
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_2fa_setup_json_endpoint():
    """The /2fa/setup-json endpoint should return secret and provisioning URI."""
    email = "setup-json@example.com"
    token = _register_and_login(email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/2fa/setup-json", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "secret" in data
    assert "provisioning_uri" in data
    assert data["issuer"] == "SelfMonitor"
    assert email.replace("@", "%40") in data["provisioning_uri"]


def test_2fa_setup_json_already_enabled():
    """Should reject setup-json if 2FA is already enabled."""
    email = "setup-json-dup@example.com"
    token = _register_and_login(email)
    headers = {"Authorization": f"Bearer {token}"}

    setup_resp = client.get("/2fa/setup-json", headers=headers)
    secret = setup_resp.json()["secret"]
    totp = pyotp.TOTP(secret)
    client.post(f"/2fa/verify?totp_code={totp.now()}", headers=headers)

    resp = client.get("/2fa/setup-json", headers=headers)
    assert resp.status_code == 400
    assert "already enabled" in resp.json()["detail"].lower()


def test_change_password_success():
    """Should change password when current password is correct."""
    email = "change-pw@example.com"
    token = _register_and_login(email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/change-password", json={
        "current_password": STRONG_PASSWORD,
        "new_password": STRONG_PASSWORD_2,
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Password changed successfully"

    login_resp = client.post("/token", data={"username": email, "password": STRONG_PASSWORD_2})
    assert login_resp.status_code == 200


def test_change_password_wrong_current():
    """Should reject password change when current password is wrong."""
    email = "change-pw-wrong@example.com"
    token = _register_and_login(email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/change-password", json={
        "current_password": "WrongP@ss1!",
        "new_password": STRONG_PASSWORD_2,
    }, headers=headers)
    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"].lower()


def test_change_password_weak_new():
    """Should reject password change when new password is weak."""
    email = "change-pw-weak@example.com"
    token = _register_and_login(email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/change-password", json={
        "current_password": STRONG_PASSWORD,
        "new_password": "weak",
    }, headers=headers)
    assert resp.status_code == 422  # Pydantic validation (min_length=8)
