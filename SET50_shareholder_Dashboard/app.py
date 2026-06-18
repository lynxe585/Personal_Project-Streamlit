import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import pandas as pd
import os
import tempfile
from datetime import datetime

from data_fetcher import get_company_metadata, get_network_data, get_company_highlights

# ===========================
# PAGE CONFIG
# ===========================
st.set_page_config(page_title="SET50 Network", page_icon="🌐", layout="wide")

if "selected_node_key" not in st.session_state:
    st.session_state.selected_node_key = "-- Show All --"

# ===========================
# LOAD CSS
# ===========================
try:
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'style.css')
    with open(css_path, encoding='utf-8') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("style.css not found — running without custom styles.")

# ===========================
# SECTOR → COLOR MAP
# ===========================
SECTOR_COLORS = {
    'FINCIAL':  '#60a5fa',   # blue
    'BANK':     '#3b82f6',   # blue-indigo  (KKP, TCAP)
    'ENERG':    '#f59e0b',   # amber
    'ICT':      '#a78bfa',   # purple
    'TECH':     '#a78bfa',   # purple       (CCET industry=TECH)
    'ETRON':    '#c084fc',   # violet       (CCET sector)
    'FOOD':     '#34d399',   # emerald
    'PROPCON':  '#fb7185',   # rose
    'RESOURC':  '#fb923c',   # orange
    'HEALTH':   '#2dd4bf',   # teal
    'INSUR':    '#818cf8',   # indigo
    'TRANS':    '#facc15',   # yellow
    'CONMAT':   '#a3e635',   # lime
    'COMM':     '#f472b6',   # pink         (BJC)
    'FIN':      '#22d3ee',   # cyan         (TIDLOR)
    'Unknown':  '#94a3b8',   # slate (fallback)
}
SHAREHOLDER_COLOR = '#fbbf24'  # gold
DIRECTOR_COLOR    = '#38bdf8'  # sky blue

def node_color(node_type: str, sector: str = '') -> str:
    if node_type == 'Shareholder':
        return SHAREHOLDER_COLOR
    if node_type == 'Director':
        return DIRECTOR_COLOR
    return SECTOR_COLORS.get(sector, SECTOR_COLORS['Unknown'])

# ===========================
# SIDEBAR
# ===========================
st.sidebar.title("🌐 SET50 Stakeholder Network")
st.sidebar.markdown("Visualize relationships between Thailand's top 50 listed companies and their key stakeholders.")

st.sidebar.subheader("⚙️ Configuration")

# Language toggle
lang_label = st.sidebar.radio("Language / ภาษา", ["EN English", "TH ภาษาไทย"], horizontal=True)
lang = "en" if "English" in lang_label else "th"

mode = st.sidebar.selectbox(
    "Stakeholder Mode",
    [
        "Combined (3 Shareholders + 2 Directors)",
        "Major Shareholders (Top 5)",
        "Board of Directors (Top 5)",
    ],
)

# ===========================
# FETCH DATA
# ===========================
with st.spinner("🔄 Fetching live data from SET..."):
    metadata = get_company_metadata()
    edges_data, nodes_info = get_network_data(mode, lang=lang)

# Sector filter
all_sectors = sorted({m['sector'] for m in metadata.values()})
selected_sectors = st.sidebar.multiselect("Filter by Sector", all_sectors, default=all_sectors)

# Sidebar footer
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
st.sidebar.markdown(
    f'<div class="sidebar-footer">'
    f'📡 Data Source: SET via <b>settfex</b><br>'
    f'🕐 Last refresh: {now_str}'
    f'</div>',
    unsafe_allow_html=True,
)

# ===========================
# FILTER EDGES BY SECTOR
# ===========================
filtered_edges = [
    (src, tgt, rel, w)
    for src, tgt, rel, w in edges_data
    if metadata.get(src, {}).get('sector', 'Unknown') in selected_sectors
]

# ===========================
# BUILD NetworkX GRAPH
# ===========================
G = nx.Graph()
name_key = 'name_th' if lang == 'th' else 'name_en'

for source, target, rel_type, weight in filtered_edges:
    # Company node
    if not G.has_node(source):
        sector   = metadata.get(source, {}).get('sector', 'Unknown')
        name     = metadata.get(source, {}).get(name_key, source)
        color    = node_color('Company', sector)
        G.add_node(
            source,
            group=sector,
            title=f"{source}\n{name}\nSector: {sector}",
            node_type='Company',
            sector=sector,
            color=color,
            size=20,          # base size — will be rescaled below
        )

    # Stakeholder node
    if not G.has_node(target):
        s_type = nodes_info.get(target, 'Stakeholder')
        color  = node_color(s_type)
        G.add_node(
            target,
            group=s_type,
            title=f"{target}\nType: {s_type}",
            node_type=s_type,
            color=color,
            size=10,
        )

    # Edge
    if rel_type == "Shareholder":
        try:
            w_float = float(weight)
        except (ValueError, TypeError):
            w_float = 1.0
        edge_width = max(1.0, min(w_float, 10.0))
        G.add_edge(source, target, value=edge_width,
                   title=f"Holds: {weight}%", color="#f59e0b")
    else:
        G.add_edge(source, target, value=2,
                   title=f"Role: {weight}", color="#38bdf8", dashes=True)

# Rescale company node sizes by degree
if G.number_of_nodes() > 0:
    degrees = dict(G.degree())
    max_deg = max(degrees.values()) or 1
    for n, attr in G.nodes(data=True):
        if attr.get('node_type') == 'Company':
            deg = degrees.get(n, 1)
            G.nodes[n]['size'] = 15 + (deg / max_deg) * 30   # 15–45

# ===========================
# ANALYTICS — TOP ROW METRICS
# ===========================
if lang == 'th':
    title_text = "รายชื่อผู้ถือหุ้นใหญ่และกรรมการของบริษัทจดทะเบียนใน SET50"
    metric_nodes = "Nodes ทั้งหมด"
    metric_edges = "การเชื่อมต่อทั้งหมด"
    metric_top   = "เชื่อมต่อมากที่สุด"
    metric_dens  = "ความหนาแน่นเครือข่าย"
else:
    title_text = "SET50 Major Shareholders and Board of Directors"
    metric_nodes = "Total Nodes"
    metric_edges = "Total Connections"
    metric_top   = "Most Connected"
    metric_dens  = "Network Density"

st.markdown(f"<h1>{title_text}</h1>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(
        f'<div class="glass-card"><div class="metric-label">{metric_nodes}</div>'
        f'<div class="metric-value">{G.number_of_nodes()}</div></div>',
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f'<div class="glass-card"><div class="metric-label">{metric_edges}</div>'
        f'<div class="metric-value">{G.number_of_edges()}</div></div>',
        unsafe_allow_html=True,
    )

if G.number_of_nodes() > 0:
    deg_centrality = nx.degree_centrality(G)
    top_node = max(deg_centrality, key=deg_centrality.get)

    with col3:
        st.markdown(
            f'<div class="glass-card" title="{top_node}"><div class="metric-label">{metric_top}</div>'
            f'<div class="metric-value metric-value-text">{top_node}</div></div>',
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f'<div class="glass-card"><div class="metric-label">{metric_dens}</div>'
            f'<div class="metric-value">{nx.density(G):.4f}</div></div>',
            unsafe_allow_html=True,
        )

    # Top 10 Most Connected — Stakeholders that bridge multiple companies
    st.subheader("🔗 Top 10 Most Connected Nodes")
    top10 = sorted(deg_centrality.items(), key=lambda x: x[1], reverse=True)[:10]
    df_top10 = pd.DataFrame([
        {
            "Node": n,
            "Type": G.nodes[n].get('node_type', ''),
            "Connections": G.degree(n),
            "Centrality": round(c, 4),
        }
        for n, c in top10
    ])
    st.dataframe(df_top10, use_container_width=True, hide_index=True)

# ===========================
# LEGEND
# ===========================
legend_items = [(c, s) for s, c in SECTOR_COLORS.items() if s != 'Unknown']
legend_items += [(SHAREHOLDER_COLOR, 'Shareholder'), (DIRECTOR_COLOR, 'Director')]

legend_html = '<div class="legend-container">'
for color, label in legend_items:
    legend_html += (
        f'<div class="legend-item">'
        f'<div class="legend-dot" style="background:{color};color:{color};"></div>'
        f'{label}</div>'
    )
legend_html += '</div>'
st.markdown(legend_html, unsafe_allow_html=True)

st.divider()

# Process click data from pyvis_comp (handled after graph rendering)
if "last_clicked" not in st.session_state:
    st.session_state["last_clicked"] = None

if "force_selected_node" in st.session_state:
    st.session_state.selected_node_key = st.session_state.force_selected_node
    del st.session_state.force_selected_node

# ===========================
# VISUALIZATION + NODE PROFILER
# ===========================
col_net, col_det = st.columns([2.5, 1])

# Collect company list
company_nodes = [n for n, attr in G.nodes(data=True) if attr.get('node_type') == 'Company']
options = ["-- Show All --"] + sorted(company_nodes) if company_nodes else ["-- Show All --"]

if st.session_state.selected_node_key not in options:
    st.session_state.selected_node_key = "-- Show All --"

# Render selectbox
with col_det:
    st.subheader("🔍 Node Profiler")
    if company_nodes:
        selected_node = st.selectbox(
            "ค้นหาหุ้น / Search Stock" if lang == "th" else "Search / Select Stock",
            options,
            key="selected_node_key"
        )
    else:
        selected_node = None

with col_net:
    st.subheader("📡 Interactive Network")
    st.caption("Drag nodes to interact · Scroll to zoom · Click node to profile")

    # Subgraph when a company is selected
    if selected_node and selected_node != "-- Show All --":
        sub_nodes = [selected_node] + list(G.neighbors(selected_node))
        G_render = G.subgraph(sub_nodes)
    else:
        G_render = G

    # Build Pyvis
    net = Network(height='620px', width='100%', bgcolor='#0d1117', font_color='#e5e7eb', cdn_resources='remote')
    net.set_options("""
    var options = {
      "nodes": {
        "borderWidth": 1.5,
        "shadow": { "enabled": true, "size": 8, "x": 2, "y": 2 }
      },
      "edges": {
        "smooth": { "type": "continuous" }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -80,
          "centralGravity": 0.01,
          "springLength": 120,
          "springConstant": 0.08
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 150,
        "navigationButtons": true,
        "keyboard": true
      }
    }
    """)

    net.from_nx(G_render)

    # Render via tempfile
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as tmp:
        net.save_graph(tmp.name)
        tmp_path = tmp.name

    with open(tmp_path, 'r', encoding='utf-8') as f:
        html_data = f.read()
    os.unlink(tmp_path)

    # Inject click handler JS — sends postMessage to parent when a node is clicked
    click_js = """
    <script>
    (function() {
        // Poll until the Pyvis 'network' object exists (drawGraph creates it)
        var attempts = 0;
        var checkInterval = setInterval(function() {
            attempts++;
            if (attempts > 50) { clearInterval(checkInterval); return; } // give up after 10s
            if (typeof network !== 'undefined' && network !== null) {
                clearInterval(checkInterval);
                network.on("click", function(params) {
                    if (params.nodes.length > 0) {
                        var nodeId = params.nodes[0];
                        // Send to parent window — the pyvis_comp will pick this up
                        window.parent.postMessage({type: 'pyvis_click', node: String(nodeId)}, '*');
                    }
                });
            }
        }, 200);
    })();
    </script>
    """
    html_data = html_data.replace('</body>', click_js + '</body>')

    # Render via custom component
    comp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pyvis_comp')
    pyvis_comp = components.declare_component("pyvis_comp", path=comp_dir)
    
    # We use a static key so the component isn't constantly recreated, but Streamlit 
    # handles args updates (html_data) automatically.
    clicked_node = pyvis_comp(html=html_data, key="pyvis_graph_component")

    if clicked_node and clicked_node != st.session_state.get("last_clicked"):
        st.session_state["last_clicked"] = clicked_node
        company_set = {n for n, a in G.nodes(data=True) if a.get('node_type') == 'Company'}
        if clicked_node in company_set:
            st.session_state.force_selected_node = clicked_node
        else:
            st.session_state.force_selected_node = "-- Show All --"
        st.rerun()

# Node profiler details
with col_det:
    if selected_node and selected_node != "-- Show All --":
        node_attr = G.nodes[selected_node]
        n_type = node_attr.get('node_type', 'Unknown')
        sector = metadata.get(selected_node, {}).get('sector', 'Unknown')
        name   = metadata.get(selected_node, {}).get(name_key, selected_node)


        st.markdown(f"### {selected_node}")
        st.markdown(f"**{name}**")
        st.markdown(f"🏢 Sector: `{sector}`")

        # Financial Highlights — mini cards
        with st.spinner("Loading financials..." if lang == 'en' else "กำลังโหลดข้อมูล..."):
            highlights = get_company_highlights(selected_node, lang=lang)

        if highlights:
            label = "#### Financial Highlights" if lang == 'en' else "#### ข้อมูลทางการเงิน"
            st.markdown(label)
            items = list(highlights.items())
            # Render in a 2-col mini-card grid
            fin_html = '<div class="fin-grid">'
            for k, v in items:
                # Colour YTD green/red
                val_class = ''
                if 'YTD' in k or 'YTD' in str(k):
                    try:
                        val_class = 'positive' if float(v) >= 0 else 'negative'
                    except (ValueError, TypeError):
                        pass
                fin_html += (
                    f'<div class="fin-card">'
                    f'<div class="fin-card-label">{k}</div>'
                    f'<div class="fin-card-value {val_class}">{v if v is not None else "N/A"}</div>'
                    f'</div>'
                )
            fin_html += '</div>'
            st.markdown(fin_html, unsafe_allow_html=True)

        # Connections list
        connections = list(G.neighbors(selected_node))
        label2 = "#### Connections" if lang == 'en' else "#### การเชื่อมต่อ"
        st.markdown(label2)
        st.markdown(f"Total: **{len(connections)}**")
        for conn in connections[:10]:
            edge_data = G.get_edge_data(selected_node, conn)
            st.markdown(f"- {conn} _{edge_data.get('title', '')}_")
        if len(connections) > 10:
            st.markdown(f"*... and {len(connections) - 10} more*")



    elif not company_nodes:
        st.info("Network is empty. Adjust sector filters.")
    else:
        if lang == 'th':
            st.info("เลือกชื่อหุ้นจากรายการด้านบนเพื่อดูรายละเอียดและโฟกัสกราฟ")
        else:
            st.info("Select a stock from the dropdown to profile it and isolate its network.")


