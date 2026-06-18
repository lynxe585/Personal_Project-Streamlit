import streamlit as st
import streamlit.components.v1 as components

st.write("Query params:", st.query_params)
html = """
<button onclick="
    window.parent.history.pushState(null, '', '?node=Hello');
    window.parent.location.reload();
">Click Me</button>
"""
components.html(html, height=100)
