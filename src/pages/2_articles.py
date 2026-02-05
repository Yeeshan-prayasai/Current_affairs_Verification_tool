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
                label = f"**{article['heading'][:50]}...**\n{article.get('theme_name', 'No theme')} | {article['date'].strftime('%Y-%m-%d') if article.get('date') else 'N/A'}"
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
                        article_news_paper = article.news_paper
                        article_read_time = article.read_time
                        article_theme_id = article.theme_id
                        article_description = article.description or ""
                        article_pointed_analysis = article.pointed_analysis or ""
                        article_mains_analysis = article.mains_analysis or ""
                        article_prelims_info = article.prelims_info or ""
                        article_mains_subject = article.mains_subject or ""
                        article_prelims_subject = article.prelims_subject or ""
                        article_secondary_tag = article.secondary_tag or ""
                        article_sub_topics = article.sub_topics or ""
                        article_current_affair_id = article.current_affair_id

                        # Get keywords while session is open
                        keywords = glossary_repo.get_keywords_for_article(article_current_affair_id)

                if article:
                    st.subheader(article_heading[:80] + "..." if len(article_heading or "") > 80 else article_heading)

                    # Metadata
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.caption(f"Date: {article_date.strftime('%Y-%m-%d') if article_date else 'N/A'}")
                    with col2:
                        st.caption(f"Source: {article_news_paper or 'N/A'}")
                    with col3:
                        st.caption(f"Read Time: {article_read_time or 'N/A'} min")

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

                    # Editable content
                    tabs = st.tabs(["Description", "Pointed Analysis", "Mains Analysis", "Prelims Info", "Classification"])

                    with tabs[0]:
                        description = st.text_area("Description", value=article_description, height=200, key="desc")

                    with tabs[1]:
                        pointed_analysis = st.text_area("Pointed Analysis", value=article_pointed_analysis, height=200, key="pointed")

                    with tabs[2]:
                        mains_analysis = st.text_area("Mains Analysis", value=article_mains_analysis, height=200, key="mains")

                    with tabs[3]:
                        prelims_info = st.text_area("Prelims Info", value=article_prelims_info, height=200, key="prelims")

                    with tabs[4]:
                        col1, col2 = st.columns(2)
                        with col1:
                            mains_subject = st.text_input("Mains Subject", value=article_mains_subject, key="mains_subj")
                            prelims_subject = st.text_input("Prelims Subject", value=article_prelims_subject, key="prelims_subj")
                        with col2:
                            secondary_tag = st.text_input("Secondary Tag", value=article_secondary_tag, key="sec_tag")
                            sub_topics = st.text_input("Sub Topics", value=article_sub_topics, key="sub_topics")

                    # Save button
                    st.markdown("---")
                    if st.button("💾 Save Changes", type="primary", key="save_article"):
                        updates = {
                            "description": description,
                            "pointed_analysis": pointed_analysis,
                            "mains_analysis": mains_analysis,
                            "prelims_info": prelims_info,
                            "mains_subject": mains_subject,
                            "prelims_subject": prelims_subject,
                            "secondary_tag": secondary_tag,
                            "sub_topics": sub_topics,
                            "theme_id": new_theme_id,
                        }
                        result = content_service.update_article(selected_id, updates)
                        if result["success"]:
                            set_success("Article saved!")
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
