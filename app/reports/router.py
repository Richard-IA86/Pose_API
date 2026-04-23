from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.router import get_current_user
from app.database import get_db
from app.reports.excel import build_sessions_report

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/sessions/excel", summary="Download pose sessions as Excel file")
def download_sessions_excel(
    user_id: int | None = Query(default=None, description="Filter by user ID (superuser only)"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate and download an Excel report (.xlsx) of POSE sessions.

    - Regular users can only download their own sessions. Providing `user_id` is not allowed.
    - Superusers may pass `user_id` to filter for a specific user, or omit it to get all sessions.
    """
    if not current_user.is_superuser:
        if user_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can filter reports by user_id",
            )
        target_user_id = current_user.id
    else:
        target_user_id = user_id  # None => all users

    xlsx_bytes = build_sessions_report(db, user_id=target_user_id)

    filename = f"pose_sessions_user{target_user_id or 'all'}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
