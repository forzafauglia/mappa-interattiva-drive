import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

st.set_page_config(page_title="Mappa Interattiva", layout="wide")

# URL CSV pubblico del Google Sheet
sheet_url = (
    "https://docs.google.com/spreadsheets/"
    "d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(sheet_url)
    return df

df = load_data()

# ?? Mostra nomi colonne per aiutarti
st.sidebar.write("?? Colonne trovate:", df.columns.tolist())

# ?? Trova nomi delle colonne anche se scritti in modo strano
def trova_colonna(parziale):
    for col in df.columns:
        if parziale.lower() in col.lower():
            return col
    return None

col_coord = trova_colonna("coord")     # ad esempio: "Coordinate"
col_colore = trova_colonna("colore")   # ad esempio: "Colore"

if not col_coord or not col_colore:
    st.error(f"? Colonne con coordinate o colore non trovate. Controlla i nomi nel Google Sheet.")
    st.stop()

# Pulisce i dati con coordinate valide
df = df[df[col_coord].notna()]

# Mappa centrata sulla Toscana
mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

# Colori personalizzati
def colore_marker(val):
    val = val.strip().upper() if isinstance(val, str) else ""
    return {
        "ROSSO": "red",
        "GIALLO": "orange",
        "ARANCIONE": "darkorange",
        "VERDE": "green"
    }.get(val, "gray")

# Marker
for _, row in df.iterrows():
    try:
        lat_lon = row[col_coord]
        lat, lon = [float(x) for x in lat_lon.strip("() ").split(",")]
        colore = colore_marker(row[col_colore])
        
        popup_html = ""
        for col in df.columns[:31]:  # Colonne da A ad AE
            val = row[col]
            if pd.notna(val):
                popup_html += f"<b>{col}</b>: {val}<br>"

        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color=colore,
            fill=True,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(mappa)
    except Exception:
        continue

# Titolo e mappa
st.title("??? Mappa Interattiva – aggiornata da Google Sheets")
folium_static(mappa, width=1000, height=700)
