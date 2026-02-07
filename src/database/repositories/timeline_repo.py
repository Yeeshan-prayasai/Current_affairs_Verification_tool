from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from src.database.models import ThemeTimeline


class TimelineRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_timeline_by_theme_id(self, theme_id: UUID) -> Optional[ThemeTimeline]:
        """Get timeline for a specific theme."""
        return (
            self.db.query(ThemeTimeline)
            .filter(ThemeTimeline.theme_id == theme_id)
            .first()
        )
