from typing import Optional, Dict, Any
from uuid import UUID

from src.database.connection import get_db
from src.database.repositories.theme_repo import ThemeRepository
from src.database.repositories.article_repo import ArticleRepository
from src.database.repositories.glossary_repo import GlossaryRepository
from src.database.repositories.question_repo import QuestionRepository


class ContentService:
    """Service for managing content editing operations."""

    # Theme Operations
    def update_theme_name(self, theme_id: UUID, new_name: str) -> dict:
        """Update theme name."""
        with get_db() as db:
            theme_repo = ThemeRepository(db)
            theme = theme_repo.update_theme_name(theme_id, new_name)
            if theme:
                return {"success": True, "name": new_name}
            return {"success": False, "error": "Theme not found"}

    def merge_themes(self, source_theme_id: UUID, target_theme_id: UUID) -> dict:
        """Merge two themes, moving all articles to target."""
        with get_db() as db:
            theme_repo = ThemeRepository(db)

            source = theme_repo.get_theme_with_articles(source_theme_id)
            if not source:
                return {"success": False, "error": "Source theme not found"}

            article_count = len(source["articles"])
            theme_repo.merge_themes(source_theme_id, target_theme_id)

            return {
                "success": True,
                "articles_moved": article_count,
                "target_theme_id": str(target_theme_id),
            }

    # Article Operations
    def update_article(self, article_id: int, updates: Dict[str, Any]) -> dict:
        """Update article content."""
        with get_db() as db:
            article_repo = ArticleRepository(db)
            article = article_repo.update_article(article_id, updates)
            if article:
                return {"success": True, "article_id": article_id}
            return {"success": False, "error": "Article not found"}

    # Keyword Operations
    def add_keyword_to_article(self, article_uuid: UUID, keyword_id: UUID) -> dict:
        """Add an existing keyword to an article."""
        with get_db() as db:
            glossary_repo = GlossaryRepository(db)
            glossary_repo.add_keyword_to_article(article_uuid, keyword_id)
            return {"success": True}

    def remove_keyword_from_article(
        self, article_uuid: UUID, keyword_id: UUID
    ) -> dict:
        """Remove a keyword from an article."""
        with get_db() as db:
            glossary_repo = GlossaryRepository(db)
            removed = glossary_repo.remove_keyword_from_article(article_uuid, keyword_id)
            return {"success": removed}

    # Definition Operations
    def update_definition(self, keyword_id: UUID, new_definition: str) -> dict:
        """Update a glossary definition."""
        with get_db() as db:
            glossary_repo = GlossaryRepository(db)

            keyword = glossary_repo.get_keyword_by_id(keyword_id)
            if not keyword:
                return {"success": False, "error": "Keyword not found"}

            glossary_repo.update_definition(keyword_id, new_definition)

            return {
                "success": True,
                "keyword_id": str(keyword_id),
                "word_count": len(new_definition.split()),
            }

    def update_keyword(
        self, keyword_id: UUID, new_keyword: str, new_definition: str
    ) -> dict:
        """Update keyword name and definition."""
        with get_db() as db:
            glossary_repo = GlossaryRepository(db)

            keyword = glossary_repo.get_keyword_by_id(keyword_id)
            if not keyword:
                return {"success": False, "error": "Keyword not found"}

            glossary_repo.update_keyword(keyword_id, new_keyword, new_definition)

            return {
                "success": True,
                "keyword_id": str(keyword_id),
            }

    # Question Operations
    def update_question(self, question_id: UUID, updates: Dict[str, Any]) -> dict:
        """Update a question's fields."""
        with get_db() as db:
            question_repo = QuestionRepository(db)
            question = question_repo.update_question(question_id, updates)
            if question:
                return {"success": True, "question_id": str(question_id)}
            return {"success": False, "error": "Question not found"}

    # Dashboard Stats
    def get_stats(self) -> dict:
        """Get content statistics for dashboard."""
        with get_db() as db:
            theme_repo = ThemeRepository(db)
            article_repo = ArticleRepository(db)
            glossary_repo = GlossaryRepository(db)

            return {
                "themes": theme_repo.get_theme_count(),
                "articles": article_repo.get_article_count(),
                "definitions": glossary_repo.get_keyword_count(),
            }
