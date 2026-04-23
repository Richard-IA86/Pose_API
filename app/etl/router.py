from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.router import get_current_superuser, get_current_user
from app.etl import schemas, service

router = APIRouter(prefix="/etl", tags=["ETL"])


@router.get("/pipelines", response_model=schemas.ETLPipelineListResponse, summary="List available ETL pipelines")
async def list_pipelines(current_user=Depends(get_current_user)):
    """Return the list of ETL pipelines available in the POSE ecosystem."""
    pipelines = [schemas.ETLPipelineInfo(**p) for p in service.KNOWN_PIPELINES]
    return schemas.ETLPipelineListResponse(pipelines=pipelines)


@router.post(
    "/trigger",
    response_model=schemas.ETLJobStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger an ETL pipeline (superuser only)",
)
async def trigger_etl(
    payload: schemas.ETLTriggerRequest,
    current_user=Depends(get_current_superuser),
):
    """
    Trigger a named ETL pipeline in the POSE ecosystem.

    Requires superuser privileges. Available pipeline names can be found
    via `GET /etl/pipelines`.
    """
    known_names = {p["name"] for p in service.KNOWN_PIPELINES}
    if payload.pipeline not in known_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown pipeline '{payload.pipeline}'. "
                   f"Available: {sorted(known_names)}",
        )

    job_status = await service.trigger_pipeline(payload, triggered_by=current_user.username)
    return job_status
