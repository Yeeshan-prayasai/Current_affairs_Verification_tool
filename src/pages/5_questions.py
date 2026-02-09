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

# Type filter - use widget key directly
if "q_type_filter" not in st.session_state:
    st.session_state.q_type_filter = "All"

type_filter = st.sidebar.selectbox(
    "Filter by type",
    options=["All", "mains", "prelims"],
    key="q_type_filter"
)

# Initialize selected questions in session state
if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = set()

# Service
content_service = ContentService()


# Helper functions for bilingual content
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


def get_english_options(options):
    """Extract English options from bilingual options."""
    if options is None:
        return None
    if isinstance(options, dict):
        if "english" in options:
            return options["english"]
        return options
    if isinstance(options, list):
        result = []
        for opt in options:
            if isinstance(opt, dict) and "english" in opt:
                result.append(opt["english"])
            else:
                result.append(opt)
        return result
    return options


# Callback for checkbox toggle - no rerun needed, Streamlit handles it
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
                # Placeholder - user will implement save logic
                st.warning("Save logic not yet implemented. Please implement the save function.")
        with col_clear:
            if st.button("Clear Selection", use_container_width=True):
                st.session_state.selected_questions = set()
                st.rerun()

        st.markdown("---")

        # Group questions by type
        questions_by_type = {}
        for q in questions:
            q_type = q.get("type") or "Other"
            if q_type not in questions_by_type:
                questions_by_type[q_type] = []
            questions_by_type[q_type].append(q)

        for q_type, q_list in questions_by_type.items():
            st.markdown(f"### {q_type} ({len(q_list)} questions)")

            for i, q in enumerate(q_list):
                q_id = str(q["question_id"])
                is_selected = q_id in selected
                question_text = get_english_text(q.get("question"))
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
                    meta_cols = st.columns(5)
                    with meta_cols[0]:
                        if q.get("subject"):
                            st.caption(f"Subject: {q['subject']}")
                    with meta_cols[1]:
                        if q.get("difficulty"):
                            st.caption(f"Difficulty: {q['difficulty']}")
                    with meta_cols[2]:
                        if q.get("max_score"):
                            st.caption(f"Score: {q['max_score']}")
                    with meta_cols[3]:
                        if q.get("paper"):
                            st.caption(f"Paper: {q['paper']}")
                    with meta_cols[4]:
                        if q.get("word_count"):
                            st.caption(f"Words: {q['word_count']}")

                    # Options for MCQ
                    options = get_english_options(q.get("options"))
                    if options:
                        with st.expander("Options", expanded=False):
                            if isinstance(options, dict):
                                for key, val in options.items():
                                    st.markdown(f"- **{key}**: {val}")
                            elif isinstance(options, list):
                                for opt in options:
                                    if isinstance(opt, dict):
                                        label = opt.get('label', opt.get('key', ''))
                                        text = opt.get('text', opt.get('value', str(opt)))
                                        st.markdown(f"- **{label}**: {text}")
                                    else:
                                        st.markdown(f"- {opt}")

                    # Correct answer
                    if q.get("correct_option") or q.get("correct_value"):
                        answer = q.get('correct_option', '')
                        value = get_english_text(q.get('correct_value')) if q.get('correct_value') else ''
                        with st.expander("Answer", expanded=False):
                            st.markdown(f"**Correct Answer:** {answer} {value}".strip())

                    # Model answer
                    model_answer = get_english_text(q.get("model_answer"))
                    if model_answer:
                        with st.expander("Model Answer", expanded=False):
                            st.markdown(model_answer)

                    # Edit mode
                    if st.session_state.get(edit_q_key, False):
                        st.markdown("---")
                        st.markdown("**Edit Question:**")

                        new_question_text = st.text_area(
                            "Question Text (English)",
                            value=question_text,
                            height=100,
                            key=f"dq_text_{q_id}"
                        )

                        edit_cols = st.columns(3)
                        with edit_cols[0]:
                            new_correct_option = st.text_input(
                                "Correct Option",
                                value=q.get("correct_option") or "",
                                key=f"dq_correct_opt_{q_id}"
                            )
                        with edit_cols[1]:
                            diff_options = ["easy", "medium", "hard"]
                            current_diff = q.get("difficulty") or "medium"
                            new_difficulty = st.selectbox(
                                "Difficulty",
                                options=diff_options,
                                index=diff_options.index(current_diff) if current_diff in diff_options else 1,
                                key=f"dq_difficulty_{q_id}"
                            )
                        with edit_cols[2]:
                            status_options = ["draft", "review", "approved", "rejected"]
                            current_status = q.get("status") or "draft"
                            new_status = st.selectbox(
                                "Status",
                                options=status_options,
                                index=status_options.index(current_status) if current_status in status_options else 0,
                                key=f"dq_status_{q_id}"
                            )

                        edit_cols2 = st.columns(3)
                        with edit_cols2[0]:
                            new_subject = st.text_input(
                                "Subject",
                                value=q.get("subject") or "",
                                key=f"dq_subject_{q_id}"
                            )
                        with edit_cols2[1]:
                            new_max_score = st.number_input(
                                "Max Score",
                                value=float(q.get("max_score") or 0),
                                min_value=0.0,
                                step=0.5,
                                key=f"dq_score_{q_id}"
                            )
                        with edit_cols2[2]:
                            new_word_count = st.number_input(
                                "Word Count",
                                value=int(q.get("word_count") or 0),
                                min_value=0,
                                step=10,
                                key=f"dq_words_{q_id}"
                            )

                        col_save_q, col_cancel_q = st.columns(2)
                        with col_save_q:
                            if st.button("Save Changes", key=f"save_dq_{q_id}", type="primary"):
                                updates = {
                                    "correct_option": new_correct_option,
                                    "difficulty": new_difficulty,
                                    "status": new_status,
                                    "subject": new_subject,
                                    "max_score": new_max_score,
                                    "word_count": new_word_count,
                                }
                                # Update question text if changed
                                if new_question_text != question_text:
                                    original_q = q.get("question")
                                    if isinstance(original_q, dict) and "english" in original_q:
                                        original_q["english"] = new_question_text
                                        updates["question"] = original_q
                                    else:
                                        updates["question"] = {"english": new_question_text}

                                result = content_service.update_question(UUID(q_id), updates)
                                if result["success"]:
                                    st.session_state[edit_q_key] = False
                                    set_success("Question updated!")
                                    st.rerun()
                        with col_cancel_q:
                            if st.button("Cancel", key=f"cancel_dq_{q_id}"):
                                st.session_state[edit_q_key] = False
                                st.rerun()

except Exception as e:
    st.error(f"Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
