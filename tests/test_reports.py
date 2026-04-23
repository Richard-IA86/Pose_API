"""Tests for Excel report generation endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestReportsEndpoint:
    def test_download_excel_authenticated(self, client: TestClient, auth_headers):
        resp = client.get("/reports/sessions/excel", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert "attachment" in resp.headers.get("content-disposition", "")
        # Verify it is a valid xlsx (starts with PK zip magic bytes)
        assert resp.content[:2] == b"PK"

    def test_download_excel_unauthenticated(self, client: TestClient):
        resp = client.get("/reports/sessions/excel")
        assert resp.status_code == 403

    def test_regular_user_cannot_filter_other_user(self, client: TestClient, auth_headers):
        # Regular user providing user_id should receive 403
        resp = client.get("/reports/sessions/excel?user_id=999", headers=auth_headers)
        assert resp.status_code == 403

    def test_superuser_can_download_all(self, client: TestClient, superuser_headers):
        resp = client.get("/reports/sessions/excel", headers=superuser_headers)
        assert resp.status_code == 200
        assert resp.content[:2] == b"PK"

    def test_superuser_can_filter_by_user(self, client: TestClient, superuser_headers):
        resp = client.get("/reports/sessions/excel?user_id=1", headers=superuser_headers)
        assert resp.status_code == 200
