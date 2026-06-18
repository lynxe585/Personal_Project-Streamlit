import streamlit as st
import streamlit.components.v1 as components
import networkx as nx
from pyvis.network import Network
import tempfile
import os

st.write('Testing Pyvis click')

# Listener
listener_dir = 'click_listener'
if os.path.exists(listener_dir):
    comp = components.declare_component('click_listener', path=listener_dir)
    res = comp(key='test')
    st.write('Clicked:', res)

G = nx.Graph()
G.add_node('ADVANC')
net = Network(height='400px', width='100%')
net.from_nx(G)

f = tempfile.NamedTemporaryFile(suffix='.html', delete=False)
net.save_graph(f.name)
f.close()

with open(f.name, 'r') as file:
    html = file.read()
os.unlink(f.name)

script = '''
<script>
console.log('Injected script running. Network typeof:', typeof network);
if (typeof network !== 'undefined') {
    network.on('click', function (params) {
        console.log('Clicked!', params);
        var nodeId = '';
        if (params.nodes.length > 0) {
            nodeId = params.nodes[0];
        }
        window.parent.postMessage({type: 'pyvis_click', node: nodeId}, '*');
    });
}
</script>
'''
html = html.replace('</body>', script + '</body>')
components.html(html, height=400)
