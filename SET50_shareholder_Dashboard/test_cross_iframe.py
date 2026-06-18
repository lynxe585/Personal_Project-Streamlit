import streamlit as st
import streamlit.components.v1 as components
import os

listener_dir = 'click_listener'
os.makedirs(listener_dir, exist_ok=True)
listener_html = """
<html>
<body>
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
        sendMessageToStreamlitClient('streamlit:setFrameHeight', {height: 0});
    }

    window.parent.addEventListener('message', function(event) {
        if (event.data && event.data.type === 'pyvis_click') {
            sendMessageToStreamlitClient('streamlit:setComponentValue', {value: event.data.node});
        }
    });

    init();
</script>
</body>
</html>
"""
with open(os.path.join(listener_dir, 'index.html'), 'w') as f:
    f.write(listener_html)

st.write("Test cross-iframe communication")

listener = components.declare_component("click_listener", path=listener_dir)
clicked_node = listener(key="pyvis_listener")
st.write(f"Clicked Node: {clicked_node}")

sender_html = """
<button onclick="window.parent.postMessage({type: 'pyvis_click', node: 'TestNode'}, '*');">Send Click</button>
"""
components.html(sender_html, height=100)
