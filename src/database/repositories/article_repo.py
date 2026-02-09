from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date as SQLDate

from src.database.models import NewsArticle, NewsTheme, ArticleKeyword, Glossary


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
            NewsArticle,
            NewsTheme.name.label("theme_name"),
        ).outerjoin(NewsTheme, NewsArticle.news_theme_id == NewsTheme.id)

        if theme_id:
            query = query.filter(NewsArticle.news_theme_id == theme_id)

        if start_date:
            query = query.filter(NewsArticle.date >= start_date)
        if end_date:
            query = query.filter(NewsArticle.date <= end_date)

        if search:
            query = query.filter(NewsArticle.title.ilike(f"%{search}%"))

        results = (
            query.order_by(NewsArticle.date.desc()).offset(offset).limit(limit).all()
        )

        return [
            {
                "id": r.NewsArticle.id,
                "heading": r.NewsArticle.title,
                "description": r.NewsArticle.description,
                "date": r.NewsArticle.date,
                "theme_id": r.NewsArticle.news_theme_id,
                "theme_name": r.theme_name,
                "source": r.NewsArticle.source,
            }
            for r in results
        ]

    def get_article_by_id(self, article_id: UUID) -> Optional[NewsArticle]:
        """Get a single article by UUID."""
        return (
            self.db.query(NewsArticle).filter(NewsArticle.id == article_id).first()
        )

    def get_article_with_keywords(self, article_uuid: UUID) -> Optional[dict]:
        """Get article with its associated keywords."""
        article = (
            self.db.query(NewsArticle)
            .filter(NewsArticle.id == article_uuid)
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
        self, article_id: UUID, updates: Dict[str, Any]
    ) -> Optional[NewsArticle]:
        """Update article fields."""
        article = (
            self.db.query(NewsArticle).filter(NewsArticle.id == article_id).first()
        )
        if not article:
            return None

        # Map old field names to new column names
        field_mapping = {
            "heading": "title",
            "pointed_analysis": "text",
            "mains_analysis": "mains_info",
            "prelims_info": "prelims_info",
            "description": "description",
            "theme_id": "news_theme_id",
            # Direct new field names also accepted
            "title": "title",
            "text": "text",
            "mains_info": "mains_info",
            "news_theme_id": "news_theme_id",
        }

        for field, value in updates.items():
            mapped_field = field_mapping.get(field, field)
            if hasattr(article, mapped_field):
                setattr(article, mapped_field, value)

        self.db.flush()
        return article

    def reassign_theme(
        self, article_id: UUID, new_theme_id: UUID
    ) -> Optional[NewsArticle]:
        """Reassign an article to a different theme."""
        article = (
            self.db.query(NewsArticle).filter(NewsArticle.id == article_id).first()
        )
        if article:
            article.news_theme_id = new_theme_id
            self.db.flush()
        return article

    def get_article_count(
        self,
        theme_id: Optional[UUID] = None,
        search: Optional[str] = None,
    ) -> int:
        """Get total count of articles."""
        query = self.db.query(func.count(NewsArticle.id))

        if theme_id:
            query = query.filter(NewsArticle.news_theme_id == theme_id)

        if search:
            query = query.filter(NewsArticle.title.ilike(f"%{search}%"))

        return query.scalar() or 0

    def get_articles_by_theme(self, theme_id: UUID) -> List[NewsArticle]:
        """Get all articles for a specific theme."""
        return (
            self.db.query(NewsArticle)
            .filter(NewsArticle.news_theme_id == theme_id)
            .order_by(NewsArticle.date.desc())
            .all()
        )
