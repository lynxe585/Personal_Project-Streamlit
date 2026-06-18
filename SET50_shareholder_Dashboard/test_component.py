import streamlit as st
import streamlit.components.v1 as components
import os

component_dir = 'pyvis_component'
os.makedirs(component_dir, exist_ok=True)
html_content = """
<html>
<body>
<h1>Hello World</h1>
<button onclick="sendVal('Node_A')">Click Node A</button>
<button onclick="sendVal('Node_B')">Click Node B</button>
<script>
    function sendMessageToStreamlitClient(type, data) {
        var outData = Object.assign({
            isStreamlitMessage: true,
            type: type,
        }, data);
        window.parent.postMessage(outData, '*');
    }
    function init() {
        sendMessageToStreamlitClient('streamlit:componentReady', {apiVersion: 1});
        sendMessageToStreamlitClient('streamlit:setFrameHeight', {height: 200});
    }
    function sendVal(val) {
        sendMessageToStreamlitClient('streamlit:setComponentValue', {value: val});
    }
    init();
</script>
</body>
</html>
"""
with open(os.path.join(component_dir, 'index.html'), 'w') as f:
    f.write(html_content)

test_comp = components.declare_component("test_comp", path=component_dir)
val = test_comp(key="test")
st.write(f"Received from JS: {val}")
