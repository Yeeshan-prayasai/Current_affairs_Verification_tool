import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from uuid import UUID
from src.config import settings
from src.utils.session_state import init_session_state, show_messages, set_success
from src.database.connection import get_db
from src.database.repositories.question_repo import QuestionRepository
from src.database.repositories.theme_repo import ThemeRepository
from src.services.verification_service import ContentService

st.set_page_config(
    page_title=f"Questions - {settings.APP_NAME}",
    page_icon="❓",
    layout="wide",
)

init_session_state()
show_messages()

st.title("❓ Daily Question Selector")
st.markdown("Select 10 questions from today's articles for the daily quiz")
st.markdown("---")

# Sidebar - date picker
st.sidebar.header("Select Date")

today = datetime.now().date()

# Initialize date in session state using the widget key directly
if "q_date_picker" not in st.session_state:
    st.session_state.q_date_picker = today

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.sidebar.button("Today", use_container_width=True, key="q_today"):
        st.session_state.q_date_picker = today
        st.rerun()
with col2:
    if st.sidebar.button("Yesterday", use_container_width=True, key="q_yesterday"):
        st.session_state.q_date_picker = today - timedelta(days=1)
        st.rerun()

selected_date = st.sidebar.date_input(
    "Or pick a date",
    key="q_date_picker"
)

st.sidebar.caption(f"Showing questions from: **{selected_date.strftime('%d %b %Y')}**")

# Pattern filter
if "q_type_filter" not in st.session_state:
    st.session_state.q_type_filter = "All"

type_filter = st.sidebar.selectbox(
    "Filter by pattern",
    options=["All"],
    key="q_type_filter"
)

# Initialize selected questions in session state
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = set()

# Service
content_service = ContentService()


def get_english_text(content):
    """Extract English text from content that may have hindi/english keys."""
    if content is None:
        return ""
    if isinstance(content, dict):
        if "english" in content:
            return str(content["english"])
        if "text" in content:
            return str(content["text"])
        return str(content)
    return str(content)


# Callback for checkbox toggle
def toggle_question(q_id):
    if q_id in st.session_state.selected_questions:
        st.session_state.selected_questions.discard(q_id)
    else:
        st.session_state.selected_questions.add(q_id)


try:
    # Theme filter - fetch all themes for the dropdown
    with get_db() as db:
        theme_repo = ThemeRepository(db)
        all_themes = theme_repo.get_all_themes(limit=500)

    all_theme_names = [t["name"] for t in all_themes]
    theme_id_map = {t["name"]: t["id"] for t in all_themes}
    theme_options = ["All"] + sorted(all_theme_names)

    # Reset if previously selected value is no longer in options
    if st.session_state.get("q_theme_filter") not in theme_options:
        st.session_state.q_theme_filter = "All"

    theme_filter = st.sidebar.selectbox(
        "Filter by theme",
        options=theme_options,
        key="q_theme_filter",
    )

    # Checkbox: show all questions for theme (ignore date)
    show_all_for_theme = False
    if theme_filter != "All":
        show_all_for_theme = st.sidebar.checkbox(
            "Show all dates for this theme",
            key="q_show_all_dates",
        )

    # Build query params
    selected_theme_id = theme_id_map.get(theme_filter) if theme_filter != "All" else None
    query_date = None if (theme_filter != "All" and show_all_for_theme) else selected_date

    with get_db() as db:
        question_repo = QuestionRepository(db)
        questions = question_repo.get_questions_by_date(
            target_date=query_date,
            question_type=type_filter if type_filter != "All" else None,
            theme_id=selected_theme_id,
        )

    # Update pattern filter options dynamically
    patterns = sorted(set(q.get("question_pattern") or "Other" for q in questions))
    if patterns and len(patterns) > 1:
        # Re-render would need rerun, so just show count per pattern
        pass

    if not questions:
        st.info(f"No questions found for {selected_date.strftime('%d %b %Y')}.")
    else:
        # Selection counter
        selected = st.session_state.selected_questions
        num_selected = len(selected)

        if num_selected == 10:
            st.success(f"**{num_selected}/10 questions selected** - Ready to save!")
        elif num_selected > 10:
            st.warning(f"**{num_selected}/10 questions selected** - Please deselect {num_selected - 10} question(s)")
        else:
            st.info(f"**{num_selected}/10 questions selected** - Select {10 - num_selected} more")

        # Save and clear buttons
        col_save, col_clear = st.columns([1, 1])
        with col_save:
            if st.button(
                "Save Selected Questions",
                disabled=num_selected != 10,
                use_container_width=True,
                type="primary",
            ):
                st.warning("Save logic not yet implemented. Please implement the save function.")
        with col_clear:
            if st.button("Clear Selection", use_container_width=True):
                st.session_state.selected_questions = set()
                st.rerun()

        st.markdown("---")

        # Group questions by pattern
        questions_by_pattern = {}
        for q in questions:
            pattern = q.get("question_pattern") or "Other"
            if pattern not in questions_by_pattern:
                questions_by_pattern[pattern] = []
            questions_by_pattern[pattern].append(q)

        for pattern, q_list in questions_by_pattern.items():
            st.markdown(f"### {pattern} ({len(q_list)} questions)")

            for i, q in enumerate(q_list):
                q_id = str(q["question_id"])
                is_selected = q_id in selected
                question_text = q.get("question_text") or ""
                edit_q_key = f"edit_dq_{q_id}"

                with st.container(border=True):
                    # Header row: checkbox + theme + article + edit button
                    col_check, col_info, col_edit = st.columns([0.5, 8.5, 1])

                    with col_check:
                        st.checkbox(
                            "sel",
                            value=is_selected,
                            key=f"sel_{q_id}",
                            on_change=toggle_question,
                            args=(q_id,),
                            label_visibility="collapsed",
                        )

                    with col_info:
                        theme_name = q.get("theme_name") or "No theme"
                        article_heading = q.get("article_heading") or "Unknown article"
                        st.markdown(f"**Theme:** {theme_name} &nbsp;|&nbsp; **Article:** {article_heading}")

                    with col_edit:
                        if st.button("Edit", key=f"btn_edit_dq_{q_id}"):
                            st.session_state[edit_q_key] = not st.session_state.get(edit_q_key, False)
                            st.rerun()

                    # Question text
                    if question_text:
                        st.markdown(f"**Q{i+1}.** {question_text}")

                    # Metadata row
                    meta_cols = st.columns(3)
                    with meta_cols[0]:
                        if q.get("question_pattern"):
                            st.caption(f"Pattern: {q['question_pattern']}")
                    with meta_cols[1]:
                        if q.get("is_multi_select"):
                            st.caption("Multi-select: Yes")
                    with meta_cols[2]:
                        if q.get("silly_mistake_prone"):
                            st.caption("Silly mistake prone")

                    # Options
                    options = q.get("options")
                    if options:
                        with st.expander("Options", expanded=False):
                            if isinstance(options, list):
                                for opt in options:
                                    if isinstance(opt, dict):
                                        opt_id = opt.get('id', '')
                                        opt_text = opt.get('text', opt.get('value', str(opt)))
                                        is_correct = str(opt_id) in [str(c) for c in (q.get("correct_option_ids") or [])]
                                        marker = " ✓" if is_correct else ""
                                        st.markdown(f"- {opt_text}{marker}")
                                    else:
                                        st.markdown(f"- {opt}")
                            elif isinstance(options, dict):
                                for key, val in options.items():
                                    st.markdown(f"- **{key}**: {val}")

                    # Explanation
                    explanation = q.get("explanation")
                    if explanation:
                        with st.expander("Explanation", expanded=False):
                            if isinstance(explanation, dict):
                                st.markdown(get_english_text(explanation))
                            else:
                                st.markdown(str(explanation))

                    # Edit mode
                    if st.session_state.get(edit_q_key, False):
                        st.markdown("---")
                        st.markdown("**Edit Question:**")

                        new_question_text = st.text_area(
                            "Question Text",
                            value=question_text,
                            height=100,
                            key=f"dq_text_{q_id}"
                        )

                        col_save_q, col_cancel_q = st.columns(2)
                        with col_save_q:
                            if st.button("Save Changes", key=f"save_dq_{q_id}", type="primary"):
                                updates = {}
                                if new_question_text != question_text:
                                    updates["question_text"] = new_question_text

                                if updates:
                                    result = content_service.update_question(UUID(q_id), updates)
                                    if result["success"]:
                                        st.session_state[edit_q_key] = False
                                        set_success("Question updated!")
                                        st.rerun()
                                else:
                                    st.info("No changes to save")
                        with col_cancel_q:
                            if st.button("Cancel", key=f"cancel_dq_{q_id}"):
                                st.session_state[edit_q_key] = False
                                st.rerun()

except Exception as e:
    st.error(f"Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
