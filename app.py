import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

st.set_page_config(page_title="Mappa Interattiva", layout="wide")

SHEET_URL = (
    "https://docs.google.com/spreadsheets/"
    "d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)

# --- MODIFICA CHIAVE: Usiamo le colonne X e Y che sono più pulite ---
COL_LAT = "Y"  # Colonna con la Latitudine
COL_LON = "X"  # Colonna con la Longitudine
COL_COLORE = "COLORE"


@st.cache_data(ttl=3600)
def load_data():
    """Carica e pulisce i dati dal Google Sheet."""
    try:
        df = pd.read_csv(SHEET_URL, na_values=["#N/D", "#N/A"])
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Impossibile caricare i dati dal Google Sheet. Errore: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("Il DataFrame è vuoto o non è stato possibile caricarlo.")
    st.stop()

# 🔎 Mostra nomi colonne per aiutarti nel debug
st.sidebar.write("✅ Colonne lette dal foglio:", df.columns.tolist())

# Controlliamo se le colonne definite esistono
required_cols = [COL_LAT, COL_LON, COL_COLORE]
if not all(col in df.columns for col in required_cols):
    st.error(
        f"❌ Colonne necessarie non trovate! "
        f"Assicurati che nel Google Sheet esistano esattamente le colonne: "
        f"'{COL_LAT}', '{COL_LON}' e '{COL_COLORE}'."
    )
    st.stop()

# Pulisce i dati, mantenendo solo le righe con coordinate valide
df.dropna(subset=[COL_LAT, COL_LON], inplace=True)

# Mappa centrata sulla Toscana
mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

def get_marker_color(val):
    val = str(val).strip().upper()
    return {
        "ROSSO": "red",
        "GIALLO": "orange",
        "ARANCIONE": "darkorange",
        "VERDE": "green"
    }.get(val, "gray")

# --- MODIFICA CICLO: Leggiamo da X e Y e gestiamo le virgole decimali ---
markers_added = 0
for _, row in df.iterrows():
    try:
        # 1. Prendi i valori dalle colonne X e Y
        lat_str = str(row[COL_LAT])
        lon_str = str(row[COL_LON])

        # 2. Sostituisci la virgola decimale con il punto
        lat_str_pulita = lat_str.replace(',', '.')
        lon_str_pulita = lon_str.replace(',', '.')

        # 3. Converti in numeri float
        lat = float(lat_str_pulita)
        lon = float(lon_str_pulita)

        # Controlla che le coordinate siano in un range valido per la Toscana
        if not (42 < lat < 45 and 9 < lon < 13):
            continue # Salta coordinate palesemente fuori zona

        colore = get_marker_color(row[COL_COLORE])
        
        popup_html = ""
        for col_name, col_value in row.items():
            if pd.notna(col_value) and str(col_value).strip() != "":
                popup_html += f"<b>{col_name}</b>: {str(col_value)}<br>"
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color=colore,
            fill=True,
            fill_color=colore,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=350)
        ).add_to(mappa)
        markers_added += 1

    except (ValueError, TypeError):
        # Ignora le righe che non possono essere convertite in numeri,
        # anche dopo la pulizia.
        continue

# Aggiungi un messaggio di debug nella sidebar
st.sidebar.success(f"🎉 Aggiunti {markers_added} marker sulla mappa.")
if markers_added == 0:
    st.sidebar.error("Nessun marker è stato aggiunto. Controlla il formato delle colonne 'X' e 'Y' nel Google Sheet. Devono essere numeri validi (es. 43,123 o 11.456).")

# Titolo e visualizzazione della mappa
st.title("🗺️ Mappa Interattiva – by Bobo")
folium_static(mappa, width=1000, height=700)
