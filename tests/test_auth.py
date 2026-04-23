"""Tests for JWT authentication endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestRegister:
    def test_register_success(self, client: TestClient):
        resp = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "Password1",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert "id" in data
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, client: TestClient, registered_user):
        resp = client.post(
            "/auth/register",
            json={
                "username": registered_user["username"],
                "email": "other@example.com",
                "password": "Password1",
            },
        )
        assert resp.status_code == 409

    def test_register_duplicate_email(self, client: TestClient, registered_user):
        resp = client.post(
            "/auth/register",
            json={
                "username": "uniqueuser99",
                "email": registered_user["email"],
                "password": "Password1",
            },
        )
        assert resp.status_code == 409

    def test_register_weak_password(self, client: TestClient):
        resp = client.post(
            "/auth/register",
            json={
                "username": "weakpwduser",
                "email": "weakpwd@example.com",
                "password": "onlyletters",
            },
        )
        assert resp.status_code == 422

    def test_register_invalid_username_chars(self, client: TestClient):
        resp = client.post(
            "/auth/register",
            json={
                "username": "bad user!",
                "email": "bad@example.com",
                "password": "Password1",
            },
        )
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient, registered_user):
        resp = client.post(
            "/auth/login",
            json={"username": registered_user["username"], "password": registered_user["password"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, registered_user):
        resp = client.post(
            "/auth/login",
            json={"username": registered_user["username"], "password": "WrongPassword9"},
        )
        assert resp.status_code == 401

    def test_login_unknown_user(self, client: TestClient):
        resp = client.post(
            "/auth/login",
            json={"username": "nobody", "password": "Password1"},
        )
        assert resp.status_code == 401


class TestProtectedEndpoints:
    def test_me_authenticated(self, client: TestClient, auth_headers, registered_user):
        resp = client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == registered_user["username"]

    def test_me_unauthenticated(self, client: TestClient):
        resp = client.get("/auth/me")
        assert resp.status_code == 403

    def test_me_invalid_token(self, client: TestClient):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


class TestRefreshToken:
    def test_refresh_success(self, client: TestClient, registered_user):
        login = client.post(
            "/auth/login",
            json={"username": registered_user["username"], "password": registered_user["password"]},
        )
        refresh_token = login.json()["refresh_token"]

        resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_invalid_token(self, client: TestClient):
        resp = client.post("/auth/refresh", json={"refresh_token": "bad.token"})
        assert resp.status_code == 401


class TestLogout:
    def test_logout(self, client: TestClient, registered_user):
        login = client.post(
            "/auth/login",
            json={"username": registered_user["username"], "password": registered_user["password"]},
        )
        tokens = login.json()
        resp = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
        assert resp.status_code == 204

        # Revoked token should no longer work
        resp2 = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert resp2.status_code == 401

    def test_logout_all(self, client: TestClient, registered_user):
        # Use a fresh login so we don't revoke the shared session auth_headers token
        login = client.post(
            "/auth/login",
            json={"username": registered_user["username"], "password": registered_user["password"]},
        )
        tokens = login.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        resp = client.post("/auth/logout-all", headers=headers)
        assert resp.status_code == 204
