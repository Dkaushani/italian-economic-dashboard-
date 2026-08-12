import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
import json
from streamlit_folium import st_folium

# ---------------------------------------------------------
# Page Setup & Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Italian Regional Economic Risk Dashboard",
    page_icon="🇮🇹",
    layout="wide"
)

st.title("🇮🇹 Italian Regional Economic Risk & Vulnerability Dashboard")
st.markdown("""
This interactive dashboard visualizes relative economic vulnerability across Italian regions 
based on regional GDP per capita (Purchasing Power Standards - PPS).
""")

# ---------------------------------------------------------
# Data Loading & Caching
# ---------------------------------------------------------
@st.cache_data
def load_and_process_data():
    # 1. Fetch GeoJSON Boundaries
    geojson_url = "https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_regions.geojson"
    gdf_italy = gpd.read_file(geojson_url)
    gdf_italy['reg_name'] = gdf_italy['reg_name'].str.strip()

    # 2. Benchmark Regional GDP Data (PPS)
    real_regional_gdp = {
        'Piemonte': 33100, "Valle d'Aosta/Vallée d'Aoste": 38200, 'Liguria': 33800,
        'Lombardia': 41600, 'Trentino-Alto Adige/Südtirol': 42100, 'Veneto': 35800,
        'Friuli-Venezia Giulia': 34200, 'Emilia-Romagna': 38100, 'Toscana': 33200,
        'Umbria': 27900, 'Marche': 29800, 'Lazio': 35900, 'Abruzzo': 26100,
        'Molise': 22800, 'Campania': 20700, 'Puglia': 21800, 'Basilicata': 23900,
        'Calabria': 18900, 'Sicilia': 19800, 'Sardegna': 23400
    }
    df_gdp = pd.DataFrame(list(real_regional_gdp.items()), columns=['reg_name', 'gdp_per_capita'])

    # 3. Merge Shapes with Economic Data
    gdf_merged = gdf_italy.merge(df_gdp, on='reg_name', how='inner')

    # 4. Normalization (Economic Risk Score)
    min_gdp = gdf_merged['gdp_per_capita'].min()
    max_gdp = gdf_merged['gdp_per_capita'].max()
    
    gdf_merged['economic_risk_score'] = round(
        100 * (1 - (gdf_merged['gdp_per_capita'] - min_gdp) / (max_gdp - min_gdp)), 1
    )
    gdf_merged['gdp_display'] = gdf_merged['gdp_per_capita'].apply(lambda x: f"{x:,} PPS")
    
    return gdf_merged

# Load cached data
gdf_data = load_and_process_data()

# ---------------------------------------------------------
# Sidebar Controls & Filters
# ---------------------------------------------------------
st.sidebar.header("Dashboard Controls")

# Region selector
selected_region = st.sidebar.selectbox(
    "Select a Region to Inspect:",
    ["All Regions"] + sorted(gdf_data['reg_name'].unique().tolist())
)

# Color Scheme Option
color_scheme = st.sidebar.selectbox(
    "Select Color Palette:",
    ["YlOrRd", "Reds", "Viridis", "YlGnBu"]
)

# Filter Data if region selected
if selected_region != "All Regions":
    filtered_data = gdf_data[gdf_data['reg_name'] == selected_region]
else:
    filtered_data = gdf_data

# ---------------------------------------------------------
# High-Level Metrics Row
# ---------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Regions Analyzed", len(gdf_data))

with col2:
    if selected_region == "All Regions":
        avg_gdp = int(gdf_data['gdp_per_capita'].mean())
        st.metric("National Avg GDP per Capita", f"{avg_gdp:,} PPS")
    else:
        reg_gdp = filtered_data['gdp_per_capita'].values[0]
        st.metric(f"GDP per Capita ({selected_region})", f"{reg_gdp:,} PPS")

with col3:
    if selected_region == "All Regions":
        avg_risk = round(gdf_data['economic_risk_score'].mean(), 1)
        st.metric("Average Vulnerability Index", f"{avg_risk} / 100")
    else:
        reg_risk = filtered_data['economic_risk_score'].values[0]
        st.metric(f"Risk Score ({selected_region})", f"{reg_risk} / 100")

st.markdown("---")

# ---------------------------------------------------------
# Build & Display Folium Map
# ---------------------------------------------------------
st.subheader("Geospatial Vulnerability Map")

m = folium.Map(location=[42.5, 12.5], zoom_start=6, tiles="cartodbpositron")

# Base Choropleth Layer
folium.Choropleth(
    geo_data=filtered_data,
    name="Economic Risk Score",
    data=filtered_data,
    columns=["reg_name", "economic_risk_score"],
    key_on="feature.properties.reg_name",
    fill_color=color_scheme,
    fill_opacity=0.7,
    line_opacity=0.4,
    legend_name="Economic Risk Score (0 = Low, 100 = High Vulnerability)",
).add_to(m)

# Tooltips Layer
geojson_data = json.loads(filtered_data.to_json())
info_tooltip = folium.features.GeoJson(
    data=geojson_data,
    style_function=lambda x: {'fillColor': '#ffffff00', 'color':'#000000', 'weight': 0.5},
    control=False,
    highlight_function=lambda x: {'weight': 2.5, 'color': '#222222', 'fillOpacity': 0.8},
    tooltip=folium.features.GeoJsonTooltip(
        fields=['reg_name', 'gdp_display', 'economic_risk_score'],
        aliases=['Region:', 'GDP per Capita:', 'Risk Score (0-100):'],
        style="background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 8px;"
    )
)
m.add_child(info_tooltip)

# Render Folium map in Streamlit
st_folium(m, width="100%", height=500, returned_objects=[])

# Data Table Display
with st.expander("View Raw Regional Data Table"):
    st.dataframe(
        gdf_data[['reg_name', 'gdp_per_capita', 'economic_risk_score']]
        .sort_values(by='economic_risk_score', ascending=False)
        .reset_index(drop=True),
        use_container_width=True
    )
