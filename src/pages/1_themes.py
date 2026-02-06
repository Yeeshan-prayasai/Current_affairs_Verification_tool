import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from uuid import UUID
from src.config import settings
from src.utils.session_state import init_session_state, show_messages, set_success
from src.database.connection import get_db
from src.database.repositories.theme_repo import ThemeRepository
from src.services.verification_service import ContentService
from src.components.sidebar import render_pagination

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

# Custom sidebar for themes page with Today/Weekly/Monthly filters
st.sidebar.header("Filter by Article Date")

# Quick filter buttons
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.sidebar.button("Today", use_container_width=True, key="theme_today"):
        st.session_state.theme_date_filter = "today"
        st.session_state.current_page = 1
        st.rerun()
    if st.sidebar.button("This Week", use_container_width=True, key="theme_week"):
        st.session_state.theme_date_filter = "week"
        st.session_state.current_page = 1
        st.rerun()
with col2:
    if st.sidebar.button("Yesterday", use_container_width=True, key="theme_yesterday"):
        st.session_state.theme_date_filter = "yesterday"
        st.session_state.current_page = 1
        st.rerun()
    if st.sidebar.button("This Month", use_container_width=True, key="theme_month"):
        st.session_state.theme_date_filter = "month"
        st.session_state.current_page = 1
        st.rerun()

if st.sidebar.button("Show All", use_container_width=True, key="theme_all"):
    st.session_state.theme_date_filter = "all"
    st.session_state.current_page = 1
    st.rerun()

# Date picker for custom date
today = datetime.now().date()

# Initialize custom date tracking
if "theme_custom_date_value" not in st.session_state:
    st.session_state.theme_custom_date_value = today

custom_date = st.sidebar.date_input(
    "Or pick a date",
    value=st.session_state.theme_custom_date_value,
    key="theme_date_picker"
)

# If user changed the date picker, switch to custom mode
if custom_date != st.session_state.theme_custom_date_value:
    st.session_state.theme_custom_date_value = custom_date
    st.session_state.theme_date_filter = "custom"
    st.session_state.current_page = 1

# Determine date range based on filter (default to "all")
date_filter = st.session_state.get("theme_date_filter", "all")

if date_filter == "custom":
    start_date = st.session_state.theme_custom_date_value
    end_date = st.session_state.theme_custom_date_value
    st.sidebar.caption(f"Showing themes with articles from {start_date.strftime('%d %b %Y')}")
elif date_filter == "today":
    start_date = today
    end_date = today
    st.sidebar.caption(f"Showing themes with articles from today ({today.strftime('%d %b')})")
elif date_filter == "yesterday":
    yesterday = today - timedelta(days=1)
    start_date = yesterday
    end_date = yesterday
    st.sidebar.caption(f"Showing themes with articles from yesterday ({yesterday.strftime('%d %b')})")
elif date_filter == "week":
    start_date = today - timedelta(days=7)
    end_date = today
    st.sidebar.caption(f"Showing themes with articles from last 7 days")
elif date_filter == "month":
    start_date = today - timedelta(days=30)
    end_date = today
    st.sidebar.caption(f"Showing themes with articles from last 30 days")
else:
    start_date = None
    end_date = None
    st.sidebar.caption("Showing all themes")

# Search
search = st.sidebar.text_input(
    "Search themes",
    value=st.session_state.get("search_query", ""),
    placeholder="Search...",
    key="theme_search",
)

# Service
content_service = ContentService()

try:
    with get_db() as db:
        theme_repo = ThemeRepository(db)

        # Get themes based on article dates
        if start_date or end_date:
            themes = theme_repo.get_themes_by_article_date(
                start_date=start_date,
                end_date=end_date,
                search=search if search else None,
                limit=settings.DEFAULT_PAGE_SIZE,
                offset=(st.session_state.current_page - 1) * settings.DEFAULT_PAGE_SIZE,
            )
            total_themes = theme_repo.get_theme_count_by_article_date(
                start_date=start_date,
                end_date=end_date,
                search=search if search else None,
            )
        else:
            themes = theme_repo.get_all_themes(
                search=search if search else None,
                limit=settings.DEFAULT_PAGE_SIZE,
                offset=(st.session_state.current_page - 1) * settings.DEFAULT_PAGE_SIZE,
            )
            total_themes = theme_repo.get_theme_count(search=search if search else None)

    # Pagination
    render_pagination(total_themes, settings.DEFAULT_PAGE_SIZE)

    if not themes:
        if start_date or end_date:
            st.info("No themes found for the selected date range.")
        else:
            st.info("No themes found.")
    else:
        # Two columns layout
        col_list, col_detail = st.columns([1, 2])

        with col_list:
            st.markdown(f"### Themes ({total_themes})")
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
                                "id": a.id,
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
                    for article in article_list:
                        article_heading = article['heading'] or "Untitled"
                        article_date = article['date'].strftime('%Y-%m-%d') if article['date'] else 'N/A'
                        article_id = article['id']

                        col_article, col_link = st.columns([5, 1])
                        with col_article:
                            st.markdown(f"**{article_heading}** ({article_date})")
                        with col_link:
                            if st.button("View →", key=f"view_article_{article_id}"):
                                st.session_state.selected_article_id = article_id
                                st.switch_page("pages/2_articles.py")

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
