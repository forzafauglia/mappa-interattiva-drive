import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

st.set_page_config(page_title="Mappa Interattiva", layout="wide")

# URL pubblico del Google Sheet (in formato CSV)
sheet_url = "https://docs.google.com/spreadsheets/d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(sheet_url)
    df = df[df['H'].notna()]  # filtra righe con coordinate
    return df

df = load_data()

# Crea la mappa centrata sulla Toscana (centro approssimato)
mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

# Funzione per assegnare colore ai marker
def colore_marker(valore):
    colore = valore.strip().upper() if isinstance(valore, str) else ""
    return {
        "ROSSO": "red",
        "GIALLO": "orange",
        "ARANCIONE": "darkorange",
        "VERDE": "green"
    }.get(colore, "gray")

# Aggiungi i marker
for _, row in df.iterrows():
    try:
        # Leggi coordinate (colonna H, formato "(latitudine, longitudine)")
        lat_lon = row['H']
        lat, lon = [float(x) for x in lat_lon.strip("()").split(",")]

        # Colore del marker
        colore = colore_marker(row['Y'])

        # Popup: mostriamo i dati da colonna A ad AE
        popup_text = ""
        for col in df.columns[:31]:  # A ? AE = prime 31 colonne
            val = row[col]
            if pd.notna(val):
                popup_text += f"<b>{col}</b>: {val}<br>"

        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color=colore,
            fill=True,
            fill_opacity=0.9,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(mappa)
    except Exception as e:
        continue

st.title("??? Mappa Interattiva - Aggiornata da Google Sheets")
folium_static(mappa, width=1000, height=700)
