from datetime import datetime

from pydantic import BaseModel, Field


class ETLJobStatus(BaseModel):
    job_id: str
    status: str
    message: str
    triggered_at: datetime
    triggered_by: str


class ETLTriggerRequest(BaseModel):
    pipeline: str = Field(
        ...,
        description="Name of the ETL pipeline to run",
        examples=["pose_sessions_to_dw", "keypoints_aggregation", "user_activity_summary"],
    )
    parameters: dict = Field(
        default_factory=dict,
        description="Optional key/value parameters forwarded to the ETL pipeline",
    )
    async_run: bool = Field(
        default=True,
        description="When True the job is submitted asynchronously; False waits for completion",
    )


class ETLPipelineInfo(BaseModel):
    name: str
    description: str
    schedule: str | None = None


class ETLPipelineListResponse(BaseModel):
    pipelines: list[ETLPipelineInfo]
