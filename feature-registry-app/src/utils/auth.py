import streamlit as st

def get_user_access_token():
    if "user_access_token" not in st.session_state:
        # The token is sent in header as x-forwarded-access-token by Databricks when the app is deployed to a Databricks workspace.
        st.session_state.user_access_token = st.context.headers.get('x-forwarded-access-token')
        if not st.session_state.user_access_token:
            st.error("The app must be deployed to a Databricks workspace. Refer to the Databricks documentation for custom app deployment.")
            st.stop()
    return st.session_state.user_access_token
