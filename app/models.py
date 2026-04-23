from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PoseSession(Base):
    """A single posture-analysis session for a user."""

    __tablename__ = "pose_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    session_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    keypoints: Mapped[list["PoseKeypoint"]] = relationship(
        "PoseKeypoint", back_populates="session", cascade="all, delete-orphan"
    )


class PoseKeypoint(Base):
    """Individual keypoint measurement within a pose session."""

    __tablename__ = "pose_keypoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("pose_sessions.id"), nullable=False)
    keypoint_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    z: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    session: Mapped["PoseSession"] = relationship("PoseSession", back_populates="keypoints")
