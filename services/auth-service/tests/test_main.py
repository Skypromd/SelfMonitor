from fastapi.testclient import TestClient
# We need to adjust the path to import the app from the parent directory
import sys
import os
os.environ["AUTH_SECRET_KEY"] = "test-secret"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import app, get_user_record, reset_auth_db_for_tests, set_user_admin_for_tests

client = TestClient(app)

def setup_function():
    reset_auth_db_for_tests()

def test_register_user_success():
    """
    Test that a new user can be registered successfully.
    """
    response = client.post(
        "/register",
        json={"email": "test@example.com", "password": "averysecurepassword"},
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
    assert user_record["hashed_password"] != "averysecurepassword"

def test_register_user_already_exists():
    """
    Test that registering a user with an email that already exists fails.
    """
    # First, create the user
    client.post(
        "/register",
        json={"email": "existing@example.com", "password": "averysecurepassword"},
    )
    # Then, try to create it again
    response = client.post(
        "/register",
        json={"email": "existing@example.com", "password": "anotherpassword"},
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
    register_response = client.post("/register", json={"email": email, "password": password})
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
    client.post("/register", json={"email": email, "password": password})

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
    # 1. Register an admin and a regular user
    admin_email = "admin@example.com"
    admin_pass = "adminpass"
    client.post("/register", json={"email": admin_email, "password": admin_pass})
    set_user_admin_for_tests(admin_email, True)

    user_email = "user@example.com"
    user_pass = "userpass"
    client.post("/register", json={"email": user_email, "password": user_pass})

    # 2. Admin logs in
    admin_login_response = client.post("/token", data={"username": admin_email, "password": admin_pass})
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
    client.post("/register", json={"email": user1_email, "password": "password1"})

    user2_email = "user2@example.com"
    user2_pass = "password2"
    client.post("/register", json={"email": user2_email, "password": user2_pass})

    # 2. User 2 logs in
    user2_login_response = client.post("/token", data={"username": user2_email, "password": user2_pass})
    user2_token = user2_login_response.json()["access_token"]
    user2_auth_headers = {"Authorization": f"Bearer {user2_token}"}

    # 3. User 2 tries to deactivate User 1 (who is the admin in this test's context)
    deactivate_response = client.post(f"/users/{user1_email}/deactivate", headers=user2_auth_headers)
    assert deactivate_response.status_code == 403
    assert deactivate_response.json()["detail"] == "Admin access required"
