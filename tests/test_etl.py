"""Tests for ETL trigger endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestETLPipelines:
    def test_list_pipelines_authenticated(self, client: TestClient, auth_headers):
        resp = client.get("/etl/pipelines", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "pipelines" in data
        assert len(data["pipelines"]) > 0
        names = [p["name"] for p in data["pipelines"]]
        assert "pose_sessions_to_dw" in names

    def test_list_pipelines_unauthenticated(self, client: TestClient):
        resp = client.get("/etl/pipelines")
        assert resp.status_code == 403


class TestETLTrigger:
    def test_trigger_requires_superuser(self, client: TestClient, auth_headers):
        resp = client.post(
            "/etl/trigger",
            headers=auth_headers,
            json={"pipeline": "pose_sessions_to_dw"},
        )
        assert resp.status_code == 403

    def test_trigger_success_superuser(self, client: TestClient, superuser_headers):
        resp = client.post(
            "/etl/trigger",
            headers=superuser_headers,
            json={"pipeline": "pose_sessions_to_dw", "parameters": {"date": "2024-01-01"}},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] in ("submitted", "simulated")
        assert data["triggered_by"] == "admin"

    def test_trigger_unknown_pipeline(self, client: TestClient, superuser_headers):
        resp = client.post(
            "/etl/trigger",
            headers=superuser_headers,
            json={"pipeline": "nonexistent_pipeline"},
        )
        assert resp.status_code == 400

    def test_trigger_all_known_pipelines(self, client: TestClient, superuser_headers):
        pipelines = ["pose_sessions_to_dw", "keypoints_aggregation", "user_activity_summary", "full_etl_refresh"]
        for name in pipelines:
            resp = client.post(
                "/etl/trigger",
                headers=superuser_headers,
                json={"pipeline": name},
            )
            assert resp.status_code == 202, f"Pipeline '{name}' trigger failed: {resp.text}"
