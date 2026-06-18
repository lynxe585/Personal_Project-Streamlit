import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(page_title="Test Pyvis Comp")

# 1. Provide mock Pyvis HTML
pyvis_html = """
<html>
<head>
    <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet" type="text/css" />
    <style type="text/css">
        #mynetwork { width: 100%; height: 600px; border: 1px solid lightgray; }
    </style>
</head>
<body>
<div id="mynetwork"></div>

<script type="text/javascript">
    // create an array with nodes
    var nodes = new vis.DataSet([
        {id: 1, label: 'Node 1'},
        {id: 2, label: 'Node 2'},
        {id: 3, label: 'Node 3'},
        {id: 4, label: 'Node 4'},
        {id: 5, label: 'Node 5'}
    ]);

    // create an array with edges
    var edges = new vis.DataSet([
        {from: 1, to: 3},
        {from: 1, to: 2},
        {from: 2, to: 4},
        {from: 2, to: 5}
    ]);

    // create a network
    var container = document.getElementById('mynetwork');
    var data = { nodes: nodes, edges: edges };
    var options = {};
    var network = new vis.Network(container, data, options);

    // INJECTED CLICK HANDLER: send pyvis_click to parent
    network.on("click", function(params) {
        if (params.nodes.length > 0) {
            window.parent.postMessage({
                type: 'pyvis_click', 
                node: params.nodes[0]
            }, '*');
        }
    });
</script>
</body>
</html>
"""

st.write("### Test Component Interaction")

# 2. Declare and use component
pyvis_comp = components.declare_component(
    "pyvis_comp",
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pyvis_comp')
)

clicked_node = pyvis_comp(html=pyvis_html, key="test_pyvis")

if clicked_node:
    st.success(f"Successfully received click on: {clicked_node}")
else:
    st.info("Click a node in the graph below to test...")
