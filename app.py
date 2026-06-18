import streamlit as st
import pymongo
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Page Config ──
st.set_page_config(page_title="Airbnb Analytics Dashboard", page_icon="🏠", layout="wide")

# ── Custom CSS ──
st.markdown("""
<style>
    .main .block-container { padding-top: 1rem; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea22, #764ba222);
        border: 1px solid #ffffff11;
        border-radius: 12px;
        padding: 12px 16px;
    }
    div[data-testid="stMetric"] label { font-size: 0.85rem; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 1.6rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏠 Airbnb Analytics Dashboard")

# ── MongoDB Connection ──
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["mongo"]["uri"]) #using secret key for storing user and pwd

try:
    client = init_connection()
except Exception as e:
    st.error(f"Failed to connect to MongoDB: {e}")
    st.stop()

# ── Data Fetching ──
@st.cache_data(ttl=600)
def get_data():
    db = client["sample_airbnb"]
    col = db["listingsAndReviews"]

    cursor = col.find(
        {"price": {"$exists": True}},
        {
            "name": 1, "summary": 1, "property_type": 1, "room_type": 1,
            "bed_type": 1, "accommodates": 1, "bedrooms": 1, "beds": 1,
            "bathrooms": 1, "price": 1, "cleaning_fee": 1,
            "number_of_reviews": 1, "minimum_nights": 1, "maximum_nights": 1,
            "cancellation_policy": 1, "host.host_is_superhost": 1,
            "address.market": 1, "address.country": 1, "address.suburb": 1,
            "address.location.coordinates": 1,
            "review_scores.review_scores_rating": 1,
            "review_scores.review_scores_cleanliness": 1,
            "review_scores.review_scores_accuracy": 1,
            "review_scores.review_scores_checkin": 1,
            "review_scores.review_scores_communication": 1,
            "review_scores.review_scores_location": 1,
            "review_scores.review_scores_value": 1,
            "amenities": 1,
        }
    ).limit(3000)

    items = list(cursor)
    rows = []
    for item in items:
        def to_float(v):
            if v is None: return None
            try: return float(str(v))
            except: return None

        coords = item.get("address", {}).get("location", {}).get("coordinates", [None, None])
        lon = coords[0] if coords and len(coords) > 0 else None
        lat = coords[1] if coords and len(coords) > 1 else None
        rs = item.get("review_scores", {}) or {}
        amenities = item.get("amenities", []) or []

        rows.append({
            "_id": str(item.get("_id")),
            "name": item.get("name"),
            "summary": (item.get("summary") or "")[:120],
            "property_type": item.get("property_type"),
            "room_type": item.get("room_type"),
            "bed_type": item.get("bed_type"),
            "accommodates": item.get("accommodates"),
            "bedrooms": to_float(item.get("bedrooms")),
            "beds": to_float(item.get("beds")),
            "bathrooms": to_float(item.get("bathrooms")),
            "price": to_float(item.get("price")),
            "cleaning_fee": to_float(item.get("cleaning_fee")),
            "number_of_reviews": item.get("number_of_reviews", 0),
            "minimum_nights": to_float(item.get("minimum_nights")),
            "maximum_nights": to_float(item.get("maximum_nights")),
            "cancellation_policy": item.get("cancellation_policy"),
            "superhost": item.get("host", {}).get("host_is_superhost", False),
            "market": item.get("address", {}).get("market"),
            "country": item.get("address", {}).get("country"),
            "suburb": item.get("address", {}).get("suburb"),
            "lon": lon, "lat": lat,
            "rating": to_float(rs.get("review_scores_rating")),
            "cleanliness": to_float(rs.get("review_scores_cleanliness")),
            "accuracy": to_float(rs.get("review_scores_accuracy")),
            "checkin": to_float(rs.get("review_scores_checkin")),
            "communication": to_float(rs.get("review_scores_communication")),
            "location_score": to_float(rs.get("review_scores_location")),
            "value": to_float(rs.get("review_scores_value")),
            "amenity_count": len(amenities),
            "has_wifi": "Wifi" in amenities or "Wireless Internet" in amenities,
            "has_kitchen": "Kitchen" in amenities,
            "has_ac": "Air conditioning" in amenities,
            "has_pool": "Pool" in amenities,
        })

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["price"])
    df["price_per_bedroom"] = df.apply(
        lambda r: r["price"] / r["bedrooms"] if r["bedrooms"] and r["bedrooms"] > 0 else None, axis=1
    )
    return df

with st.spinner("Loading data from MongoDB..."):
    df_raw = get_data()

if df_raw.empty:
    st.warning("No data found. Check your connection & dataset.")
    st.stop()

# ── Sidebar Filters ──
st.sidebar.header("🔍 Filters")

countries = sorted(df_raw["country"].dropna().unique().tolist())
sel_country = st.sidebar.selectbox("Country", ["All"] + countries)
df = df_raw.copy()
if sel_country != "All":
    df = df[df["country"] == sel_country]

room_types = df["room_type"].dropna().unique().tolist()
sel_rooms = st.sidebar.multiselect("Room Type", room_types, default=room_types)
if sel_rooms:
    df = df[df["room_type"].isin(sel_rooms)]

p_min, p_max = int(df["price"].min()), min(int(df["price"].max()), 2000)
st.sidebar.markdown("**Price Range ($)**")
price_col1, price_col2 = st.sidebar.columns(2)
input_min = price_col1.number_input("Min", min_value=p_min, max_value=p_max, value=p_min, step=10, key="price_min")
input_max = price_col2.number_input("Max", min_value=p_min, max_value=p_max, value=p_max, step=10, key="price_max")
price_range = st.sidebar.slider("Drag to adjust", p_min, p_max, (int(input_min), int(input_max)), key="price_slider", label_visibility="collapsed")
df = df[(df["price"] >= price_range[0]) & (df["price"] <= price_range[1])]

superhost_only = st.sidebar.checkbox("Superhost Only")
if superhost_only:
    df = df[df["superhost"] == True]

st.sidebar.markdown("---")
st.sidebar.caption(f"Showing **{len(df):,}** of {len(df_raw):,} listings")

# ── KPI Metrics ──
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Listings", f"{len(df):,}")
c2.metric("Avg Price", f"${df['price'].mean():.0f}")
c3.metric("Median Price", f"${df['price'].median():.0f}")
avg_rating = df["rating"].mean()
c4.metric("Avg Rating", f"{avg_rating:.1f}/100" if not pd.isna(avg_rating) else "N/A")
c5.metric("Superhosts", f"{df['superhost'].sum():,}")
c6.metric("Markets", f"{df['market'].nunique()}")

st.markdown("")

# ── Tabs ──
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Map", "📊 Price Analysis", "⭐ Reviews", "🏘️ Property Insights", "📋 Data Explorer"
])

# ══════════════════════ TAB 1 — MAP ══════════════════════
with tab1:
    map_df = df.dropna(subset=["lat", "lon"])
    if not map_df.empty:
        color_by = st.radio("Color by", ["price", "rating", "room_type"], horizontal=True, key="map_color")
        fig = px.scatter_mapbox(
            map_df, lat="lat", lon="lon",
            color=color_by,
            size="accommodates",
            color_continuous_scale="Turbo" if color_by != "room_type" else None,
            size_max=14, zoom=1,
            hover_name="name",
            hover_data={"lat": False, "lon": False, "price": True, "room_type": True, "rating": True},
        )
        fig.update_layout(mapbox_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0), height=550)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No listings with coordinates for the current filter.")

# ══════════════════════ TAB 2 — PRICE ══════════════════════
with tab2:
    r1c1, r1c2 = st.columns(2)

    with r1c1:
        fig_hist = px.histogram(df, x="price", nbins=40, color="room_type",
                                title="Price Distribution by Room Type",
                                color_discrete_sequence=px.colors.qualitative.Pastel1)
        fig_hist.update_layout(bargap=0.05, xaxis_title="Price ($)", yaxis_title="Count")
        st.plotly_chart(fig_hist, use_container_width=True)

    with r1c2:
        fig_box = px.box(df, x="room_type", y="price", color="room_type",
                         title="Price Spread by Room Type", points="outliers",
                         color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig_box, use_container_width=True)

    r2c1, r2c2 = st.columns(2)

    with r2c1:
        # Avg price by market
        market_price = df.groupby("market")["price"].agg(["mean", "count"]).reset_index()
        market_price.columns = ["market", "avg_price", "count"]
        market_price = market_price[market_price["count"] >= 5].sort_values("avg_price", ascending=True).tail(15)
        fig_bar = px.bar(market_price, x="avg_price", y="market", orientation="h",
                         title="Top 15 Markets by Avg Price",
                         color="avg_price", color_continuous_scale="Sunset",
                         hover_data={"count": True})
        fig_bar.update_layout(yaxis_title="", xaxis_title="Avg Price ($)", showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with r2c2:
        ppb = df.dropna(subset=["price_per_bedroom"])
        if not ppb.empty:
            ppb_market = ppb.groupby("market")["price_per_bedroom"].mean().reset_index()
            ppb_market = ppb_market.sort_values("price_per_bedroom", ascending=True).tail(15)
            fig_ppb = px.bar(ppb_market, x="price_per_bedroom", y="market", orientation="h",
                             title="Price Per Bedroom by Market",
                             color="price_per_bedroom", color_continuous_scale="Tealgrn")
            fig_ppb.update_layout(yaxis_title="", xaxis_title="$/Bedroom", showlegend=False)
            st.plotly_chart(fig_ppb, use_container_width=True)

    # Correlation heatmap
    st.subheader("Correlation Matrix")
    num_cols = ["price", "accommodates", "bedrooms", "beds", "bathrooms",
                "number_of_reviews", "rating", "amenity_count"]
    corr_df = df[num_cols].dropna()
    if len(corr_df) > 10:
        corr = corr_df.corr()
        fig_corr = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r",
                             title="Feature Correlation Heatmap", aspect="auto")
        fig_corr.update_layout(height=500)
        st.plotly_chart(fig_corr, use_container_width=True)

# ══════════════════════ TAB 3 — REVIEWS ══════════════════════
with tab3:
    rc1, rc2 = st.columns(2)

    with rc1:
        score_cols = ["cleanliness", "accuracy", "checkin", "communication", "location_score", "value"]
        means = {c: df[c].mean() for c in score_cols if not pd.isna(df[c].mean())}
        if means:
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=list(means.values()), theta=[c.replace("_", " ").title() for c in means.keys()],
                fill="toself", name="Average Scores",
                line_color="#FF5A5F"
            ))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
                                    title="Average Review Score Breakdown", height=400)
            st.plotly_chart(fig_radar, use_container_width=True)

    with rc2:
        rated = df.dropna(subset=["rating"])
        if not rated.empty:
            fig_scatter = px.scatter(rated, x="rating", y="price", color="room_type",
                                    size="number_of_reviews", size_max=12,
                                    title="Rating vs Price",
                                    hover_name="name", opacity=0.6,
                                    color_discrete_sequence=px.colors.qualitative.Bold)
            st.plotly_chart(fig_scatter, use_container_width=True)

    # Superhost comparison
    st.subheader("Superhost vs Regular Host")
    sh_comp = df.groupby("superhost").agg(
        avg_price=("price", "mean"), avg_rating=("rating", "mean"),
        avg_reviews=("number_of_reviews", "mean"), count=("_id", "count")
    ).reset_index()
    sh_comp["superhost"] = sh_comp["superhost"].map({True: "Superhost", False: "Regular"})

    sc1, sc2, sc3 = st.columns(3)
    for col_widget, metric, title in [
        (sc1, "avg_price", "Avg Price ($)"),
        (sc2, "avg_rating", "Avg Rating"),
        (sc3, "avg_reviews", "Avg Reviews"),
    ]:
        fig_sh = px.bar(sh_comp, x="superhost", y=metric, color="superhost", title=title,
                        color_discrete_map={"Superhost": "#FF5A5F", "Regular": "#484848"})
        fig_sh.update_layout(showlegend=False, xaxis_title="")
        col_widget.plotly_chart(fig_sh, use_container_width=True)

# ══════════════════════ TAB 4 — PROPERTY INSIGHTS ══════════════════════
with tab4:
    pc1, pc2 = st.columns(2)

    with pc1:
        prop_counts = df["property_type"].value_counts().reset_index()
        prop_counts.columns = ["property_type", "count"]
        fig_tree = px.treemap(prop_counts.head(20), path=["property_type"], values="count",
                              title="Property Type Treemap (Top 20)",
                              color="count", color_continuous_scale="Viridis")
        fig_tree.update_layout(height=450)
        st.plotly_chart(fig_tree, use_container_width=True)

    with pc2:
        sun_df = df.dropna(subset=["country", "room_type"]).copy()
        if not sun_df.empty:
            fig_sun = px.sunburst(sun_df, path=["country", "room_type", "property_type"],
                                  title="Hierarchy: Country → Room → Property",
                                  color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_sun.update_layout(height=450)
            st.plotly_chart(fig_sun, use_container_width=True)

    # Amenity popularity
    st.subheader("Top Amenity Features")
    amenity_flags = {"WiFi": "has_wifi", "Kitchen": "has_kitchen",
                     "AC": "has_ac", "Pool": "has_pool"}
    am_data = []
    for label, col in amenity_flags.items():
        pct = df[col].mean() * 100
        avg_p = df[df[col]]["price"].mean()
        am_data.append({"Amenity": label, "% of Listings": round(pct, 1), "Avg Price ($)": round(avg_p, 1)})
    am_df = pd.DataFrame(am_data)

    ac1, ac2 = st.columns(2)
    with ac1:
        fig_am = px.bar(am_df, x="Amenity", y="% of Listings", color="Amenity",
                        title="Amenity Prevalence",
                        color_discrete_sequence=px.colors.qualitative.Vivid)
        fig_am.update_layout(showlegend=False)
        st.plotly_chart(fig_am, use_container_width=True)
    with ac2:
        fig_amp = px.bar(am_df, x="Amenity", y="Avg Price ($)", color="Amenity",
                         title="Avg Price by Amenity",
                         color_discrete_sequence=px.colors.qualitative.Vivid)
        fig_amp.update_layout(showlegend=False)
        st.plotly_chart(fig_amp, use_container_width=True)

    # Cancellation policy
    st.subheader("Cancellation Policy Distribution")
    cancel = df["cancellation_policy"].value_counts().reset_index()
    cancel.columns = ["policy", "count"]
    fig_cancel = px.pie(cancel, values="count", names="policy", hole=0.45,
                        color_discrete_sequence=px.colors.qualitative.Set3)
    st.plotly_chart(fig_cancel, use_container_width=True)

# ══════════════════════ TAB 5 — DATA EXPLORER ══════════════════════
with tab5:
    st.subheader("Top Listings")
    sort_by = st.selectbox("Sort by", ["price", "rating", "number_of_reviews"], key="sort_top")
    ascending = st.checkbox("Ascending", value=False, key="asc_top")
    display_cols = ["name", "country", "market", "room_type", "property_type",
                    "price", "bedrooms", "rating", "number_of_reviews", "superhost"]
    top_df = df[display_cols].sort_values(sort_by, ascending=ascending).head(50)
    st.dataframe(top_df, use_container_width=True, height=400)

    st.subheader("Descriptive Statistics")
    st.dataframe(df[["price", "accommodates", "bedrooms", "beds", "bathrooms",
                      "number_of_reviews", "rating", "amenity_count"]].describe().T.round(2),
                 use_container_width=True)

    st.download_button("📥 Download Filtered Data (CSV)", df.to_csv(index=False),
                       "airbnb_filtered.csv", "text/csv")

st.markdown("---")
st.caption("Built by Thiti Chaiwiwatthanan with Streamlit • Plotly • MongoDB | Data: sample_airbnb")
