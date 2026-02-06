import sys
from pathlib import Path
from datetime import datetime, timedelta
from uuid import UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from src.config import settings
from src.utils.session_state import init_session_state, show_messages, set_success
from src.database.connection import get_db
from src.database.repositories.theme_repo import ThemeRepository
from src.database.repositories.article_repo import ArticleRepository
from src.database.repositories.question_repo import QuestionRepository
from src.services.verification_service import ContentService

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

# Service
content_service = ContentService()

# Date filter selection
today = datetime.now().date()
yesterday = today - timedelta(days=1)

# Filter buttons in sidebar
st.sidebar.header("Date Filter")
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.sidebar.button("Today", use_container_width=True, key="main_today"):
        st.session_state.main_date_filter = "today"
        st.session_state.main_custom_date = None
        st.rerun()
with col2:
    if st.sidebar.button("Yesterday", use_container_width=True, key="main_yesterday"):
        st.session_state.main_date_filter = "yesterday"
        st.session_state.main_custom_date = None
        st.rerun()

# Date picker for custom date
# Initialize main_custom_date if not set
if "main_custom_date" not in st.session_state:
    st.session_state.main_custom_date = today

custom_date = st.sidebar.date_input(
    "Or pick a date",
    value=st.session_state.main_custom_date,
    key="main_date_picker"
)

# Only set to custom filter if user changed the date
if custom_date != st.session_state.main_custom_date:
    st.session_state.main_custom_date = custom_date
    st.session_state.main_date_filter = "custom"

# Determine which date to show
date_filter = st.session_state.get("main_date_filter", "today")
if date_filter == "custom" and st.session_state.get("main_custom_date"):
    selected_date = st.session_state.main_custom_date
    if selected_date == today:
        date_label = "Today's"
    elif selected_date == yesterday:
        date_label = "Yesterday's"
    else:
        date_label = f"{selected_date.strftime('%d %b')}"
elif date_filter == "yesterday":
    selected_date = yesterday
    date_label = "Yesterday's"
else:
    selected_date = today
    date_label = "Today's"

st.sidebar.caption(f"Showing: {selected_date.strftime('%d %b %Y')}")

# Main page content
st.title(f"📋 {date_label} Current Affairs Review")
st.markdown(f"**{selected_date.strftime('%A, %d %B %Y')}**")
st.markdown("---")

try:
    with get_db() as db:
        theme_repo = ThemeRepository(db)
        article_repo = ArticleRepository(db)

        # Get articles for selected date
        todays_articles = article_repo.get_articles(
            start_date=selected_date,
            end_date=selected_date,
            limit=100,
        )

        # Get all themes for the dropdown
        all_themes = theme_repo.get_all_themes(limit=500)
        all_themes_list = [{"id": t["id"], "name": t["name"]} for t in all_themes]

    if not todays_articles:
        st.info(f"No articles found for {selected_date.strftime('%d %b %Y')}.")
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
        theme_order = []  # Keep track of order
        for article in todays_articles:
            theme_id = article.get("theme_id")
            theme_name = article.get("theme_name") or "Uncategorized"
            if theme_name not in themes_dict:
                themes_dict[theme_name] = {
                    "theme_id": theme_id,
                    "articles": []
                }
                theme_order.append(theme_name)
            themes_dict[theme_name]["articles"].append(article)

        st.markdown(f"### {len(todays_articles)} articles in {len(themes_dict)} themes")

        # Theme navigation section - clickable buttons to jump to themes
        st.markdown("#### Quick Navigation")
        theme_cols = st.columns(min(len(theme_order), 4))
        for i, tname in enumerate(theme_order):
            col_idx = i % 4
            with theme_cols[col_idx]:
                article_count = len(themes_dict[tname]["articles"])
                if st.button(f"🏷️ {tname[:25]}{'...' if len(tname) > 25 else ''} ({article_count})",
                           key=f"nav_{i}", use_container_width=True):
                    st.session_state.selected_theme_view = tname
                    st.rerun()

        st.markdown("---")

        # Determine which theme to show
        selected_theme_view = st.session_state.get("selected_theme_view")

        # If a theme is selected, show only that theme; otherwise show all
        if selected_theme_view and selected_theme_view in themes_dict:
            themes_to_show = {selected_theme_view: themes_dict[selected_theme_view]}
            if st.button("← Back to All Themes", key="back_to_all"):
                st.session_state.selected_theme_view = None
                st.rerun()
        else:
            themes_to_show = themes_dict

        # Display each theme with its articles
        for theme_name, theme_data in themes_to_show.items():
            theme_id = theme_data["theme_id"]
            articles = theme_data["articles"]

            st.markdown(f"## 🏷️ {theme_name}")
            st.caption(f"{len(articles)} articles")

            # Theme editing section - only show if theme exists (not Uncategorized)
            if theme_id:
                with st.expander("Edit Theme", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        new_theme_name = st.text_input(
                            "Rename Theme",
                            value=theme_name,
                            key=f"theme_name_{theme_id}",
                            label_visibility="collapsed"
                        )
                    with col2:
                        if new_theme_name and new_theme_name != theme_name:
                            if st.button("Save", key=f"save_theme_{theme_id}"):
                                result = content_service.update_theme_name(UUID(str(theme_id)), new_theme_name)
                                if result["success"]:
                                    set_success(f"Theme renamed to '{new_theme_name}'")
                                    st.session_state.selected_theme_view = new_theme_name
                                    st.rerun()

                    # Merge with similar theme
                    with get_db() as db:
                        theme_repo = ThemeRepository(db)
                        similar = theme_repo.find_similar_themes(theme_name, exclude_id=theme_id, limit=3)
                        similar_list = [{"id": s.id, "name": s.name} for s in similar]

                    if similar_list:
                        st.caption("Merge into another theme:")
                        for sim in similar_list:
                            if st.button(f"→ Merge into '{sim['name'][:30]}'", key=f"merge_{theme_id}_{sim['id']}"):
                                result = content_service.merge_themes(UUID(str(theme_id)), sim["id"])
                                if result["success"]:
                                    set_success(f"Merged {result['articles_moved']} articles!")
                                    st.session_state.selected_theme_view = None
                                    st.rerun()

            # Display articles
            for article in articles:
                article_id = article["id"]
                article_theme_id = article.get("theme_id")

                with st.container(border=True):
                    st.markdown(f"#### 📄 {article['heading']}")

                    # Load full article data for editing
                    with get_db() as db:
                        article_repo = ArticleRepository(db)
                        question_repo = QuestionRepository(db)
                        full_article = article_repo.get_article_by_id(article_id)
                        if full_article:
                            article_mains = full_article.mains_analysis or ""
                            article_prelims = full_article.prelims_info or ""
                            article_pointed = full_article.pointed_analysis or ""
                            article_current_affair_id = full_article.current_affair_id
                            # Get questions
                            article_questions = question_repo.get_questions_for_article(article_current_affair_id)
                        else:
                            article_questions = []

                    # Theme selector for this article
                    theme_names_list = ["None"] + [t["name"] for t in all_themes_list]
                    theme_ids_list = [None] + [t["id"] for t in all_themes_list]
                    current_theme_idx = 0
                    if article_theme_id:
                        for i, tid in enumerate(theme_ids_list):
                            if tid == article_theme_id:
                                current_theme_idx = i
                                break

                    col_theme, col_btn = st.columns([3, 1])
                    with col_theme:
                        selected_theme_idx = st.selectbox(
                            "Article Theme",
                            options=range(len(theme_names_list)),
                            format_func=lambda i: theme_names_list[i],
                            index=current_theme_idx,
                            key=f"article_theme_{article_id}",
                            label_visibility="collapsed"
                        )
                    with col_btn:
                        new_article_theme_id = theme_ids_list[selected_theme_idx]
                        if new_article_theme_id != article_theme_id:
                            if st.button("Update", key=f"update_theme_{article_id}"):
                                result = content_service.update_article(article_id, {"theme_id": new_article_theme_id})
                                if result["success"]:
                                    set_success("Article theme updated!")
                                    st.rerun()

                    # Tabs for content - show preview by default, edit on button click
                    tabs = st.tabs(["Pointed Analysis", "Mains Analysis", "Prelims Info"])

                    # Track edit state for each field
                    edit_pointed_key = f"edit_pointed_{article_id}"
                    edit_mains_key = f"edit_mains_{article_id}"
                    edit_prelims_key = f"edit_prelims_{article_id}"

                    with tabs[0]:
                        st.markdown(article_pointed)
                        if st.button("✏️ Edit", key=f"btn_edit_pointed_{article_id}"):
                            st.session_state[edit_pointed_key] = not st.session_state.get(edit_pointed_key, False)
                            st.rerun()
                        if st.session_state.get(edit_pointed_key, False):
                            pointed = st.text_area(
                                "Edit Pointed Analysis",
                                value=article_pointed,
                                height=150,
                                key=f"pointed_{article_id}",
                                label_visibility="collapsed"
                            )
                            if st.button("💾 Save", key=f"save_pointed_{article_id}"):
                                result = content_service.update_article(article_id, {"pointed_analysis": pointed})
                                if result["success"]:
                                    st.session_state[edit_pointed_key] = False
                                    set_success("Pointed Analysis saved!")
                                    st.rerun()

                    with tabs[1]:
                        st.markdown(article_mains)
                        if st.button("✏️ Edit", key=f"btn_edit_mains_{article_id}"):
                            st.session_state[edit_mains_key] = not st.session_state.get(edit_mains_key, False)
                            st.rerun()
                        if st.session_state.get(edit_mains_key, False):
                            mains = st.text_area(
                                "Edit Mains Analysis",
                                value=article_mains,
                                height=150,
                                key=f"mains_{article_id}",
                                label_visibility="collapsed"
                            )
                            if st.button("💾 Save", key=f"save_mains_{article_id}"):
                                result = content_service.update_article(article_id, {"mains_analysis": mains})
                                if result["success"]:
                                    st.session_state[edit_mains_key] = False
                                    set_success("Mains Analysis saved!")
                                    st.rerun()

                    with tabs[2]:
                        st.markdown(article_prelims)
                        if st.button("✏️ Edit", key=f"btn_edit_prelims_{article_id}"):
                            st.session_state[edit_prelims_key] = not st.session_state.get(edit_prelims_key, False)
                            st.rerun()
                        if st.session_state.get(edit_prelims_key, False):
                            prelims = st.text_area(
                                "Edit Prelims Info",
                                value=article_prelims,
                                height=150,
                                key=f"prelims_{article_id}",
                                label_visibility="collapsed"
                            )
                            if st.button("💾 Save", key=f"save_prelims_{article_id}"):
                                result = content_service.update_article(article_id, {"prelims_info": prelims})
                                if result["success"]:
                                    st.session_state[edit_prelims_key] = False
                                    set_success("Prelims Info saved!")
                                    st.rerun()

                    # Helper function to extract English text
                    def get_english_text(content):
                        if content is None:
                            return ""
                        if isinstance(content, dict):
                            if "english" in content:
                                return str(content["english"])
                            if "text" in content:
                                return str(content["text"])
                            return str(content)
                        return str(content)

                    def get_english_options(options):
                        if options is None:
                            return None
                        if isinstance(options, dict):
                            if "english" in options:
                                return options["english"]
                            return options
                        return options

                    # Questions section - collapsible
                    if article_questions:
                        with st.expander(f"📝 Questions ({len(article_questions)})", expanded=False):
                            for i, q in enumerate(article_questions):
                                q_type = q.get("type") or "Question"
                                q_id = q.get("question_id")
                                st.markdown(f"**{q_type} {i+1}**")

                                # Display question (English only)
                                question_text = get_english_text(q.get("question"))
                                if question_text:
                                    st.markdown(question_text)

                                # Key info in a row
                                info_parts = []
                                if q.get("paper"):
                                    info_parts.append(f"Paper: {q['paper']}")
                                if q.get("subject"):
                                    info_parts.append(f"Subject: {q['subject']}")
                                if q.get("difficulty"):
                                    info_parts.append(f"Difficulty: {q['difficulty']}")
                                if info_parts:
                                    st.caption(" | ".join(info_parts))

                                # Options for MCQ (English only)
                                options = get_english_options(q.get("options"))
                                if options and isinstance(options, dict):
                                    for key, val in options.items():
                                        st.markdown(f"- **{key}**: {val}")

                                # Answer
                                if q.get("correct_option") or q.get("correct_value"):
                                    answer = q.get('correct_option', '')
                                    value = get_english_text(q.get('correct_value')) if q.get('correct_value') else ''
                                    st.markdown(f"**Answer:** {answer} {value}".strip())

                                if i < len(article_questions) - 1:
                                    st.markdown("---")

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
