from typing import List, Optional
from datetime import date
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from src.database.models import NewsTheme, NewsArticle, ArticleGeneratedQuestion


class TrendingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_themes_with_article_count(
        self,
        search: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[dict]:
        """Get news_themes with article counts, optionally filtered by article date."""
        query = (
            self.db.query(
                NewsTheme.id,
                NewsTheme.name,
                NewsTheme.summary,
                NewsTheme.is_trending,
                NewsTheme.created_at,
                func.count(NewsArticle.id).label("article_count"),
            )
            .outerjoin(NewsArticle, NewsArticle.news_theme_id == NewsTheme.id)
        )

        if start_date:
            query = query.filter(NewsArticle.date >= start_date)
        if end_date:
            query = query.filter(NewsArticle.date <= end_date)

        query = query.group_by(NewsTheme.id)

        # Only return themes that have articles in the date range
        if start_date or end_date:
            query = query.having(func.count(NewsArticle.id) > 0)

        if search:
            query = query.filter(NewsTheme.name.ilike(f"%{search}%"))

        results = query.order_by(func.count(NewsArticle.id).desc()).all()

        return [
            {
                "id": r.id,
                "name": r.name,
                "summary": r.summary,
                "is_trending": r.is_trending,
                "created_at": r.created_at,
                "article_count": r.article_count,
            }
            for r in results
        ]

    def get_currently_trending(self) -> List[dict]:
        """Get themes currently marked as trending."""
        results = (
            self.db.query(
                NewsTheme.id,
                NewsTheme.name,
                NewsTheme.summary,
                NewsTheme.is_trending,
                func.count(NewsArticle.id).label("article_count"),
            )
            .outerjoin(NewsArticle, NewsArticle.news_theme_id == NewsTheme.id)
            .filter(NewsTheme.is_trending == True)
            .group_by(NewsTheme.id)
            .all()
        )

        return [
            {
                "id": r.id,
                "name": r.name,
                "summary": r.summary,
                "is_trending": r.is_trending,
                "article_count": r.article_count,
            }
            for r in results
        ]

    def get_questions_for_theme(self, theme_id: UUID) -> List[dict]:
        """Get all questions for articles belonging to a theme."""
        results = (
            self.db.query(ArticleGeneratedQuestion, NewsArticle.title)
            .join(NewsArticle, NewsArticle.id == ArticleGeneratedQuestion.current_affair_id)
            .filter(NewsArticle.news_theme_id == theme_id)
            .order_by(ArticleGeneratedQuestion.type, ArticleGeneratedQuestion.question_number)
            .all()
        )

        return [
            {
                "question_id": q.question_id,
                "current_affair_id": q.current_affair_id,
                "article_title": title,
                "paper": q.paper,
                "subject": q.subject,
                "max_score": q.max_score,
                "word_count": q.word_count,
                "topics": q.topics,
                "question": q.question,
                "model_answer": q.model_answer,
                "explanation": q.explanation,
                "difficulty": q.difficulty,
                "correct_option": q.correct_option,
                "correct_value": q.correct_value,
                "options": q.options,
                "status": q.status,
                "type": q.type,
            }
            for q, title in results
        ]

    def save_trending_themes(self, trending_theme_ids: List[UUID]):
        """Set selected themes as trending and unset the rest."""
        # Unset all
        self.db.query(NewsTheme).filter(NewsTheme.is_trending == True).update(
            {"isTrending": False}, synchronize_session="fetch"
        )
        # Set selected
        if trending_theme_ids:
            self.db.query(NewsTheme).filter(NewsTheme.id.in_(trending_theme_ids)).update(
                {"isTrending": True}, synchronize_session="fetch"
            )
