import streamlit as st

from entities.features import Feature


class FeatureFilters:
    def __init__(self):
        #  - If app is run for the first time, initialize the filters
        #  - If app is rerun after user clears form, reset the state of the filters
        if "reset_filters_on_init" not in st.session_state:
            st.session_state.reset_filters_on_init = False
        if (
            st.session_state.reset_filters_on_init
            or "name_filter" not in st.session_state
        ):
            st.session_state.name_filter = ""
        if (
            st.session_state.reset_filters_on_init
            or "table_filter" not in st.session_state
        ):
            st.session_state.table_filter = ""
        if (
            st.session_state.reset_filters_on_init
            or "description_filter" not in st.session_state
        ):
            st.session_state.description_filter = ""
        st.session_state.reset_filters_on_init = False

    @staticmethod
    def substring_match(haystack: str, needle: str) -> bool:
        """Check if 'needle' can be found in 'haystack', ignoring case."""
        return not needle or needle.lower() in haystack.lower()

    def clear(self):
        # User hit clear for. Filters should be clear when app is rerun
        st.session_state.reset_filters_on_init = True
        st.rerun()

    def enabled(self):
        return bool(
            st.session_state.name_filter
            or st.session_state.table_filter
            or st.session_state.description_filter
        )

    def include(self, feature: Feature) -> bool:
        """Check if feature should be included based on filters."""
        return (
            self.substring_match(feature.name, st.session_state.name_filter)
            and self.substring_match(
                feature.table.name(), st.session_state.table_filter
            )
            and self.substring_match(
                feature.description() or "", st.session_state.description_filter
            )
        )
