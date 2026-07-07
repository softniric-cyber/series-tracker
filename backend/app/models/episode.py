from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Episode(Base):
    """Caché local de TMDB. Aplana la temporada en season_number."""

    __tablename__ = "episodes"
    __table_args__ = (UniqueConstraint("series_tmdb_id", "season_number", "episode_number"),)

    tmdb_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    series_tmdb_id: Mapped[int] = mapped_column(
        ForeignKey("series.tmdb_id", ondelete="CASCADE"), nullable=False, index=True
    )
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    air_date: Mapped[date | None] = mapped_column(Date, nullable=True)
