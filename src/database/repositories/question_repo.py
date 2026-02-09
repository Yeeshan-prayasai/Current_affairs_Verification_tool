from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from src.database.models import ArticleGeneratedQuestion, NewsArticle, NewsTheme


class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_questions_for_article(self, current_affair_id: UUID) -> List[dict]:
        """Get all questions linked to an article."""
        questions = (
            self.db.query(ArticleGeneratedQuestion)
            .filter(ArticleGeneratedQuestion.current_affair_id == current_affair_id)
            .order_by(ArticleGeneratedQuestion.type, ArticleGeneratedQuestion.question_number)
            .all()
        )

        return [
            {
                "question_id": q.question_id,
                "paper": q.paper,
                "subject": q.subject,
                "max_score": q.max_score,
                "word_count": q.word_count,
                "year": q.year,
                "topics": q.topics,
                "sub_topics": q.sub_topics,
                "section": q.section,
                "hints": q.hints,
                "question": q.question,
                "model_answer": q.model_answer,
                "question_number": q.question_number,
                "iteration": q.iteration,
                "explanation": q.explanation,
                "difficulty": q.difficulty,
                "correct_option": q.correct_option,
                "correct_value": q.correct_value,
                "options": q.options,
                "status": q.status,
                "duration": q.duration,
                "secondary_tag": q.secondary_tag,
                "type": q.type,
            }
            for q in questions
        ]

    def get_question_by_id(self, question_id: UUID) -> Optional[ArticleGeneratedQuestion]:
        """Get a single question by ID."""
        return (
            self.db.query(ArticleGeneratedQuestion)
            .filter(ArticleGeneratedQuestion.question_id == question_id)
            .first()
        )

    def get_questions_by_date(self, target_date=None, question_type: Optional[str] = None, theme_id: Optional[UUID] = None) -> List[dict]:
        """Get questions with optional date, type, and theme filters."""
        from sqlalchemy import or_, cast, Date as SADate
        query = (
            self.db.query(ArticleGeneratedQuestion, NewsArticle.title.label("heading"), NewsTheme.name.label("theme_name"))
            .outerjoin(NewsArticle, NewsArticle.id == ArticleGeneratedQuestion.current_affair_id)
            .outerjoin(NewsTheme, NewsTheme.id == NewsArticle.news_theme_id)
        )

        if target_date:
            query = query.filter(
                or_(
                    NewsArticle.date == target_date,
                    cast(ArticleGeneratedQuestion.created_at, SADate) == target_date,
                )
            )

        if question_type:
            query = query.filter(ArticleGeneratedQuestion.type == question_type)

        if theme_id:
            query = query.filter(NewsArticle.news_theme_id == theme_id)

        query = query.order_by(ArticleGeneratedQuestion.type, ArticleGeneratedQuestion.question_number)
        results = query.all()

        return [
            {
                "question_id": q.question_id,
                "current_affair_id": q.current_affair_id,
                "article_heading": heading,
                "theme_name": theme_name,
                "paper": q.paper,
                "subject": q.subject,
                "max_score": q.max_score,
                "word_count": q.word_count,
                "year": q.year,
                "topics": q.topics,
                "sub_topics": q.sub_topics,
                "section": q.section,
                "hints": q.hints,
                "question": q.question,
                "model_answer": q.model_answer,
                "question_number": q.question_number,
                "iteration": q.iteration,
                "explanation": q.explanation,
                "difficulty": q.difficulty,
                "correct_option": q.correct_option,
                "correct_value": q.correct_value,
                "options": q.options,
                "status": q.status,
                "duration": q.duration,
                "secondary_tag": q.secondary_tag,
                "type": q.type,
            }
            for q, heading, theme_name in results
        ]

    def update_question(self, question_id: UUID, updates: dict) -> Optional[ArticleGeneratedQuestion]:
        """Update a question's fields."""
        question = self.get_question_by_id(question_id)
        if question:
            for key, value in updates.items():
                if hasattr(question, key):
                    setattr(question, key, value)
            self.db.flush()
        return question
