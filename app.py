import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

st.set_page_config(page_title="Mappa Interattiva", layout="wide")

# URL CSV pubblico del Google Sheet
SHEET_URL = (
    "https://docs.google.com/spreadsheets/"
    "d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)

# --- MODIFICA 1: Definiamo i nomi esatti delle colonne ---
# Questo è molto più robusto che cercare una sottostringa.
# Se i nomi nel Google Sheet cambiano, basterà aggiornarli qui.
COL_COORD = "COORDINATE (lat, lon)"
COL_COLORE = "Colore del marker (ROSSO, GIALLO, VERDE)"


@st.cache_data(ttl=3600)
def load_data():
    """Carica i dati dal Google Sheet e li restituisce come DataFrame."""
    try:
        df = pd.read_csv(SHEET_URL)
        return df
    except Exception as e:
        # Fornisce un errore più chiaro se il link non è raggiungibile
        st.error(f"Impossibile caricare i dati dal Google Sheet. Errore: {e}")
        return pd.DataFrame() # Restituisce un dataframe vuoto per evitare altri errori

df = load_data()

# Se il caricamento dei dati fallisce, df sarà vuoto. Interrompiamo lo script.
if df.empty:
    st.stop()

# 🔎 Mostra nomi colonne per aiutarti nel debug
st.sidebar.write("📋 Colonne trovate nel foglio:", df.columns.tolist())


# --- MODIFICA 2: Rimuoviamo la funzione `trova_colonna` e controlliamo direttamente ---
# Controlliamo se le colonne definite esistono nel DataFrame caricato.
if COL_COORD not in df.columns or COL_COLORE not in df.columns:
    st.error(
        f"❌ Colonne necessarie non trovate! "
        f"Assicurati che nel Google Sheet esistano esattamente le colonne: "
        f"'{COL_COORD}' e '{COL_COLORE}'."
    )
    st.stop()

# Pulisce i dati, mantenendo solo le righe con coordinate valide
df.dropna(subset=[COL_COORD], inplace=True)

# Mappa centrata sulla Toscana
mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

# Funzione per mappare i nomi dei colori ai colori CSS/Folium
def get_marker_color(val):
    # Rende il confronto insensibile a maiuscole/minuscole e spazi
    val = str(val).strip().upper()
    return {
        "ROSSO": "red",
        "GIALLO": "orange",
        "ARANCIONE": "darkorange", # Aggiunto per coerenza
        "VERDE": "green"
    }.get(val, "gray") # Grigio come colore di default se non trovato

# Itera sulle righe del DataFrame per aggiungere i marker alla mappa
for _, row in df.iterrows():
    try:
        # Estrae e pulisce le coordinate
        lat_lon_str = row[COL_COORD]
        lat, lon = [float(x.strip()) for x in lat_lon_str.split(",")]

        # Ottiene il colore
        colore = get_marker_color(row[COL_COLORE])

        # --- MODIFICA 3: Popup più pulito e robusto ---
        # Costruisce il contenuto del popup mostrando tutte le colonne non vuote per quella riga.
        popup_html = ""
        for col_name, col_value in row.items():
            if pd.notna(col_value) and str(col_value).strip() != "":
                popup_html += f"<b>{col_name}</b>: {col_value}<br>"
        
        # Aggiunge il marker alla mappa
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color=colore,
            fill=True,
            fill_color=colore, # È buona norma specificare anche fill_color
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=350)
        ).add_to(mappa)
    except (ValueError, IndexError):
        # Ignora le righe con coordinate formattate male (es. "43.1, ")
        # e continua con il ciclo.
        st.sidebar.warning(f"Riga saltata a causa di coordinate non valide: {row[COL_COORD]}")
        continue

# Titolo e visualizzazione della mappa
st.title("🗺️ Mappa Interattiva – aggiornata da Google Sheets")
folium_static(mappa, width=1000, height=700)
