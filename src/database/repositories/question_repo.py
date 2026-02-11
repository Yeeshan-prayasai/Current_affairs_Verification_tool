from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from src.database.models import MCQ, ItemRelation, NewsArticle, NewsTheme, LearningItem


class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_questions_for_article(self, learning_item_id: UUID) -> List[dict]:
        """Get all MCQs linked to an article via item_relations.

        Join path: news_articles.learningItemId = item_relations.sourceItemId
                   item_relations.targetItemId = mcqs.learningItemId
        """
        questions = (
            self.db.query(MCQ)
            .join(ItemRelation, ItemRelation.target_item_id == MCQ.learning_item_id)
            .filter(ItemRelation.source_item_id == learning_item_id)
            .order_by(MCQ.question_pattern, MCQ.created_at)
            .all()
        )

        return [
            {
                "question_id": q.id,
                "question_text": q.question_text,
                "options": q.options,
                "correct_option_ids": q.correct_option_ids,
                "is_multi_select": q.is_multi_select,
                "learning_item_id": q.learning_item_id,
                "explanation": q.explanation,
                "silly_mistake_prone": q.silly_mistake_prone,
                "question_pattern": q.question_pattern,
                "created_at": q.created_at,
            }
            for q in questions
        ]

    def get_question_by_id(self, question_id: UUID) -> Optional[MCQ]:
        """Get a single MCQ by ID."""
        return (
            self.db.query(MCQ)
            .filter(MCQ.id == question_id)
            .first()
        )

    def get_questions_by_date(self, target_date=None, question_type: Optional[str] = None, theme_id: Optional[UUID] = None) -> List[dict]:
        """Get MCQs with optional date, type, and theme filters.

        Join path: mcqs -> item_relations -> news_articles -> news_themes
        """
        from sqlalchemy import cast, Date as SADate
        query = (
            self.db.query(MCQ, NewsArticle.title.label("heading"), NewsTheme.name.label("theme_name"))
            .join(ItemRelation, ItemRelation.target_item_id == MCQ.learning_item_id)
            .join(NewsArticle, NewsArticle.learning_item_id == ItemRelation.source_item_id)
            .outerjoin(NewsTheme, NewsTheme.id == NewsArticle.news_theme_id)
        )

        if target_date:
            query = query.filter(NewsArticle.date == target_date)

        if question_type:
            query = query.filter(MCQ.question_pattern == question_type)

        if theme_id:
            query = query.filter(NewsArticle.news_theme_id == theme_id)

        query = query.order_by(MCQ.question_pattern, MCQ.created_at)
        results = query.all()

        return [
            {
                "question_id": q.id,
                "article_heading": heading,
                "theme_name": theme_name,
                "question_text": q.question_text,
                "options": q.options,
                "correct_option_ids": q.correct_option_ids,
                "is_multi_select": q.is_multi_select,
                "learning_item_id": q.learning_item_id,
                "explanation": q.explanation,
                "silly_mistake_prone": q.silly_mistake_prone,
                "question_pattern": q.question_pattern,
                "created_at": q.created_at,
            }
            for q, heading, theme_name in results
        ]

    def update_question(self, question_id: UUID, updates: dict) -> Optional[MCQ]:
        """Update an MCQ's fields."""
        question = self.get_question_by_id(question_id)
        if question:
            for key, value in updates.items():
                if hasattr(question, key):
                    setattr(question, key, value)
            self.db.flush()
        return question

    def save_daily_selected(self, mcq_ids: List[UUID]) -> int:
        """Mark 10 selected MCQs as 'daily-selected' and reset any previous daily selections.

        Only touches learning_items with purpose = 'article-generated-questions'
        or purpose = 'daily-selected'. Never touches NULL purpose rows.
        """
        # Get learning_item_ids for the selected MCQs
        selected_li_ids = (
            self.db.query(MCQ.learning_item_id)
            .filter(MCQ.id.in_(mcq_ids))
            .all()
        )
        selected_li_ids = [row[0] for row in selected_li_ids]

        # Reset all current 'daily-selected' back to 'article-generated-questions'
        self.db.query(LearningItem).filter(
            LearningItem.purpose == "daily-selected"
        ).update(
            {"purpose": "article-generated-questions"},
            synchronize_session="fetch",
        )

        # Mark the selected ones as 'daily-selected'
        if selected_li_ids:
            self.db.query(LearningItem).filter(
                LearningItem.id.in_(selected_li_ids),
                LearningItem.purpose == "article-generated-questions",
            ).update(
                {"purpose": "daily-selected"},
                synchronize_session="fetch",
            )

        return len(selected_li_ids)

    def get_daily_selected_ids(self) -> set:
        """Get MCQ IDs that are currently marked as daily-selected."""
        results = (
            self.db.query(MCQ.id)
            .join(LearningItem, LearningItem.id == MCQ.learning_item_id)
            .filter(LearningItem.purpose == "daily-selected")
            .all()
        )
        return {str(row[0]) for row in results}
