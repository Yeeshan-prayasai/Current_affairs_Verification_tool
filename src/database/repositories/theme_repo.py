from typing import List, Optional
from uuid import UUID
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date as SQLDate

from src.database.models import Theme, CurrentAffair


class ThemeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_themes(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """Get all themes with article counts."""
        query = (
            self.db.query(
                Theme.id,
                Theme.name,
                Theme.created_at,
                func.count(CurrentAffair.id).label("article_count"),
            )
            .outerjoin(CurrentAffair, CurrentAffair.theme_id == Theme.id)
            .group_by(Theme.id)
        )

        if search:
            query = query.filter(Theme.name.ilike(f"%{search}%"))

        results = (
            query.order_by(Theme.created_at.desc()).offset(offset).limit(limit).all()
        )

        return [
            {
                "id": r.id,
                "name": r.name,
                "created_at": r.created_at,
                "article_count": r.article_count,
            }
            for r in results
        ]

    def get_themes_by_article_date(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """Get themes that have articles within a date range."""
        # Subquery to get theme IDs that have articles in the date range
        article_query = self.db.query(CurrentAffair.theme_id).filter(
            CurrentAffair.theme_id.isnot(None)
        )

        if start_date:
            article_query = article_query.filter(
                cast(CurrentAffair.date, SQLDate) >= start_date
            )
        if end_date:
            article_query = article_query.filter(
                cast(CurrentAffair.date, SQLDate) <= end_date
            )

        theme_ids_with_articles = article_query.distinct().subquery()

        # Main query
        query = (
            self.db.query(
                Theme.id,
                Theme.name,
                Theme.created_at,
                func.count(CurrentAffair.id).label("article_count"),
            )
            .join(theme_ids_with_articles, Theme.id == theme_ids_with_articles.c.theme_id)
            .outerjoin(CurrentAffair, CurrentAffair.theme_id == Theme.id)
        )

        # Filter articles by date for accurate count
        if start_date:
            query = query.filter(cast(CurrentAffair.date, SQLDate) >= start_date)
        if end_date:
            query = query.filter(cast(CurrentAffair.date, SQLDate) <= end_date)

        query = query.group_by(Theme.id)

        if search:
            query = query.filter(Theme.name.ilike(f"%{search}%"))

        results = (
            query.order_by(func.count(CurrentAffair.id).desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [
            {
                "id": r.id,
                "name": r.name,
                "created_at": r.created_at,
                "article_count": r.article_count,
            }
            for r in results
        ]

    def get_theme_by_id(self, theme_id: UUID) -> Optional[Theme]:
        """Get a single theme by ID."""
        return self.db.query(Theme).filter(Theme.id == theme_id).first()

    def get_theme_with_articles(self, theme_id: UUID) -> Optional[dict]:
        """Get theme details with all associated articles."""
        theme = self.db.query(Theme).filter(Theme.id == theme_id).first()
        if not theme:
            return None

        articles = (
            self.db.query(CurrentAffair)
            .filter(CurrentAffair.theme_id == theme_id)
            .order_by(CurrentAffair.date.desc())
            .all()
        )

        return {"theme": theme, "articles": articles}

    def update_theme_name(self, theme_id: UUID, new_name: str) -> Optional[Theme]:
        """Update theme name."""
        theme = self.db.query(Theme).filter(Theme.id == theme_id).first()
        if theme:
            theme.name = new_name
            self.db.flush()
        return theme

    def merge_themes(self, source_id: UUID, target_id: UUID) -> int:
        """Merge source theme into target, reassigning all articles."""
        updated = (
            self.db.query(CurrentAffair)
            .filter(CurrentAffair.theme_id == source_id)
            .update({"theme_id": target_id})
        )

        # Delete source theme
        self.db.query(Theme).filter(Theme.id == source_id).delete()

        return updated

    def find_similar_themes(
        self, theme_name: str, exclude_id: UUID = None, limit: int = 5
    ) -> List[Theme]:
        """Find potentially similar themes for merge suggestions."""
        words = theme_name.split()
        if not words:
            return []

        query = self.db.query(Theme).filter(Theme.name.ilike(f"%{words[0]}%"))

        if exclude_id:
            query = query.filter(Theme.id != exclude_id)

        return query.limit(limit).all()

    def get_theme_count(self, search: Optional[str] = None) -> int:
        """Get total count of themes."""
        query = self.db.query(func.count(Theme.id))
        if search:
            query = query.filter(Theme.name.ilike(f"%{search}%"))
        return query.scalar() or 0

    def get_theme_count_by_article_date(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
    ) -> int:
        """Get count of themes that have articles within a date range."""
        query = (
            self.db.query(func.count(func.distinct(CurrentAffair.theme_id)))
            .filter(CurrentAffair.theme_id.isnot(None))
        )

        if start_date:
            query = query.filter(cast(CurrentAffair.date, SQLDate) >= start_date)
        if end_date:
            query = query.filter(cast(CurrentAffair.date, SQLDate) <= end_date)
        if search:
            query = query.join(Theme, Theme.id == CurrentAffair.theme_id).filter(
                Theme.name.ilike(f"%{search}%")
            )

        return query.scalar() or 0
