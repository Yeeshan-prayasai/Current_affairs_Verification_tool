import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from uuid import UUID
from src.config import settings
from src.utils.session_state import init_session_state, show_messages, set_success
from src.database.connection import get_db
from src.database.repositories.article_repo import ArticleRepository
from src.database.repositories.theme_repo import ThemeRepository
from src.database.repositories.glossary_repo import GlossaryRepository
from src.database.repositories.question_repo import QuestionRepository
from src.database.repositories.timeline_repo import TimelineRepository
from src.services.verification_service import ContentService
from src.components.sidebar import render_sidebar_filters, render_pagination

st.set_page_config(
    page_title=f"Articles - {settings.APP_NAME}",
    page_icon="📰",
    layout="wide",
)

init_session_state()
show_messages()

st.title("📰 Article Review")
st.markdown("Edit article content and analysis")
st.markdown("---")

# Sidebar filters
filters = render_sidebar_filters()

# Service
content_service = ContentService()

try:
    with get_db() as db:
        article_repo = ArticleRepository(db)
        theme_repo = ThemeRepository(db)

        articles = article_repo.get_articles(
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            search=filters["search"],
            limit=settings.DEFAULT_PAGE_SIZE,
            offset=(st.session_state.current_page - 1) * settings.DEFAULT_PAGE_SIZE,
        )

        total_articles = article_repo.get_article_count(search=filters["search"])
        all_themes = theme_repo.get_all_themes(limit=500)

    # Pagination
    render_pagination(total_articles, settings.DEFAULT_PAGE_SIZE)

    if not articles:
        st.info("No articles found.")
    else:
        # Two columns layout
        col_list, col_detail = st.columns([1, 2])

        with col_list:
            st.markdown("### Articles")
            for article in articles:
                # Better article display - full heading with theme below
                heading = article['heading'] or "Untitled"
                theme_name = article.get('theme_name') or 'No theme'
                date_str = article['date'].strftime('%d %b') if article.get('date') else ''

                label = f"📄 **{heading}**\n🏷️ {theme_name} • {date_str}"
                if st.button(label, key=f"article_{article['id']}", use_container_width=True):
                    st.session_state.selected_article_id = article["id"]
                    st.rerun()

        with col_detail:
            selected_id = st.session_state.get("selected_article_id")

            if selected_id:
                with get_db() as db:
                    article_repo = ArticleRepository(db)
                    glossary_repo = GlossaryRepository(db)
                    question_repo = QuestionRepository(db)
                    timeline_repo = TimelineRepository(db)
                    article = article_repo.get_article_by_id(selected_id)

                    if article:
                        # Store values we need outside the session
                        article_heading = article.heading
                        article_date = article.date
                        article_theme_id = article.theme_id
                        article_pointed_analysis = article.pointed_analysis or ""
                        article_mains_analysis = article.mains_analysis or ""
                        article_prelims_info = article.prelims_info or ""
                        article_current_affair_id = article.current_affair_id

                        # Get keywords while session is open
                        keywords = glossary_repo.get_keywords_for_article(article_current_affair_id)

                        # Get questions while session is open
                        questions = question_repo.get_questions_for_article(article_current_affair_id)

                        # Get timeline for the article's theme
                        theme_timeline_content = None
                        if article_theme_id:
                            timeline = timeline_repo.get_timeline_by_theme_id(article_theme_id)
                            if timeline:
                                theme_timeline_content = timeline.timeline_content

                if article:
                    st.subheader(article_heading)
                    st.caption(f"Date: {article_date.strftime('%Y-%m-%d') if article_date else 'N/A'}")

                    st.markdown("---")

                    # Theme assignment
                    theme_names = ["None"] + [t["name"] for t in all_themes]
                    theme_ids = [None] + [t["id"] for t in all_themes]

                    current_idx = 0
                    if article_theme_id:
                        for i, tid in enumerate(theme_ids):
                            if tid == article_theme_id:
                                current_idx = i
                                break

                    selected_theme_idx = st.selectbox(
                        "Theme",
                        options=range(len(theme_names)),
                        format_func=lambda i: theme_names[i],
                        index=current_idx,
                        key="article_theme",
                    )
                    new_theme_id = theme_ids[selected_theme_idx]

                    # Editable content - tabs with markdown preview and collapsible edit
                    tabs = st.tabs(["Pointed Analysis", "Mains Analysis", "Prelims Info", "Timeline Summary"])

                    # Track edit state for each field
                    edit_pointed_key = f"edit_pointed_{selected_id}"
                    edit_mains_key = f"edit_mains_{selected_id}"
                    edit_prelims_key = f"edit_prelims_{selected_id}"

                    with tabs[0]:
                        st.markdown(article_pointed_analysis)
                        if st.button("✏️ Edit", key="btn_edit_pointed"):
                            st.session_state[edit_pointed_key] = not st.session_state.get(edit_pointed_key, False)
                            st.rerun()
                        if st.session_state.get(edit_pointed_key, False):
                            pointed_analysis = st.text_area("Edit Pointed Analysis", value=article_pointed_analysis, height=200, key="pointed", label_visibility="collapsed")
                            if st.button("💾 Save Pointed", key="save_pointed"):
                                updates = {"pointed_analysis": pointed_analysis, "theme_id": new_theme_id}
                                result = content_service.update_article(selected_id, updates)
                                if result["success"]:
                                    st.session_state[edit_pointed_key] = False
                                    set_success("Pointed Analysis saved!")
                                    st.rerun()

                    with tabs[1]:
                        st.markdown(article_mains_analysis)
                        if st.button("✏️ Edit", key="btn_edit_mains"):
                            st.session_state[edit_mains_key] = not st.session_state.get(edit_mains_key, False)
                            st.rerun()
                        if st.session_state.get(edit_mains_key, False):
                            mains_analysis = st.text_area("Edit Mains Analysis", value=article_mains_analysis, height=200, key="mains", label_visibility="collapsed")
                            if st.button("💾 Save Mains", key="save_mains"):
                                updates = {"mains_analysis": mains_analysis, "theme_id": new_theme_id}
                                result = content_service.update_article(selected_id, updates)
                                if result["success"]:
                                    st.session_state[edit_mains_key] = False
                                    set_success("Mains Analysis saved!")
                                    st.rerun()

                    with tabs[2]:
                        st.markdown(article_prelims_info)
                        if st.button("✏️ Edit", key="btn_edit_prelims"):
                            st.session_state[edit_prelims_key] = not st.session_state.get(edit_prelims_key, False)
                            st.rerun()
                        if st.session_state.get(edit_prelims_key, False):
                            prelims_info = st.text_area("Edit Prelims Info", value=article_prelims_info, height=200, key="prelims", label_visibility="collapsed")
                            if st.button("💾 Save Prelims", key="save_prelims"):
                                updates = {"prelims_info": prelims_info, "theme_id": new_theme_id}
                                result = content_service.update_article(selected_id, updates)
                                if result["success"]:
                                    st.session_state[edit_prelims_key] = False
                                    set_success("Prelims Info saved!")
                                    st.rerun()

                    with tabs[3]:
                        # Timeline Summary - fetched from theme_timelines table
                        if theme_timeline_content:
                            st.markdown(theme_timeline_content)
                        else:
                            st.info("No timeline available for this theme")

                    # Keywords section
                    st.markdown("---")
                    st.markdown("### Keywords")

                    if keywords:
                        for kw in keywords:
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.write(f"**{kw['keyword']}**: {kw['definition'][:80] if kw.get('definition') else 'No definition'}...")
                            with col2:
                                if st.button("Remove", key=f"rm_kw_{kw['id']}"):
                                    content_service.remove_keyword_from_article(article_current_affair_id, kw["id"])
                                    st.rerun()
                    else:
                        st.info("No keywords linked to this article")

                    # Questions section
                    st.markdown("---")
                    st.markdown(f"### Questions ({len(questions)})")

                    # Helper function to extract English text from bilingual content
                    def get_english_text(content):
                        """Extract English text from content that may have hindi/english keys."""
                        if content is None:
                            return ""
                        if isinstance(content, dict):
                            # Check for 'english' key first
                            if "english" in content:
                                return str(content["english"])
                            # Check for 'text' key
                            if "text" in content:
                                return str(content["text"])
                            # Return the dict as string if no known keys
                            return str(content)
                        return str(content)

                    def get_english_options(options):
                        """Extract English options from bilingual options."""
                        if options is None:
                            return None
                        if isinstance(options, dict):
                            # Check if it has 'english' key with options inside
                            if "english" in options:
                                return options["english"]
                            # Otherwise return as-is
                            return options
                        if isinstance(options, list):
                            # Check if list items have 'english' key
                            result = []
                            for opt in options:
                                if isinstance(opt, dict) and "english" in opt:
                                    result.append(opt["english"])
                                else:
                                    result.append(opt)
                            return result
                        return options

                    if questions:
                        # Group questions by type
                        questions_by_type = {}
                        for q in questions:
                            q_type = q.get("type") or "Other"
                            if q_type not in questions_by_type:
                                questions_by_type[q_type] = []
                            questions_by_type[q_type].append(q)

                        for q_type, q_list in questions_by_type.items():
                            with st.expander(f"**{q_type}** ({len(q_list)} questions)", expanded=False):
                                for i, q in enumerate(q_list):
                                    q_id = q.get("question_id")
                                    edit_q_key = f"edit_q_{q_id}"

                                    col_q, col_edit = st.columns([6, 1])
                                    with col_q:
                                        st.markdown(f"**Q{i+1}.**")
                                    with col_edit:
                                        if st.button("✏️", key=f"btn_edit_q_{q_id}"):
                                            st.session_state[edit_q_key] = not st.session_state.get(edit_q_key, False)
                                            st.rerun()

                                    # Display question content (English only)
                                    question_text = get_english_text(q.get("question"))
                                    if question_text:
                                        st.markdown(question_text)

                                    # Show key metadata in columns
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        if q.get("paper"):
                                            st.caption(f"Paper: {q['paper']}")
                                        if q.get("subject"):
                                            st.caption(f"Subject: {q['subject']}")
                                    with col2:
                                        if q.get("difficulty"):
                                            st.caption(f"Difficulty: {q['difficulty']}")
                                        if q.get("max_score"):
                                            st.caption(f"Max Score: {q['max_score']}")
                                    with col3:
                                        if q.get("word_count"):
                                            st.caption(f"Word Count: {q['word_count']}")
                                        if q.get("duration"):
                                            st.caption(f"Duration: {q['duration']} min")

                                    # Options for MCQ (English only)
                                    options = get_english_options(q.get("options"))
                                    if options:
                                        st.markdown("**Options:**")
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
                                        st.markdown(f"**Correct Answer:** {answer} {value}".strip())

                                    # Model answer in expander (English only)
                                    model_answer = get_english_text(q.get("model_answer"))
                                    if model_answer:
                                        with st.expander("Model Answer", expanded=False):
                                            st.markdown(model_answer)

                                    # Explanation (English only)
                                    explanation = get_english_text(q.get("explanation"))
                                    if explanation:
                                        with st.expander("Explanation", expanded=False):
                                            st.markdown(explanation)

                                    # Topics
                                    if q.get("topics"):
                                        topics = q["topics"]
                                        if isinstance(topics, list):
                                            topics_str = ", ".join(str(t) for t in topics)
                                        else:
                                            topics_str = str(topics)
                                        st.caption(f"Topics: {topics_str}")

                                    # Hints (English only)
                                    if q.get("hints"):
                                        hints = q["hints"]
                                        with st.expander("Hints", expanded=False):
                                            if isinstance(hints, list):
                                                for hint in hints:
                                                    hint_text = get_english_text(hint)
                                                    st.markdown(f"- {hint_text}")
                                            else:
                                                st.markdown(get_english_text(hints))

                                    # Edit mode
                                    if st.session_state.get(edit_q_key, False):
                                        st.markdown("---")
                                        st.markdown("**Edit Question:**")

                                        # Editable fields
                                        new_correct_option = st.text_input(
                                            "Correct Option",
                                            value=q.get("correct_option") or "",
                                            key=f"q_correct_opt_{q_id}"
                                        )
                                        new_difficulty = st.selectbox(
                                            "Difficulty",
                                            options=["easy", "medium", "hard"],
                                            index=["easy", "medium", "hard"].index(q.get("difficulty")) if q.get("difficulty") in ["easy", "medium", "hard"] else 1,
                                            key=f"q_difficulty_{q_id}"
                                        )
                                        new_status = st.selectbox(
                                            "Status",
                                            options=["draft", "review", "approved", "rejected"],
                                            index=["draft", "review", "approved", "rejected"].index(q.get("status")) if q.get("status") in ["draft", "review", "approved", "rejected"] else 0,
                                            key=f"q_status_{q_id}"
                                        )

                                        if st.button("💾 Save Question", key=f"save_q_{q_id}"):
                                            updates = {
                                                "correct_option": new_correct_option,
                                                "difficulty": new_difficulty,
                                                "status": new_status,
                                            }
                                            result = content_service.update_question(q_id, updates)
                                            if result["success"]:
                                                st.session_state[edit_q_key] = False
                                                set_success("Question updated!")
                                                st.rerun()

                                    if i < len(q_list) - 1:
                                        st.markdown("---")
                    else:
                        st.info("No questions linked to this article")
            else:
                st.info("👈 Select an article from the list to edit")

except Exception as e:
    st.error(f"Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
