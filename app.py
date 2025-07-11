import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

st.set_page_config(page_title="Mappa Interattiva", layout="wide")

# URL CSV pubblico del Google Sheet (lo stesso di prima)
SHEET_URL = (
    "https://docs.google.com/spreadsheets/"
    "d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)

# --- MODIFICA 1: Usiamo i nomi ESATTI dal tuo file ---
# Questi sono i nomi corretti delle colonne, copiati dal tuo file.
COL_COORD = "COORDINATE GOOGLE MAPS"
COL_COLORE = "COLORE"


@st.cache_data(ttl=3600)
def load_data():
    """Carica e pulisce i dati dal Google Sheet."""
    try:
        # --- MODIFICA 2: Gestione robusta dei dati ---
        # Aggiungiamo 'na_values' per dire a pandas di considerare "#N/D" come un valore vuoto.
        df = pd.read_csv(SHEET_URL, na_values=["#N/D"])
        
        # Pulisce i nomi delle colonne da eventuali spazi bianchi all'inizio o alla fine.
        # Es: " COLORE " diventa "COLORE"
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

# Controlliamo se le colonne definite esistono nel DataFrame caricato.
if COL_COORD not in df.columns or COL_COLORE not in df.columns:
    st.error(
        f"❌ Colonne necessarie non trovate! "
        f"Assicurati che nel Google Sheet esistano esattamente le colonne: "
        f"'{COL_COORD}' e '{COL_COLORE}'."
    )
    st.stop()

# Pulisce i dati, mantenendo solo le righe con coordinate valide e non vuote
df.dropna(subset=[COL_COORD], inplace=True)

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

# Itera sulle righe per aggiungere i marker
for _, row in df.iterrows():
    try:
        lat_lon_str = row[COL_COORD]
        # La virgola nei numeri (es. "43,123") può dare problemi.
        # Sostituiamo la virgola del decimale con il punto.
        lat_lon_str = lat_lon_str.replace(',', '.', 1) # Sostituisce solo la prima occorrenza (separatore decimale)
        lat, lon = [float(x.strip()) for x in lat_lon_str.split(',')] # Splitta su un'altra virgola (separatore coordinate)

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
    except (ValueError, IndexError, AttributeError):
        # Ignora le righe con coordinate formattate male (es. vuote, testo, #N/D)
        # L'AttributeError gestisce il caso in cui lat_lon_str non sia una stringa.
        continue

# Titolo e visualizzazione della mappa
st.title("🗺️ Mappa Interattiva – aggiornata da Google Sheets")
folium_static(mappa, width=1000, height=700)
