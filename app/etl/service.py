"""ETL service client — thin HTTP wrapper around the POSE ETL service."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.etl.schemas import ETLJobStatus, ETLTriggerRequest

logger = logging.getLogger(__name__)

# Known pipelines exposed by this API
KNOWN_PIPELINES = [
    {
        "name": "pose_sessions_to_dw",
        "description": "Load raw pose sessions into the data warehouse",
        "schedule": "0 2 * * *",
    },
    {
        "name": "keypoints_aggregation",
        "description": "Aggregate keypoint metrics per user per day",
        "schedule": "0 3 * * *",
    },
    {
        "name": "user_activity_summary",
        "description": "Compute weekly user activity summaries",
        "schedule": "0 4 * * 1",
    },
    {
        "name": "full_etl_refresh",
        "description": "Full refresh: runs all pipelines in order",
        "schedule": None,
    },
]


async def trigger_pipeline(request: ETLTriggerRequest, triggered_by: str) -> ETLJobStatus:
    """
    Send a trigger request to the ETL service.

    Falls back to a simulated in-process response when the ETL service
    is unreachable (useful during development / tests).
    """
    job_id = str(uuid.uuid4())
    triggered_at = datetime.now(timezone.utc)

    if not settings.etl_base_url:
        return _simulate_job(job_id, request, triggered_at, triggered_by)

    payload = {
        "pipeline": request.pipeline,
        "parameters": request.parameters,
        "async_run": request.async_run,
        "triggered_by": triggered_by,
    }
    headers = {"X-API-Key": settings.etl_api_key, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{settings.etl_base_url}/trigger",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return ETLJobStatus(
                job_id=data.get("job_id", job_id),
                status=data.get("status", "submitted"),
                message=data.get("message", "Pipeline triggered successfully"),
                triggered_at=triggered_at,
                triggered_by=triggered_by,
            )
    except httpx.HTTPStatusError as exc:
        logger.warning("ETL service returned %s: %s", exc.response.status_code, exc.response.text)
        return ETLJobStatus(
            job_id=job_id,
            status="error",
            message=f"ETL service error: {exc.response.status_code}",
            triggered_at=triggered_at,
            triggered_by=triggered_by,
        )
    except httpx.RequestError as exc:
        logger.warning("ETL service unreachable: %s", exc)
        return _simulate_job(job_id, request, triggered_at, triggered_by)


def _simulate_job(
    job_id: str,
    request: ETLTriggerRequest,
    triggered_at: datetime,
    triggered_by: str,
) -> ETLJobStatus:
    """Return a simulated job status when the real ETL service is unavailable."""
    return ETLJobStatus(
        job_id=job_id,
        status="simulated",
        message=f"ETL service not configured — pipeline '{request.pipeline}' simulated locally",
        triggered_at=triggered_at,
        triggered_by=triggered_by,
    )
