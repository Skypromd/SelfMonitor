# Auth Service

Handles user authentication, registration, and token management.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /register | No | Register a new user |
| POST | /token | No | Login and obtain an access token |
| GET | /2fa/setup | Yes | Generate a 2FA secret and QR code |
| POST | /2fa/verify | Yes | Verify a TOTP code and enable 2FA |
| DELETE | /2fa/disable | Yes | Disable 2FA for the current user |
| GET | /me | Yes | Get the current authenticated user |
| POST | /users/{user_email}/deactivate | Yes (Admin) | Deactivate a user account |
| POST | /organizations | Yes | Create a new organization |
| GET | /enterprise/pricing | No | Get enterprise pricing plans |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AUTH_SECRET_KEY | Yes | - | JWT signing key |
| AUTH_DB_PATH | No | /tmp/auth.db | Path to the SQLite auth database |
| AUTH_ADMIN_EMAIL | No | admin@example.com | Default admin email |
| AUTH_ADMIN_PASSWORD | No | admin_password | Default admin password |
| AUTH_BOOTSTRAP_ADMIN | No | false | Seed an admin user on startup |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

```bash
pytest tests/test_main.py
```
