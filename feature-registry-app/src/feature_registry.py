import streamlit as st

pages = [st.Page("navigator/explore/features.py", title="Features")]

pg = st.navigation(pages=pages)
pg.run()
