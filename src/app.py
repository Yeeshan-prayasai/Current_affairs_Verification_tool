import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from src.config import settings
from src.utils.session_state import init_session_state, show_messages
from src.database.connection import get_db
from src.database.repositories.theme_repo import ThemeRepository
from src.database.repositories.article_repo import ArticleRepository
from src.database.repositories.glossary_repo import GlossaryRepository

# Page configuration
st.set_page_config(
    page_title=settings.APP_NAME,
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
init_session_state()

# Show any pending messages
show_messages()

# Main page content
st.title("📋 UPSC Expert Verification Dashboard")
st.markdown("Internal tool for reviewing and editing current affairs content")
st.markdown("---")

# Load stats
try:
    with get_db() as db:
        theme_repo = ThemeRepository(db)
        article_repo = ArticleRepository(db)
        glossary_repo = GlossaryRepository(db)

        theme_count = theme_repo.get_theme_count()
        article_count = article_repo.get_article_count()
        definition_count = glossary_repo.get_keyword_count()

    # Quick stats
    st.markdown("### Content Overview")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Themes", theme_count)

    with col2:
        st.metric("Articles", article_count)

    with col3:
        st.metric("Definitions", definition_count)

    st.markdown("---")

    # Quick actions
    st.markdown("### Quick Actions")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 🏷️ Theme Review")
        st.write("Edit theme names, merge duplicates")
        if st.button("Go to Themes", key="nav_theme"):
            st.switch_page("pages/1_themes.py")

    with col2:
        st.markdown("#### 📰 Article Review")
        st.write("Edit article content and analysis")
        if st.button("Go to Articles", key="nav_article"):
            st.switch_page("pages/2_articles.py")

    with col3:
        st.markdown("#### 📖 Definition Review")
        st.write("Edit glossary definitions")
        if st.button("Go to Definitions", key="nav_definition"):
            st.switch_page("pages/3_definitions.py")

except Exception as e:
    st.error(f"Error connecting to database: {str(e)}")
    st.info("Please ensure your database is configured correctly in the .env file.")
    st.code(
        """
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=your_username
DB_PASSWORD=your_password
DB_NAME=prayas
        """,
        language="bash",
    )
