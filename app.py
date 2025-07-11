import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

st.set_page_config(page_title="Mappa Interattiva", layout="wide")

SHEET_URL = (
    "https://docs.google.com/spreadsheets/"
    "d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)

# --- Nomi delle colonne (DA VERIFICARE con il debug!) ---
COL_COORD = "COORDINATE (lat, lon)"
COL_COLORE = "Colore del marker (ROSSO, GIALLO, VERDE)"

@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        return df
    except Exception as e:
        st.error(f"Impossibile caricare i dati dal Google Sheet. Errore: {e}")
        return pd.DataFrame()

df = load_data()

# --- AGGIUNTA PER DEBUG ---
# Questo ti mostrerà i nomi esatti delle colonne come li vede Pandas.
# Copia e incolla i nomi corretti nelle variabili COL_COORD e COL_COLORE sopra.
st.subheader("🕵️ Dati per il Debug (da rimuovere dopo la correzione) 🕵️")
st.write("Nomi esatti delle colonne lette dal foglio:", df.columns.tolist())
# -------------------------

if df.empty:
    st.warning("Il DataFrame è vuoto. Impossibile continuare.")
    st.stop()

if COL_COORD not in df.columns or COL_COLORE not in df.columns:
    st.error(
        f"❌ Colonne necessarie non trovate! Controlla i nomi stampati sopra e correggili nel codice."
    )
    st.stop()

df.dropna(subset=[COL_COORD], inplace=True)
mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

def get_marker_color(val):
    val = str(val).strip().upper()
    return {
        "ROSSO": "red",
        "GIALLO": "orange",
        "ARANCIONE": "darkorange",
        "VERDE": "green"
    }.get(val, "gray")

for _, row in df.iterrows():
    try:
        lat_lon_str = row[COL_COORD]
        lat, lon = [float(x.strip()) for x in lat_lon_str.split(",")]
        colore = get_marker_color(row[COL_COLORE])
        popup_html = ""
        for col_name, col_value in row.items():
            if pd.notna(col_value) and str(col_value).strip() != "":
                popup_html += f"<b>{col_name}</b>: {col_value}<br>"
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color=colore,
            fill=True,
            fill_color=colore,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=350)
        ).add_to(mappa)
    except (ValueError, IndexError):
        st.sidebar.warning(f"Riga saltata: coordinate non valide -> {row.get(COL_COORD, 'N/A')}")
        continue

st.title("🗺️ Mappa Interattiva – aggiornata da Google Sheets")
folium_static(mappa, width=1000, height=700)