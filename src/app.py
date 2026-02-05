import sys
from pathlib import Path
from datetime import datetime
from uuid import UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from src.config import settings
from src.utils.session_state import init_session_state, show_messages, set_success
from src.database.connection import get_db
from src.database.repositories.theme_repo import ThemeRepository
from src.database.repositories.article_repo import ArticleRepository
from src.services.verification_service import ContentService

# Page configuration
st.set_page_config(
    page_title=settings.APP_NAME,
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize session state
init_session_state()

# Show any pending messages
show_messages()

# Service
content_service = ContentService()

# Main page content
st.title("📋 Today's Current Affairs Review")
today = datetime.now().date()
st.markdown(f"**{today.strftime('%A, %d %B %Y')}**")
st.markdown("---")

try:
    with get_db() as db:
        theme_repo = ThemeRepository(db)
        article_repo = ArticleRepository(db)

        # Get today's articles grouped by theme
        todays_articles = article_repo.get_articles(
            start_date=today,
            end_date=today,
            limit=100,
        )

        # Get all themes for the dropdown
        all_themes = theme_repo.get_all_themes(limit=500)
        all_themes_list = [{"id": t["id"], "name": t["name"]} for t in all_themes]

    if not todays_articles:
        st.info("No articles found for today.")
        st.markdown("---")
        st.markdown("### Quick Navigation")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🏷️ All Themes", use_container_width=True):
                st.switch_page("pages/1_themes.py")
        with col2:
            if st.button("📰 All Articles", use_container_width=True):
                st.switch_page("pages/2_articles.py")
        with col3:
            if st.button("📖 Definitions", use_container_width=True):
                st.switch_page("pages/3_definitions.py")
    else:
        # Group articles by theme
        themes_dict = {}
        for article in todays_articles:
            theme_id = article.get("theme_id")
            theme_name = article.get("theme_name") or "Uncategorized"
            if theme_name not in themes_dict:
                themes_dict[theme_name] = {
                    "theme_id": theme_id,
                    "articles": []
                }
            themes_dict[theme_name]["articles"].append(article)

        st.markdown(f"### {len(todays_articles)} articles in {len(themes_dict)} themes")

        # Display each theme with its articles
        for theme_name, theme_data in themes_dict.items():
            theme_id = theme_data["theme_id"]
            articles = theme_data["articles"]

            with st.expander(f"🏷️ **{theme_name}** ({len(articles)} articles)", expanded=True):
                # Theme editing section
                col1, col2 = st.columns([3, 1])
                with col1:
                    new_theme_name = st.text_input(
                        "Theme Name",
                        value=theme_name if theme_name != "Uncategorized" else "",
                        key=f"theme_name_{theme_id}",
                        placeholder="Enter theme name..."
                    )
                with col2:
                    if theme_id and new_theme_name and new_theme_name != theme_name:
                        if st.button("Save Theme", key=f"save_theme_{theme_id}"):
                            result = content_service.update_theme_name(UUID(str(theme_id)), new_theme_name)
                            if result["success"]:
                                set_success(f"Theme renamed to '{new_theme_name}'")
                                st.rerun()

                # Merge with similar theme
                if theme_id:
                    with get_db() as db:
                        theme_repo = ThemeRepository(db)
                        similar = theme_repo.find_similar_themes(theme_name, exclude_id=theme_id, limit=3)
                        similar_list = [{"id": s.id, "name": s.name} for s in similar]

                    if similar_list:
                        st.caption("Merge with similar theme:")
                        merge_cols = st.columns(len(similar_list) + 1)
                        for i, sim in enumerate(similar_list):
                            with merge_cols[i]:
                                if st.button(f"→ {sim['name'][:20]}", key=f"merge_{theme_id}_{sim['id']}"):
                                    result = content_service.merge_themes(UUID(str(theme_id)), sim["id"])
                                    if result["success"]:
                                        set_success(f"Merged {result['articles_moved']} articles!")
                                        st.rerun()

                st.markdown("---")

                # Display articles
                for article in articles:
                    article_id = article["id"]
                    article_key = f"article_{article_id}"

                    st.markdown(f"#### 📄 {article['heading']}")

                    # Load full article data for editing
                    with get_db() as db:
                        article_repo = ArticleRepository(db)
                        full_article = article_repo.get_article_by_id(article_id)
                        if full_article:
                            article_mains = full_article.mains_analysis or ""
                            article_prelims = full_article.prelims_info or ""
                            article_pointed = full_article.pointed_analysis or ""

                    # Tabs for editing
                    tabs = st.tabs(["Pointed Analysis", "Mains Analysis", "Prelims Info"])

                    with tabs[0]:
                        st.markdown(article_pointed)
                        pointed = st.text_area(
                            "Edit Pointed Analysis",
                            value=article_pointed,
                            height=150,
                            key=f"pointed_{article_id}",
                            label_visibility="collapsed"
                        )

                    with tabs[1]:
                        mains = st.text_area(
                            "Mains Analysis",
                            value=article_mains,
                            height=150,
                            key=f"mains_{article_id}"
                        )

                    with tabs[2]:
                        prelims = st.text_area(
                            "Prelims Info",
                            value=article_prelims,
                            height=150,
                            key=f"prelims_{article_id}"
                        )

                    # Save button for article
                    if st.button("💾 Save Article", key=f"save_{article_id}"):
                        updates = {
                            "pointed_analysis": pointed,
                            "mains_analysis": mains,
                            "prelims_info": prelims,
                        }
                        result = content_service.update_article(article_id, updates)
                        if result["success"]:
                            set_success(f"Article saved!")
                            st.rerun()

                    st.markdown("---")

        # Navigation to other pages
        st.markdown("### Other Pages")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🏷️ All Themes", use_container_width=True):
                st.switch_page("pages/1_themes.py")
        with col2:
            if st.button("📰 All Articles", use_container_width=True):
                st.switch_page("pages/2_articles.py")
        with col3:
            if st.button("📖 Definitions", use_container_width=True):
                st.switch_page("pages/3_definitions.py")

except Exception as e:
    st.error(f"Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
