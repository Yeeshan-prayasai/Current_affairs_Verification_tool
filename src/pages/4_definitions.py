import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from uuid import UUID
from src.config import settings
from src.utils.session_state import init_session_state, show_messages, set_success
from src.database.connection import get_db
from src.database.repositories.glossary_repo import GlossaryRepository
from src.services.verification_service import ContentService
from src.components.sidebar import render_sidebar_filters, render_pagination

st.set_page_config(
    page_title=f"Definitions - {settings.APP_NAME}",
    page_icon="📖",
    layout="wide",
)

init_session_state()
show_messages()

st.title("📖 Definition Review")
st.markdown("Edit glossary definitions (~30 words each)")
st.markdown("---")

# Sidebar filters
filters = render_sidebar_filters()

# Service
content_service = ContentService()

try:
    with get_db() as db:
        glossary_repo = GlossaryRepository(db)

        definitions = glossary_repo.get_all_keywords(
            search=filters["search"],
            limit=settings.DEFAULT_PAGE_SIZE,
            offset=(st.session_state.current_page - 1) * settings.DEFAULT_PAGE_SIZE,
        )

        total_definitions = glossary_repo.get_keyword_count(search=filters["search"])

    # Pagination
    render_pagination(total_definitions, settings.DEFAULT_PAGE_SIZE)

    if not definitions:
        st.info("No definitions found.")
    else:
        # Two columns layout
        col_list, col_detail = st.columns([1, 2])

        with col_list:
            st.markdown("### Keywords")
            for defn in definitions:
                word_count = len((defn.get("definition") or "").split())
                label = f"**{defn['keyword']}** ({word_count} words)\n{defn['article_count']} articles"
                if st.button(label, key=f"def_{defn['id']}", use_container_width=True):
                    st.session_state.selected_keyword_id = str(defn["id"])
                    st.rerun()

        with col_detail:
            selected_id = st.session_state.get("selected_keyword_id")

            if selected_id:
                with get_db() as db:
                    glossary_repo = GlossaryRepository(db)
                    keyword_data = glossary_repo.get_keyword_with_articles(UUID(selected_id))

                    if keyword_data:
                        keyword = keyword_data["keyword"]
                        articles = keyword_data["articles"]

                        # Extract values while session is open
                        keyword_name = keyword.keyword
                        keyword_definition = keyword.definition or ""
                        keyword_created_at = keyword.created_at

                        # Extract article data
                        article_list = [
                            {
                                "id": a.id,
                                "heading": a.title,
                                "date": a.date
                            }
                            for a in articles
                        ]

                if keyword_data:
                    st.subheader(f"Keyword: {keyword_name}")
                    st.caption(f"Used in {len(article_list)} articles | Created: {keyword_created_at.strftime('%Y-%m-%d') if keyword_created_at else 'N/A'}")

                    # Edit keyword name - use dynamic key based on selected_id
                    new_keyword_name = st.text_input("Keyword", value=keyword_name, key=f"edit_keyword_name_{selected_id}")

                    # Edit definition - use dynamic key based on selected_id
                    st.markdown("### Definition")
                    new_definition = st.text_area(
                        "Definition (~30 words recommended)",
                        value=keyword_definition,
                        height=150,
                        key=f"edit_definition_{selected_id}",
                    )

                    # Word count
                    word_count = len(new_definition.split()) if new_definition else 0
                    if word_count < 15:
                        st.warning(f"Word count: {word_count} (too short)")
                    elif word_count > 50:
                        st.warning(f"Word count: {word_count} (too long)")
                    else:
                        st.success(f"Word count: {word_count}")

                    # Save button
                    if st.button("💾 Save Changes", type="primary", key=f"save_definition_{selected_id}"):
                        if new_keyword_name != keyword_name:
                            result = content_service.update_keyword(
                                UUID(selected_id), new_keyword_name, new_definition
                            )
                        else:
                            result = content_service.update_definition(UUID(selected_id), new_definition)

                        if result["success"]:
                            set_success("Definition saved!")
                            st.rerun()

                    # Articles using this keyword
                    st.markdown("---")
                    st.markdown("### Articles Using This Keyword")
                    if article_list:
                        for article in article_list[:10]:
                            col_article, col_link = st.columns([5, 1])
                            with col_article:
                                date_str = article['date'].strftime('%Y-%m-%d') if article['date'] else 'N/A'
                                st.markdown(f"**{article['heading'][:60]}{'...' if len(article['heading']) > 60 else ''}** ({date_str})")
                            with col_link:
                                if st.button("View →", key=f"view_article_{article['id']}_{selected_id}"):
                                    st.session_state.selected_article_id = article['id']
                                    st.switch_page("pages/3_articles.py")
                        if len(article_list) > 10:
                            st.caption(f"... and {len(article_list) - 10} more")
                    else:
                        st.info("No articles use this keyword")
            else:
                st.info("👈 Select a keyword from the list to edit")

except Exception as e:
    st.error(f"Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
