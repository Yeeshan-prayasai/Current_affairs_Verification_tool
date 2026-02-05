from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date as SQLDate

from src.database.models import CurrentAffair, Theme, ArticleKeyword, Glossary


class ArticleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_articles(
        self,
        theme_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """Get articles with optional filters."""
        query = self.db.query(
            CurrentAffair,
            Theme.name.label("theme_name"),
        ).outerjoin(Theme, CurrentAffair.theme_id == Theme.id)

        if theme_id:
            query = query.filter(CurrentAffair.theme_id == theme_id)

        # Cast DateTime to Date for proper date comparison
        if start_date:
            query = query.filter(cast(CurrentAffair.date, SQLDate) >= start_date)
        if end_date:
            query = query.filter(cast(CurrentAffair.date, SQLDate) <= end_date)

        if search:
            query = query.filter(CurrentAffair.heading.ilike(f"%{search}%"))

        results = (
            query.order_by(CurrentAffair.date.desc()).offset(offset).limit(limit).all()
        )

        return [
            {
                "id": r.CurrentAffair.id,
                "current_affair_id": r.CurrentAffair.current_affair_id,
                "heading": r.CurrentAffair.heading,
                "description": r.CurrentAffair.description,
                "date": r.CurrentAffair.date,
                "theme_id": r.CurrentAffair.theme_id,
                "theme_name": r.theme_name,
                "mains_subject": r.CurrentAffair.mains_subject,
                "prelims_subject": r.CurrentAffair.prelims_subject,
                "news_paper": r.CurrentAffair.news_paper,
            }
            for r in results
        ]

    def get_article_by_id(self, article_id: int) -> Optional[CurrentAffair]:
        """Get a single article by integer ID."""
        return (
            self.db.query(CurrentAffair).filter(CurrentAffair.id == article_id).first()
        )

    def get_article_by_uuid(self, article_uuid: UUID) -> Optional[CurrentAffair]:
        """Get a single article by UUID."""
        return (
            self.db.query(CurrentAffair)
            .filter(CurrentAffair.current_affair_id == article_uuid)
            .first()
        )

    def get_article_with_keywords(self, article_uuid: UUID) -> Optional[dict]:
        """Get article with its associated keywords."""
        article = (
            self.db.query(CurrentAffair)
            .filter(CurrentAffair.current_affair_id == article_uuid)
            .first()
        )

        if not article:
            return None

        keywords = (
            self.db.query(Glossary)
            .join(ArticleKeyword, ArticleKeyword.keyword_id == Glossary.id)
            .filter(ArticleKeyword.article_id == article_uuid)
            .all()
        )

        return {"article": article, "keywords": keywords}

    def update_article(
        self, article_id: int, updates: Dict[str, Any]
    ) -> Optional[CurrentAffair]:
        """Update article fields."""
        article = (
            self.db.query(CurrentAffair).filter(CurrentAffair.id == article_id).first()
        )
        if not article:
            return None

        allowed_fields = {
            "heading",
            "description",
            "pointed_analysis",
            "mains_analysis",
            "prelims_info",
            "mains_subject",
            "prelims_subject",
            "mains_topics",
            "prelims_topics",
            "secondary_tag",
            "sub_topics",
            "theme_id",
        }

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(article, field, value)

        self.db.flush()
        return article

    def reassign_theme(
        self, article_id: int, new_theme_id: UUID
    ) -> Optional[CurrentAffair]:
        """Reassign an article to a different theme."""
        article = (
            self.db.query(CurrentAffair).filter(CurrentAffair.id == article_id).first()
        )
        if article:
            article.theme_id = new_theme_id
            self.db.flush()
        return article

    def get_article_count(
        self,
        theme_id: Optional[UUID] = None,
        search: Optional[str] = None,
    ) -> int:
        """Get total count of articles."""
        query = self.db.query(func.count(CurrentAffair.id))

        if theme_id:
            query = query.filter(CurrentAffair.theme_id == theme_id)

        if search:
            query = query.filter(CurrentAffair.heading.ilike(f"%{search}%"))

        return query.scalar() or 0

    def get_articles_by_theme(self, theme_id: UUID) -> List[CurrentAffair]:
        """Get all articles for a specific theme."""
        return (
            self.db.query(CurrentAffair)
            .filter(CurrentAffair.theme_id == theme_id)
            .order_by(CurrentAffair.date.desc())
            .all()
        )
