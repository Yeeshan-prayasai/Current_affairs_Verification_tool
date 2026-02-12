import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from uuid import UUID
from src.config import settings
from src.utils.session_state import init_session_state, show_messages, set_success
from src.database.connection import get_db
from src.database.repositories.trending_repo import TrendingRepository

st.set_page_config(
    page_title=f"Trending - {settings.APP_NAME}",
    page_icon="🔥",
    layout="wide",
)

init_session_state()
show_messages()

st.title("🔥 Trending Theme Selector")

with st.expander("📋 Workflow Guide", expanded=False):
    st.markdown("""
**Select 5 Trending Themes**
- Use the date filter (sidebar) to view today's themes
- Browse themes and check the ones most relevant for today
- Select exactly **5 themes** and click **Save Trending Themes**
- Click on a theme to preview its questions and summary
""")

st.markdown("---")

# Sidebar - date filter
st.sidebar.header("Filter by Article Date")

# Sidebar - workflow guide
st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Quick Steps")
st.sidebar.markdown("""
1. Filter by **today's date**
2. Select **5 trending themes** → Save
""")

today = datetime.now().date()

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.sidebar.button("Today", use_container_width=True, key="trend_today"):
        st.session_state.trend_date_filter = "today"
        st.rerun()
    if st.sidebar.button("This Week", use_container_width=True, key="trend_week"):
        st.session_state.trend_date_filter = "week"
        st.rerun()
with col2:
    if st.sidebar.button("Yesterday", use_container_width=True, key="trend_yesterday"):
        st.session_state.trend_date_filter = "yesterday"
        st.rerun()
    if st.sidebar.button("This Month", use_container_width=True, key="trend_month"):
        st.session_state.trend_date_filter = "month"
        st.rerun()

if st.sidebar.button("Show All", use_container_width=True, key="trend_all"):
    st.session_state.trend_date_filter = "all"
    st.rerun()

# Date picker for custom date
if "trend_custom_date_value" not in st.session_state:
    st.session_state.trend_custom_date_value = today

custom_date = st.sidebar.date_input(
    "Or pick a date",
    value=st.session_state.trend_custom_date_value,
    key="trend_date_picker"
)

if custom_date != st.session_state.trend_custom_date_value:
    st.session_state.trend_custom_date_value = custom_date
    st.session_state.trend_date_filter = "custom"

# Default to today
date_filter = st.session_state.get("trend_date_filter", "today")

if date_filter == "custom":
    start_date = st.session_state.trend_custom_date_value
    end_date = st.session_state.trend_custom_date_value
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
    st.sidebar.caption("Showing themes with articles from last 7 days")
elif date_filter == "month":
    start_date = today - timedelta(days=30)
    end_date = today
    st.sidebar.caption("Showing themes with articles from last 30 days")
else:
    start_date = None
    end_date = None
    st.sidebar.caption("Showing all themes")

# Search
search = st.sidebar.text_input(
    "Search themes",
    placeholder="Search...",
    key="trending_search",
)

# Initialize selected trending themes in session state
if "selected_trending" not in st.session_state:
    st.session_state.selected_trending = set()

# Track which theme's questions to show
if "trending_detail_theme" not in st.session_state:
    st.session_state.trending_detail_theme = None

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


def toggle_trending(theme_id_str):
    if theme_id_str in st.session_state.selected_trending:
        st.session_state.selected_trending.discard(theme_id_str)
    else:
        st.session_state.selected_trending.add(theme_id_str)


try:
    with get_db() as db:
        trending_repo = TrendingRepository(db)
        all_themes = trending_repo.get_themes_with_article_count(
            search=search if search else None,
            start_date=start_date,
            end_date=end_date,
        )

    # On first load, pre-select currently trending themes
    if "trending_initialized" not in st.session_state:
        st.session_state.selected_trending = {
            str(t["id"]) for t in all_themes if t["is_trending"]
        }
        st.session_state.trending_initialized = True

    selected = st.session_state.selected_trending
    num_selected = len(selected)

    # Selection counter
    if num_selected == 5:
        st.success(f"**{num_selected}/5 themes selected** - Ready to save!")
    elif num_selected > 5:
        st.warning(f"**{num_selected}/5 themes selected** - Please deselect {num_selected - 5} theme(s)")
    else:
        st.info(f"**{num_selected}/5 themes selected** - Select {5 - num_selected} more")

    # Save and clear buttons
    col_save, col_clear = st.columns([1, 1])
    with col_save:
        if st.button(
            "Save Trending Themes",
            disabled=num_selected != 5,
            use_container_width=True,
            type="primary",
        ):
            with get_db() as db:
                trending_repo = TrendingRepository(db)
                trending_repo.save_trending_themes(
                    [UUID(tid) for tid in selected]
                )
                num_daily = trending_repo.auto_select_daily_questions(today)
            set_success(f"Trending themes saved! {num_daily} questions marked as daily-selected.")
            st.rerun()
    with col_clear:
        if st.button("Clear Selection", use_container_width=True):
            st.session_state.selected_trending = set()
            st.rerun()

    st.markdown("---")

    if not all_themes:
        st.info("No themes found for the selected date range.")
    else:
        # Two column layout: theme list | questions detail
        col_list, col_detail = st.columns([1, 2])

        with col_list:
            st.markdown(f"### Themes ({len(all_themes)})")

            for theme in all_themes:
                t_id = str(theme["id"])
                is_selected = t_id in selected

                with st.container(border=True):
                    col_check, col_name = st.columns([0.5, 9.5])

                    with col_check:
                        st.checkbox(
                            "sel",
                            value=is_selected,
                            key=f"trend_sel_{t_id}",
                            on_change=toggle_trending,
                            args=(t_id,),
                            label_visibility="collapsed",
                        )

                    with col_name:
                        label = f"**{theme['name']}** ({theme['article_count']} articles)"
                        if theme["is_trending"]:
                            label += " 🔥"
                        if st.button(
                            label,
                            key=f"trend_view_{t_id}",
                            use_container_width=True,
                        ):
                            st.session_state.trending_detail_theme = t_id
                            st.rerun()

        with col_detail:
            detail_id = st.session_state.trending_detail_theme

            if detail_id:
                # Find theme info
                theme_info = next((t for t in all_themes if str(t["id"]) == detail_id), None)

                if theme_info:
                    st.subheader(f"{theme_info['name']}")
                    is_cur_trending = str(theme_info["id"]) in selected
                    status_label = "Selected as trending" if is_cur_trending else "Not selected"
                    st.caption(f"{theme_info['article_count']} articles | {status_label}")

                    if theme_info.get("summary"):
                        with st.expander("Theme Summary", expanded=False):
                            st.markdown(theme_info["summary"])

                    # Fetch questions for this theme
                    with get_db() as db:
                        trending_repo = TrendingRepository(db)
                        questions = trending_repo.get_questions_for_theme(UUID(detail_id))

                    st.markdown("---")
                    st.markdown(f"### Questions ({len(questions)})")

                    if not questions:
                        st.info("No questions found for this theme")
                    else:
                        for i, q in enumerate(questions):
                            with st.container(border=True):
                                st.caption(f"From: {q.get('article_title', 'Unknown')}")
                                st.markdown(f"**Q{i+1}.** {q.get('question_text', '')}")

                                # Options with correct answer markers
                                options = q.get("options")
                                if options and isinstance(options, list):
                                    for opt in options:
                                        if isinstance(opt, dict):
                                            opt_id = opt.get('id', '')
                                            opt_text = opt.get('text', opt.get('value', str(opt)))
                                            is_correct = str(opt_id) in [str(c) for c in (q.get("correct_option_ids") or [])]
                                            marker = " ✓" if is_correct else ""
                                            st.markdown(f"- {opt_text}{marker}")

                                # Explanation
                                explanation = q.get("explanation")
                                if explanation:
                                    with st.expander("Explanation", expanded=False):
                                        st.markdown(get_english_text(explanation))
                else:
                    st.info("Theme not found in current filter. Try changing the date range.")
            else:
                st.info("👈 Select a theme to view its questions")

except Exception as e:
    st.error(f"Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
