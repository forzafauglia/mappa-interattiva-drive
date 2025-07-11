import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from datetime import datetime

# --- 1. FUNZIONE DI CONTROLLO PASSWORD ---
def check_password():
    """Restituisce True se l'utente è autenticato, altrimenti False."""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.text_input(
            "Inserisci la password per accedere:",
            type="password",
            on_change=password_entered,
            key="password",
        )
        if st.session_state["password_correct"] is False and "password" in st.session_state and st.session_state["password"] != "":
             st.error("😕 Password errata. Riprova.")
        st.stop()
    return True

# --- Contatore di Visualizzazioni ---
@st.cache_resource
def get_view_counter():
    return {"count": 0}
counter = get_view_counter()
counter["count"] += 1

# Esegui il controllo della password
check_password()

# --- 2. IL CODICE DELLA TUA APP ---
st.set_page_config(page_title="Mappa Funghi Protetta", layout="wide")

# --- MODIFICA RIPRISTINATA: Il tuo titolo originale ---
st.title("🗺️ Mappa Interattiva – by Bobo")

# --- Caricamento Dati ---
SHEET_URL = (
    "https://docs.google.com/spreadsheets/"
    "d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)
COL_LAT = "Y"
COL_LON = "X"
COL_COLORE = "COLORE"

@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, na_values=["#N/D", "#N/A"])
        df.columns = df.columns.str.strip()
        df.attrs['last_loaded'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        return df
    except Exception as e:
        st.error(f"Impossibile caricare i dati dal Google Sheet. Errore: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("Il DataFrame è vuoto o non è stato possibile caricarlo.")
    st.stop()

# --- Informazioni nella Sidebar ---
st.sidebar.title("Informazioni")
st.sidebar.write("✅ Colonne lette:", df.columns.tolist())
st.sidebar.success(f"Aggiunti {len(df.dropna(subset=[COL_LAT, COL_LON]))} marker sulla mappa.")
st.sidebar.markdown("---")
st.sidebar.subheader("Statistiche")
st.sidebar.info(f"Visite totali: **{counter['count']}**")
if 'last_loaded' in df.attrs:
    st.sidebar.info(f"Dati aggiornati il: **{df.attrs['last_loaded']}**")

# --- Preparazione Mappa ---
required_cols = [COL_LAT, COL_LON, COL_COLORE]
if not all(col in df.columns for col in required_cols):
    st.error(
        f"❌ Colonne necessarie non trovate! Assicurati che nel Google Sheet esistano: "
        f"'{COL_LAT}', '{COL_LON}' e '{COL_COLORE}'."
    )
    st.stop()

df.dropna(subset=[COL_LAT, COL_LON], inplace=True)
mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

def get_marker_color(val):
    val = str(val).strip().upper()
    return {
        "ROSSO": "red",
        "GIALLO": "yellow",
        "ARANCIONE": "orange",
        "VERDE": "green"
    }.get(val, "gray")

for _, row in df.iterrows():
    try:
        lat = float(str(row[COL_LAT]).replace(',', '.'))
        lon = float(str(row[COL_LON]).replace(',', '.'))
        if not (42 < lat < 45 and 9 < lon < 13):
            continue
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
    except (ValueError, TypeError):
        continue

# --- Visualizzazione Mappa ---
# La riga st.title() è stata spostata all'inizio, qui mostriamo solo la mappa.
folium_static(mappa, width=1000, height=700)
