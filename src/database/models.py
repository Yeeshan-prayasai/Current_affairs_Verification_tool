from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Index,
    CheckConstraint,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


# ============================================
# CORE TABLES
# ============================================


class NewsTheme(Base):
    __tablename__ = "news_themes"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    created_at = Column("createdAt", DateTime(timezone=True), nullable=False)
    updated_at = Column("updatedAt", DateTime(timezone=True), nullable=False)
    name = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    is_trending = Column("isTrending", Boolean, nullable=False, default=False)
    thumbnail_url = Column("thumbnailUrl", Text)

    # Relationships
    articles = relationship("NewsArticle", back_populates="theme")

    def __repr__(self):
        return f"<NewsTheme(id={self.id}, name='{self.name}', trending={self.is_trending})>"


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    created_at = Column("createdAt", DateTime(timezone=True), nullable=False)
    updated_at = Column("updatedAt", DateTime(timezone=True), nullable=False)
    date = Column(Date, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    text = Column(Text, nullable=False)  # pointed_analysis equivalent
    prelims_info = Column("prelimsInfo", Text)
    learning_item_id = Column("learningItemId", PGUUID(as_uuid=True), nullable=False)
    source = Column(Text)
    time_in_minutes = Column("timeInMinutes", Integer, nullable=False)
    news_theme_id = Column("newsThemeId", PGUUID(as_uuid=True), ForeignKey("news_themes.id"))
    thumbnail_url = Column("thumbnailUrl", Text)
    mains_info = Column("mainsInfo", Text)

    # Relationships
    theme = relationship("NewsTheme", back_populates="articles")

    def __repr__(self):
        return f"<NewsArticle(id={self.id}, title='{self.title[:50] if self.title else ''}')>"


class Glossary(Base):
    __tablename__ = "glossary"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    keyword = Column(String(255), nullable=False)
    definition = Column(Text)
    created_at = Column("createdAt", DateTime, default=func.now())
    updated_at = Column("updatedAt", DateTime(timezone=True))

    # Relationships
    article_links = relationship("ArticleKeyword", back_populates="keyword_obj")

    def __repr__(self):
        return f"<Glossary(id={self.id}, keyword='{self.keyword}')>"


class ArticleKeyword(Base):
    __tablename__ = "article_keywords"

    article_id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )
    keyword_id = Column(
        PGUUID(as_uuid=True), ForeignKey("glossary.id"), primary_key=True
    )
    id = Column(PGUUID(as_uuid=True))
    created_at = Column("createdAt", DateTime(timezone=True))
    updated_at = Column("updatedAt", DateTime(timezone=True))

    # Relationships
    keyword_obj = relationship("Glossary", back_populates="article_links")


class ThemeTimeline(Base):
    __tablename__ = "theme_timelines"

    theme_id = Column(PGUUID(as_uuid=True), primary_key=True)
    timeline_content = Column(Text)
    last_updated = Column(DateTime)

    def __repr__(self):
        return f"<ThemeTimeline(theme_id={self.theme_id})>"


class ItemRelation(Base):
    __tablename__ = "item_relations"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    created_at = Column("createdAt", DateTime(timezone=True), nullable=False)
    updated_at = Column("updatedAt", DateTime(timezone=True), nullable=False)
    relation_type = Column("relationType", String, nullable=False)
    source_item_id = Column("sourceItemId", PGUUID(as_uuid=True), nullable=False)
    target_item_id = Column("targetItemId", PGUUID(as_uuid=True), nullable=False)

    def __repr__(self):
        return f"<ItemRelation(source={self.source_item_id}, target={self.target_item_id}, type={self.relation_type})>"


class MCQ(Base):
    __tablename__ = "mcqs"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    created_at = Column("createdAt", DateTime(timezone=True), nullable=False)
    updated_at = Column("updatedAt", DateTime(timezone=True), nullable=False)
    question_text = Column("questionText", Text)
    options = Column(JSONB)
    correct_option_ids = Column("correctOptionIds", ARRAY(PGUUID(as_uuid=True)))
    is_multi_select = Column("isMultiSelect", Boolean, default=False)
    learning_item_id = Column("learningItemId", PGUUID(as_uuid=True), nullable=False)
    explanation = Column(JSONB)
    silly_mistake_prone = Column(Boolean, default=False)
    question_pattern = Column(String(255))

    def __repr__(self):
        return f"<MCQ(id={self.id}, pattern='{self.question_pattern}')>"


class ArticleGeneratedQuestion(Base):
    __tablename__ = "article_generated_questions"

    question_id = Column(PGUUID(as_uuid=True), primary_key=True)
    current_affair_id = Column(PGUUID(as_uuid=True))

    # Question metadata
    paper = Column(String(100))
    subject = Column(String(50))
    max_score = Column(Float)
    word_count = Column(Integer)
    year = Column(Integer)
    topics = Column(JSONB)
    sub_topics = Column(JSONB)
    section = Column(Text)
    hints = Column(JSONB)

    # Question content
    question = Column(JSONB)
    model_answer = Column(JSONB)
    question_number = Column(String(50))
    iteration = Column(String(50))
    explanation = Column(JSONB)

    # For MCQ type questions
    difficulty = Column(String(50))
    correct_option = Column(String(10))
    correct_value = Column(Text)
    options = Column(JSONB)

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    status = Column(String(50))
    duration = Column(Float)
    secondary_tag = Column(String(255))
    type = Column(String(50))

    def __repr__(self):
        return f"<ArticleGeneratedQuestion(id={self.question_id}, type='{self.type}')>"
