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
                    tabs = st.tabs(["Pointed Analysis", "Mains Analysis", "Prelims Info"])

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
            else:
                st.info("👈 Select an article from the list to edit")

except Exception as e:
    st.error(f"Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
