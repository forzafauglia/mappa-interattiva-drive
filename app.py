import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

st.set_page_config(page_title="Mappa Interattiva", layout="wide")

# URL pubblico del Google Sheet in formato CSV
sheet_url = (
    "https://docs.google.com/spreadsheets/"
    "d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(sheet_url)
    return df

df = load_data()

# ?? Mostra i nomi delle colonne per verificare quelli corretti
st.sidebar.write("?? Colonne trovate:", df.columns.tolist())

# Qui inserisci i nomi delle colonne esatti come appaiono:
col_coord = "Coordinate"  # es. la colonna con "(lat, lon)"
col_colore = "Colore"     # es. la colonna con ROSSO/GIALLO ecc.

if col_coord not in df.columns or col_colore not in df.columns:
    st.error(f"Le colonne '{col_coord}' o '{col_colore}' non sono state trovate.\n"
             "Controlla i nomi esatti sulla sidebar sopra.")
    st.stop()

# Filtra righe con coordinate
df = df[df[col_coord].notna()]

# Crea la mappa centrata sulla Toscana
mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

# Funzione che assegna il colore al marker
def colore_marker(val):
    val = val.strip().upper() if isinstance(val, str) else ""
    return {
        "ROSSO": "red",
        "GIALLO": "orange",
        "ARANCIONE": "darkorange",
        "VERDE": "green"
    }.get(val, "gray")

# Aggiungi marker correttamente
for _, row in df.iterrows():
    try:
        lat_lon = row[col_coord]
        lat, lon = [float(x) for x in lat_lon.strip("()").split(",")]
        colore = colore_marker(row[col_colore])
        
        # Costruzione del popup con le colonne da A ad AE
        popup_html = ""
        for col in df.columns[:31]:
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

# **Titolo e visualizzazione della mappa**
st.title("??? Mappa Interattiva – Google Sheets ? Streamlit")
folium_static(mappa, width=1000, height=700)
