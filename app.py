import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

st.set_page_config(page_title="Mappa Interattiva", layout="wide")

# URL CSV pubblico del Google Sheet
sheet_url = (
    "https://docs.google.com/spreadsheets/d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(sheet_url)
    return df

# Caricamento dati
df = load_data()

# ?? Mostra tutte le colonne trovate per capire i nomi
st.sidebar.write("?? Colonne trovate nel file:", df.columns.tolist())

# ?? Trova la colonna che contiene le coordinate (es. "(43.77,11.09)")
col_coord = next((col for col in df.columns if "coord" in col.lower()), None)

# ?? Trova la colonna che contiene il colore (es. "ROSSO")
col_colore = next((col for col in df.columns if "colore" in col.lower() or "y" == col.strip().lower()), None)

if not col_coord or not col_colore:
    st.error("? Errore: Non riesco a trovare la colonna con le coordinate o il colore.")
    st.stop()

# Pulisce i dati con coordinate valide
df = df[df[col_coord].notna()]

# Crea la mappa centrata sulla Toscana
mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

# Funzione per il colore
def colore_marker(val):
    val = str(val).strip().upper()
    return {
        "ROSSO": "red",
        "GIALLO": "orange",
        "ARANCIONE": "darkorange",
        "VERDE": "green"
    }.get(val, "gray")

# Aggiunge i marker
for _, row in df.iterrows():
    try:
        coord_text = row[col_coord]
        lat, lon = [float(x.strip()) for x in coord_text.strip("()").split(",")]
        colore = colore_marker(row[col_colore])

        # Popup: mostra tutte le colonne da A ad AE (indice 0–30)
        popup_html = ""
        for col in df.columns[:31]:
            valore = row[col]
            if pd.notna(valore):
                popup_html += f"<b>{col}</b>: {valore}<br>"

        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color=colore,
            fill=True,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=400)
        ).add_to(mappa)
    except Exception:
        continue

st.title("?? Mappa Interattiva da Google Sheets")
folium_static(mappa, width=1000, height=700)
