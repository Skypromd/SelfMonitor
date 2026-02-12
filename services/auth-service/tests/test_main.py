from fastapi.testclient import TestClient
from jose import jwt
# We need to adjust the path to import the app from the parent directory
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import ALGORITHM, SECRET_KEY, app, fake_users_db, get_password_hash

client = TestClient(app)

def setup_function():
    # Reset the in-memory database before each test and keep seeded admin user.
    fake_users_db.clear()
    fake_users_db["admin@example.com"] = {
        "user_data": {
            "email": "admin@example.com",
            "is_active": True,
            "is_admin": True,
            "two_factor_secret": None,
            "is_two_factor_enabled": False,
        },
        "hashed_password": get_password_hash("admin_password"),
    }

def test_register_user_success():
    """
    Test that a new user can be registered successfully.
    """
    response = client.post(
        "/register",
        data={"username": "test@example.com", "password": "averysecurepassword"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["is_active"] is True

    # Check that the password is not stored in plain text
    assert "password" not in fake_users_db["test@example.com"]
    assert "hashed_password" in fake_users_db["test@example.com"]

def test_register_user_already_exists():
    """
    Test that registering a user with an email that already exists fails.
    """
    # First, create the user
    client.post(
        "/register",
        data={"username": "existing@example.com", "password": "averysecurepassword"},
    )
    # Then, try to create it again
    response = client.post(
        "/register",
        data={"username": "existing@example.com", "password": "anotherpassword"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Email already registered"}

def test_login_and_get_me():
    """
    Test that a user can log in and then access a protected endpoint.
    """
    # 1. Register user
    email = "login-test@example.com"
    password = "averysecurepassword"
    register_response = client.post("/register", data={"username": email, "password": password})
    assert register_response.status_code == 201

    # 2. Log in to get token
    login_response = client.post(
        "/token",
        data={"username": email, "password": password}
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 3. Use token to access protected route
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
    password = "averysecurepassword"
    client.post("/register", data={"username": email, "password": password})

    response = client.post(
        "/token",
        data={"username": email, "password": "wrongpassword"}
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
    # 1. Register a regular user
    user_email = "user@example.com"
    user_pass = "userpass"
    client.post("/register", data={"username": user_email, "password": user_pass})

    # 2. Seeded admin logs in
    admin_login_response = client.post("/token", data={"username": "admin@example.com", "password": "admin_password"})
    admin_token = admin_login_response.json()["access_token"]
    admin_auth_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. Admin deactivates the regular user
    deactivate_response = client.post(f"/users/{user_email}/deactivate", headers=admin_auth_headers)
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    # 4. The deactivated user tries to log in
    user_login_response = client.post("/token", data={"username": user_email, "password": user_pass})
    assert user_login_response.status_code == 200 # Login is still successful, token is issued
    user_token = user_login_response.json()["access_token"]

    # 5. The deactivated user tries to access a protected route
    me_response = client.get("/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_response.status_code == 401
    assert me_response.json()["detail"] == "Inactive user"

def test_non_admin_cannot_deactivate():
    # 1. Register two users
    user1_email = "user1@example.com"
    client.post("/register", data={"username": user1_email, "password": "password1"})

    user2_email = "user2@example.com"
    user2_pass = "password2"
    client.post("/register", data={"username": user2_email, "password": user2_pass})

    # 2. User 2 logs in
    user2_login_response = client.post("/token", data={"username": user2_email, "password": user2_pass})
    user2_token = user2_login_response.json()["access_token"]
    user2_auth_headers = {"Authorization": f"Bearer {user2_token}"}

    # 3. User 2 tries to deactivate User 1
    deactivate_response = client.post(f"/users/{user1_email}/deactivate", headers=user2_auth_headers)
    assert deactivate_response.status_code == 403
    assert deactivate_response.json()["detail"] == "Admin access required"


def test_admin_token_contains_billing_claims():
    login_response = client.post("/token", data={"username": "admin@example.com", "password": "admin_password"})
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["sub"] == "admin@example.com"
    assert payload["is_admin"] is True
    assert "admin" in payload["roles"]
    assert "billing:read" in payload["scopes"]


def test_regular_user_token_has_no_billing_scope():
    email = "regular@example.com"
    password = "regular-password"
    client.post("/register", data={"username": email, "password": password})

    login_response = client.post("/token", data={"username": email, "password": password})
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["sub"] == email
    assert payload["is_admin"] is False
    assert payload["roles"] == ["user"]
    assert payload["scopes"] == []
