import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SeriesRating(Base):
    """Puntuación que un usuario da a una serie: 1-5 estrellas enteras."""

    __tablename__ = "series_ratings"
    __table_args__ = (CheckConstraint("score BETWEEN 1 AND 5", name="ck_series_ratings_score"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    series_tmdb_id: Mapped[int] = mapped_column(
        ForeignKey("series.tmdb_id", ondelete="CASCADE"), primary_key=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
