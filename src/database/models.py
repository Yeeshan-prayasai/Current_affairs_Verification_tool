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
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


# ============================================
# EXISTING TABLES (mapped for ORM usage)
# ============================================


class Theme(Base):
    __tablename__ = "themes"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    articles = relationship("CurrentAffair", back_populates="theme")

    def __repr__(self):
        return f"<Theme(id={self.id}, name='{self.name}')>"


class Glossary(Base):
    __tablename__ = "glossary"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    keyword = Column(String(255), nullable=False)
    definition = Column(Text)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    article_links = relationship("ArticleKeyword", back_populates="keyword_obj")

    def __repr__(self):
        return f"<Glossary(id={self.id}, keyword='{self.keyword}')>"


class CurrentAffair(Base):
    __tablename__ = "current_affairs"

    id = Column(Integer, primary_key=True)
    current_affair_id = Column(PGUUID(as_uuid=True), unique=True)
    date = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Content fields
    paper = Column(String(255))
    heading = Column(Text)
    description = Column(Text)
    source = Column(String(255))
    published_at = Column(DateTime)
    read_time = Column(Integer)

    # Analysis fields
    pointed_analysis = Column(Text)
    mains_analysis = Column(Text)
    prelims_info = Column(Text)

    # Classification
    mains_subject = Column(String(50))
    prelims_subject = Column(String(50))
    mains_topics = Column(JSONB)
    prelims_topics = Column(JSONB)
    secondary_tag = Column(String(50))

    # Newspaper info
    news_paper = Column(String(50))
    news_paper_date = Column(Date)

    # Additional metadata
    sub_topics = Column(String(255))
    keywords = Column(JSONB)
    embedding = Column(JSONB)

    # Foreign keys
    theme_id = Column(PGUUID(as_uuid=True), ForeignKey("themes.id"))

    # Relationships
    theme = relationship("Theme", back_populates="articles")
    keyword_links = relationship("ArticleKeyword", back_populates="article")

    def __repr__(self):
        return f"<CurrentAffair(id={self.id}, heading='{self.heading[:50] if self.heading else ''}...')>"


class ArticleKeyword(Base):
    __tablename__ = "article_keywords"

    article_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("current_affairs.current_affair_id"),
        primary_key=True,
    )
    keyword_id = Column(
        PGUUID(as_uuid=True), ForeignKey("glossary.id"), primary_key=True
    )

    # Relationships
    article = relationship("CurrentAffair", back_populates="keyword_links")
    keyword_obj = relationship("Glossary", back_populates="article_links")


class ThemeTimeline(Base):
    __tablename__ = "theme_timelines"

    theme_id = Column(PGUUID(as_uuid=True), ForeignKey("themes.id"), primary_key=True)
    timeline_content = Column(Text)
    last_updated = Column(DateTime)

    def __repr__(self):
        return f"<ThemeTimeline(theme_id={self.theme_id})>"


class ArticleGeneratedQuestion(Base):
    __tablename__ = "article_generated_questions"

    question_id = Column(PGUUID(as_uuid=True), primary_key=True)
    current_affair_id = Column(PGUUID(as_uuid=True), ForeignKey("current_affairs.current_affair_id"))

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


