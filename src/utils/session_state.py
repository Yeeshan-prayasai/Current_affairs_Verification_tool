import streamlit as st
from datetime import datetime, timedelta


def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        # Filters
        "date_filter_start": datetime.now().date() - timedelta(days=30),
        "date_filter_end": datetime.now().date(),
        "search_query": "",
        # Current selections
        "selected_theme_id": None,
        "selected_article_id": None,
        "selected_keyword_id": None,
        # Pagination
        "current_page": 1,
        "page_size": 20,
        # Messages
        "success_message": None,
        "error_message": None,
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def clear_messages():
    """Clear any flash messages."""
    st.session_state.success_message = None
    st.session_state.error_message = None


def show_messages():
    """Display any pending messages."""
    if st.session_state.get("success_message"):
        st.success(st.session_state.success_message)
        st.session_state.success_message = None

    if st.session_state.get("error_message"):
        st.error(st.session_state.error_message)
        st.session_state.error_message = None


def set_success(message: str):
    """Set a success message to display."""
    st.session_state.success_message = message


def set_error(message: str):
    """Set an error message to display."""
    st.session_state.error_message = message


def reset_pagination():
    """Reset pagination to first page."""
    st.session_state.current_page = 1
