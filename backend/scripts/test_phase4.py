"""
scripts/test_phase4.py
----------------------
Verification suite for Phase 4:
1. Verifies Clerk JWT verification error handling (invalid token, empty token, missing kid -> HTTP 401).
2. Verifies FastAPI get_current_user dependency handles missing/malformed auth headers with 401.
3. Verifies GitHub OAuth state generation and CSRF verification.
4. Verifies tampered OAuth state is rejected with HTTP 400.
5. Verifies FastAPI routes registration and unauthorized protection via TestClient.
"""

import os
import sys
from urllib.parse import parse_qs, urlparse

# Ensure UTF-8 output on Windows consoles
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt

from app.auth.clerk import verify_clerk_token
from app.auth.github_oauth import generate_github_auth_url, verify_state
from app.core.config import settings
from app.main import app


def test_clerk_invalid_tokens():
    print("\n[1] Testing verify_clerk_token with invalid tokens...")

    # Test empty token
    try:
        verify_clerk_token("")
        assert False, "Empty token should have raised HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 401, f"Expected 401, got {exc.status_code}"
        print(f"  [PASS] Empty token correctly rejected with 401: {exc.detail}")

    # Test malformed garbage string
    try:
        verify_clerk_token("not.a.valid.jwt.token")
        assert False, "Garbage token should have raised HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 401, f"Expected 401, got {exc.status_code}"
        print(f"  [PASS] Garbage token correctly rejected with 401: {exc.detail}")

    # Test JWT missing kid
    fake_jwt = jwt.encode({"sub": "user_test123"}, "secret", algorithm="HS256")
    try:
        verify_clerk_token(fake_jwt)
        assert False, "Token without kid should have raised HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 401, f"Expected 401, got {exc.status_code}"
        print(f"  [PASS] Missing kid token correctly rejected with 401: {exc.detail}")


def test_github_oauth_state_roundtrip():
    print("\n[2] Testing GitHub OAuth state generation & CSRF verification...")
    test_user_id = "user_clerk_987654321"

    # Set mock settings if not present
    if not settings.TOKEN_ENCRYPTION_KEY:
        settings.TOKEN_ENCRYPTION_KEY = "test_signing_key_for_phase4_verification_12345"
    if not settings.GITHUB_OAUTH_CLIENT_ID:
        settings.GITHUB_OAUTH_CLIENT_ID = "mock_client_id"
    if not settings.GITHUB_OAUTH_CLIENT_SECRET:
        settings.GITHUB_OAUTH_CLIENT_SECRET = "mock_client_secret"
    if not settings.GITHUB_OAUTH_REDIRECT_URI:
        settings.GITHUB_OAUTH_REDIRECT_URI = "http://localhost:3000/github/callback"

    auth_url = generate_github_auth_url(test_user_id)
    print(f"  Generated Auth URL: {auth_url[:60]}...")
    assert "github.com/login/oauth/authorize" in auth_url
    assert f"client_id={settings.GITHUB_OAUTH_CLIENT_ID}" in auth_url

    # Extract state parameter from URL
    parsed = urlparse(auth_url)
    qs = parse_qs(parsed.query)
    state = qs["state"][0]

    # Verify state round-trip
    verified_user_id = verify_state(state)
    assert verified_user_id == test_user_id, f"Expected {test_user_id}, got {verified_user_id}"
    print(f"  [PASS] State verified successfully for user: {verified_user_id}")

    # Verify tampered state fails
    tampered_state = state[:-4] + "abcd"
    try:
        verify_state(tampered_state)
        assert False, "Tampered state should have raised HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400, f"Expected 400, got {exc.status_code}"
        print(f"  [PASS] Tampered state correctly rejected with 400: {exc.detail}")


def test_routes_with_testclient():
    print("\n[3] Testing GitHub auth route registration and 401 protections via TestClient...")
    client = TestClient(app)

    # 1. GET /auth/github/login without credentials must return 401
    resp_login = client.get("/auth/github/login", follow_redirects=False)
    assert resp_login.status_code == 401, f"Expected 401 on /login, got {resp_login.status_code}"
    print(f"  [PASS] GET /auth/github/login protected: HTTP {resp_login.status_code}")

    # 2. GET /auth/github/status without credentials must return 401
    resp_status = client.get("/auth/github/status")
    assert resp_status.status_code == 401, f"Expected 401 on /status, got {resp_status.status_code}"
    print(f"  [PASS] GET /auth/github/status protected: HTTP {resp_status.status_code}")

    # 3. POST /auth/github/disconnect without credentials must return 401
    resp_disconnect = client.post("/auth/github/disconnect")
    assert resp_disconnect.status_code == 401, f"Expected 401 on /disconnect, got {resp_disconnect.status_code}"
    print(f"  [PASS] POST /auth/github/disconnect protected: HTTP {resp_disconnect.status_code}")

    # 4. GET /auth/github/callback with invalid state must return 400 (NOT 401, demonstrating it does NOT require get_current_user)
    resp_callback = client.get("/auth/github/callback?code=mock_code&state=invalid_state")
    assert resp_callback.status_code == 400, f"Expected 400 on /callback with invalid state, got {resp_callback.status_code}"
    print(f"  [PASS] GET /auth/github/callback accessible without user auth: HTTP {resp_callback.status_code} ({resp_callback.json().get('detail')})")


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 4 VERIFICATION TEST SUITE")
    print("=" * 60)
    test_clerk_invalid_tokens()
    test_github_oauth_state_roundtrip()
    test_routes_with_testclient()
    print("\n" + "=" * 60)
    print("ALL PHASE 4 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)
