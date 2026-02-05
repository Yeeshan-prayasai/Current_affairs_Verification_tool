import streamlit as st
from datetime import datetime, timedelta


def render_sidebar_filters():
    """Render common sidebar filters."""
    st.sidebar.header("Filters")

    # Quick filter buttons
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Today", use_container_width=True):
            st.session_state.show_all_dates = False
            st.session_state.today_filter = True
            st.session_state.current_page = 1
            st.rerun()
    with col2:
        if st.button("Show All", use_container_width=True):
            st.session_state.show_all_dates = True
            st.session_state.today_filter = False
            st.session_state.current_page = 1
            st.rerun()

    # Check filter states
    show_all = st.session_state.get("show_all_dates", False)
    today_filter = st.session_state.get("today_filter", False)

    # Date range
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "From",
            value=st.session_state.get(
                "date_filter_start", datetime.now().date() - timedelta(days=30)
            ),
            key="sidebar_start_date",
            disabled=show_all or today_filter,
        )
    with col2:
        end_date = st.date_input(
            "To",
            value=st.session_state.get("date_filter_end", datetime.now().date()),
            key="sidebar_end_date",
            disabled=show_all or today_filter,
        )

    # Status messages
    if show_all:
        st.sidebar.caption("Showing all dates")
    elif today_filter:
        st.sidebar.caption(f"Showing today: {datetime.now().date().strftime('%d %b %Y')}")

    # Reset button
    if show_all or today_filter:
        if st.sidebar.button("Reset Filters", use_container_width=True):
            st.session_state.show_all_dates = False
            st.session_state.today_filter = False
            st.session_state.current_page = 1
            st.rerun()

    # Update session state
    st.session_state.date_filter_start = start_date
    st.session_state.date_filter_end = end_date

    # Search
    search = st.sidebar.text_input(
        "Search",
        value=st.session_state.get("search_query", ""),
        placeholder="Search...",
        key="sidebar_search",
    )
    st.session_state.search_query = search

    # Determine actual date filters to return
    if show_all:
        return_start = None
        return_end = None
    elif today_filter:
        today = datetime.now().date()
        return_start = today
        return_end = today
    else:
        return_start = start_date
        return_end = end_date

    return {
        "start_date": return_start,
        "end_date": return_end,
        "search": search if search else None,
    }


def render_pagination(total_items: int, page_size: int = 20):
    """Render pagination controls."""
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    current_page = st.session_state.get("current_page", 1)

    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            if st.button("← Previous", disabled=current_page <= 1):
                st.session_state.current_page = current_page - 1
                st.rerun()

        with col2:
            st.markdown(
                f"<div style='text-align: center'>Page {current_page} of {total_pages}</div>",
                unsafe_allow_html=True,
            )

        with col3:
            if st.button("Next →", disabled=current_page >= total_pages):
                st.session_state.current_page = current_page + 1
                st.rerun()

    return current_page, page_size
