import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from uuid import UUID
from src.config import settings
from src.utils.session_state import init_session_state, show_messages, set_success
from src.database.connection import get_db
from src.database.repositories.theme_repo import ThemeRepository
from src.services.verification_service import ContentService
from src.components.sidebar import render_sidebar_filters, render_pagination

st.set_page_config(
    page_title=f"Themes - {settings.APP_NAME}",
    page_icon="🏷️",
    layout="wide",
)

init_session_state()
show_messages()

st.title("🏷️ Theme Review")
st.markdown("Edit theme names and merge duplicates")
st.markdown("---")

# Sidebar filters
filters = render_sidebar_filters()

# Service
content_service = ContentService()

try:
    with get_db() as db:
        theme_repo = ThemeRepository(db)

        # Get themes
        themes = theme_repo.get_all_themes(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            search=filters["search"],
            limit=settings.DEFAULT_PAGE_SIZE,
            offset=(st.session_state.current_page - 1) * settings.DEFAULT_PAGE_SIZE,
        )

        total_themes = theme_repo.get_theme_count(search=filters["search"])

    # Pagination
    render_pagination(total_themes, settings.DEFAULT_PAGE_SIZE)

    if not themes:
        st.info("No themes found.")
    else:
        # Two columns layout
        col_list, col_detail = st.columns([1, 2])

        with col_list:
            st.markdown("### Themes")
            for theme in themes:
                with st.container():
                    if st.button(
                        f"**{theme['name']}** ({theme['article_count']} articles)",
                        key=f"theme_{theme['id']}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_theme_id = str(theme["id"])
                        st.rerun()

        with col_detail:
            selected_id = st.session_state.get("selected_theme_id")

            if selected_id:
                with get_db() as db:
                    theme_repo = ThemeRepository(db)
                    theme_data = theme_repo.get_theme_with_articles(UUID(selected_id))

                    if theme_data:
                        theme = theme_data["theme"]
                        articles = theme_data["articles"]

                        # Extract values while session is open
                        theme_name = theme.name
                        theme_id = theme.id
                        theme_created_at = theme.created_at

                        # Extract article data
                        article_list = [
                            {
                                "heading": a.heading,
                                "date": a.date
                            }
                            for a in articles
                        ]

                        # Find similar themes
                        similar_themes = theme_repo.find_similar_themes(theme_name, exclude_id=theme_id)
                        similar_list = [
                            {"id": s.id, "name": s.name}
                            for s in similar_themes
                        ]

                if theme_data:
                    st.subheader(f"Theme: {theme_name}")
                    st.caption(f"{len(article_list)} articles | Created: {theme_created_at.strftime('%Y-%m-%d') if theme_created_at else 'N/A'}")

                    # Edit name
                    new_name = st.text_input("Edit Theme Name", value=theme_name, key="edit_theme_name")
                    if new_name != theme_name:
                        if st.button("Save Name", key="save_theme_name"):
                            result = content_service.update_theme_name(UUID(selected_id), new_name)
                            if result["success"]:
                                set_success("Theme name updated!")
                                st.rerun()

                    # Articles list
                    st.markdown("---")
                    st.markdown("### Articles")
                    for article in article_list[:10]:
                        st.markdown(f"- {article['heading'][:60]}... ({article['date'].strftime('%Y-%m-%d') if article['date'] else 'N/A'})")
                    if len(article_list) > 10:
                        st.caption(f"... and {len(article_list) - 10} more")

                    # Merge option
                    st.markdown("---")
                    st.markdown("### Merge with Another Theme")

                    if similar_list:
                        for sim in similar_list:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(sim["name"])
                            with col2:
                                if st.button("Merge →", key=f"merge_{sim['id']}"):
                                    result = content_service.merge_themes(UUID(selected_id), sim["id"])
                                    if result["success"]:
                                        set_success(f"Merged {result['articles_moved']} articles!")
                                        st.session_state.selected_theme_id = None
                                        st.rerun()
                    else:
                        st.info("No similar themes found")
            else:
                st.info("👈 Select a theme from the list to edit")

except Exception as e:
    st.error(f"Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
