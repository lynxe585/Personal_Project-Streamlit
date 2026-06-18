"""Minimal test: can a components.html iframe navigate the parent via query params?"""
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Iframe Nav Test", layout="wide")

# Read query params BEFORE any widgets
qp = st.query_params
if "test_node" in qp:
    node = qp["test_node"]
    st.query_params.clear()
    st.success(f"✅ SUCCESS! Received click: **{node}**")
else:
    st.info("Click a button below to test iframe → parent navigation")

# Test 1: Direct location assignment
test_html = """
<div style="background:#1e1e2e; padding:20px; border-radius:8px; color:#cdd6f4; font-family:monospace;">
    <h3 style="color:#89b4fa;">🧪 Iframe Navigation Test</h3>
    <div id="status" style="margin:10px 0; color:#f9e2af;">Waiting for click...</div>
    <button onclick="testNav()" style="padding:10px 20px; background:#89b4fa; border:none; border-radius:6px; cursor:pointer; font-size:16px;">
        Click to navigate parent
    </button>
    <script>
        function testNav() {
            var status = document.getElementById('status');
            try {
                status.textContent = 'Attempting: window.parent.location = ...';
                window.parent.location = '/?test_node=TEST_SUCCESS';
            } catch(e) {
                status.textContent = 'ERROR: ' + e.message;
                status.style.color = '#f38ba8';
                console.error('Navigation failed:', e);
            }
        }
    </script>
</div>
"""
components.html(test_html, height=200)
