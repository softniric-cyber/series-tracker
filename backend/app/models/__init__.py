"""Modelos SQLAlchemy. Importar desde aquí para que Alembic los descubra."""

from app.models.episode import Episode
from app.models.series import Series
from app.models.series_rating import SeriesRating
from app.models.user import User
from app.models.user_series import UserSeries
from app.models.watched_episode import WatchedEpisode

__all__ = ["User", "Series", "Episode", "UserSeries", "WatchedEpisode", "SeriesRating"]
