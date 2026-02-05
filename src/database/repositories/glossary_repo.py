from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database.models import Glossary, ArticleKeyword, CurrentAffair


class GlossaryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_keywords(
        self,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """Get all glossary keywords."""
        query = (
            self.db.query(
                Glossary.id,
                Glossary.keyword,
                Glossary.definition,
                Glossary.created_at,
                func.count(ArticleKeyword.article_id).label("article_count"),
            )
            .outerjoin(ArticleKeyword, ArticleKeyword.keyword_id == Glossary.id)
            .group_by(Glossary.id)
        )

        if search:
            query = query.filter(Glossary.keyword.ilike(f"%{search}%"))

        results = (
            query.order_by(Glossary.created_at.desc()).offset(offset).limit(limit).all()
        )

        return [
            {
                "id": r.id,
                "keyword": r.keyword,
                "definition": r.definition,
                "created_at": r.created_at,
                "article_count": r.article_count,
            }
            for r in results
        ]

    def get_keyword_by_id(self, keyword_id: UUID) -> Optional[Glossary]:
        """Get a single keyword by ID."""
        return self.db.query(Glossary).filter(Glossary.id == keyword_id).first()

    def get_keyword_with_articles(self, keyword_id: UUID) -> Optional[dict]:
        """Get keyword with all articles using it."""
        keyword = self.db.query(Glossary).filter(Glossary.id == keyword_id).first()
        if not keyword:
            return None

        articles = (
            self.db.query(CurrentAffair)
            .join(
                ArticleKeyword,
                ArticleKeyword.article_id == CurrentAffair.current_affair_id,
            )
            .filter(ArticleKeyword.keyword_id == keyword_id)
            .order_by(CurrentAffair.date.desc())
            .all()
        )

        return {"keyword": keyword, "articles": articles}

    def update_definition(
        self, keyword_id: UUID, new_definition: str
    ) -> Optional[Glossary]:
        """Update keyword definition."""
        keyword = self.db.query(Glossary).filter(Glossary.id == keyword_id).first()
        if keyword:
            keyword.definition = new_definition
            self.db.flush()
        return keyword

    def update_keyword(
        self, keyword_id: UUID, new_keyword: str, new_definition: str
    ) -> Optional[Glossary]:
        """Update keyword name and definition."""
        keyword = self.db.query(Glossary).filter(Glossary.id == keyword_id).first()
        if keyword:
            keyword.keyword = new_keyword
            keyword.definition = new_definition
            self.db.flush()
        return keyword

    def search_keywords(self, search_term: str, limit: int = 10) -> List[Glossary]:
        """Search keywords by name."""
        return (
            self.db.query(Glossary)
            .filter(Glossary.keyword.ilike(f"%{search_term}%"))
            .limit(limit)
            .all()
        )

    def create_keyword(
        self, keyword: str, definition: str, keyword_id: UUID
    ) -> Glossary:
        """Create a new glossary keyword."""
        new_keyword = Glossary(
            id=keyword_id,
            keyword=keyword,
            definition=definition,
        )
        self.db.add(new_keyword)
        self.db.flush()
        return new_keyword

    def get_keywords_for_article(self, article_uuid: UUID) -> List[dict]:
        """Get all keywords linked to an article."""
        results = (
            self.db.query(
                Glossary.id,
                Glossary.keyword,
                Glossary.definition,
            )
            .join(ArticleKeyword, ArticleKeyword.keyword_id == Glossary.id)
            .filter(ArticleKeyword.article_id == article_uuid)
            .all()
        )

        return [
            {
                "id": r.id,
                "keyword": r.keyword,
                "definition": r.definition,
            }
            for r in results
        ]

    def add_keyword_to_article(
        self, article_uuid: UUID, keyword_id: UUID
    ) -> ArticleKeyword:
        """Link a keyword to an article."""
        link = ArticleKeyword(article_id=article_uuid, keyword_id=keyword_id)
        self.db.add(link)
        self.db.flush()
        return link

    def remove_keyword_from_article(self, article_uuid: UUID, keyword_id: UUID) -> bool:
        """Remove keyword link from article."""
        deleted = (
            self.db.query(ArticleKeyword)
            .filter(
                ArticleKeyword.article_id == article_uuid,
                ArticleKeyword.keyword_id == keyword_id,
            )
            .delete()
        )
        return deleted > 0

    def get_keyword_count(self, search: Optional[str] = None) -> int:
        """Get total count of keywords."""
        query = self.db.query(func.count(Glossary.id))
        if search:
            query = query.filter(Glossary.keyword.ilike(f"%{search}%"))
        return query.scalar() or 0
