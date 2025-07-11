import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# --- 1. FUNZIONE DI CONTROLLO PASSWORD ---
def check_password():
    """Restituisce True se l'utente è autenticato, altrimenti False."""

    def password_entered():
        """Controlla se la password inserita corrisponde a quella nei secrets."""
        # Usa st.secrets["password"] per accedere alla password che imposterai
        # nella dashboard di Streamlit.
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            # Elimina la password dalla memoria per sicurezza
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # Se l'utente non ha ancora inserito la password o se è sbagliata
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        # Mostra il campo per inserire la password
        st.text_input(
            "Inserisci la password per accedere:",
            type="password",
            on_change=password_entered,
            key="password",
        )
        if st.session_state["password_correct"] is False and "password" in st.session_state and st.session_state["password"] != "":
             st.error("😕 Password errata. Riprova.")
        st.stop()  # Ferma l'esecuzione del resto dell'app
    
    # Se la password è corretta, la funzione non farà nulla e lo script continuerà
    return True

# Esegui il controllo della password all'inizio
check_password()


# --- 2. IL CODICE DELLA TUA APP (VIENE ESEGUITO SOLO SE LA PASSWORD È CORRETTA) ---

# Configurazione della pagina (deve essere qui, dopo il check della password)
st.set_page_config(page_title="Mappa Funghi Protetta", layout="wide")

st.title("🍄 Mappa dei Funghi in Toscana (Riservata) 🍄")

# --- Caricamento Dati ---
SHEET_URL = (
    "https://docs.google.com/spreadsheets/"
    "d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)

# Definiamo i nomi delle colonne che useremo
COL_LAT = "Y"
COL_LON = "X"
COL_COLORE = "COLORE"

@st.cache_data(ttl=3600)
def load_data():
    """Carica e pulisce i dati dal Google Sheet."""
    try:
        # Aggiungiamo il riconoscimento per i valori vuoti comuni
        df = pd.read_csv(SHEET_URL, na_values=["#N/D", "#N/A"])
        # Pulisce gli spazi extra dai nomi delle colonne
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Impossibile caricare i dati dal Google Sheet. Errore: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("Il DataFrame è vuoto o non è stato possibile caricarlo.")
    st.stop()

# --- Preparazione e Visualizzazione della Mappa ---

# Mostra le colonne nella sidebar per debug
st.sidebar.write("✅ Colonne lette dal foglio:", df.columns.tolist())

# Controlliamo se le colonne necessarie esistono
required_cols = [COL_LAT, COL_LON, COL_COLORE]
if not all(col in df.columns for col in required_cols):
    st.error(
        f"❌ Colonne necessarie non trovate! Assicurati che nel Google Sheet esistano: "
        f"'{COL_LAT}', '{COL_LON}' e '{COL_COLORE}'."
    )
    st.stop()

# Rimuovi le righe dove le coordinate sono mancanti
df.dropna(subset=[COL_LAT, COL_LON], inplace=True)

# Mappa centrata sulla Toscana
mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

def get_marker_color(val):
    """Restituisce un colore valido per Folium in base al testo."""
    val = str(val).strip().upper()
    return {
        "ROSSO": "red",
        "GIALLO": "yellow",
        "ARANCIONE": "darkorange",
        "VERDE": "green"
    }.get(val, "gray") # Grigio di default se il colore non è riconosciuto

markers_added = 0
for _, row in df.iterrows():
    try:
        # Converte le coordinate (gestendo la virgola decimale)
        lat = float(str(row[COL_LAT]).replace(',', '.'))
        lon = float(str(row[COL_LON]).replace(',', '.'))

        # Salta coordinate palesemente fuori zona
        if not (42 < lat < 45 and 9 < lon < 13):
            continue

        colore = get_marker_color(row[COL_COLORE])
        
        # Crea il popup con tutte le informazioni della riga
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
        # Ignora righe con coordinate non convertibili a numero
        continue

# Messaggio di feedback nella sidebar
st.sidebar.success(f"🎉 Aggiunti {markers_added} marker sulla mappa.")
if markers_added == 0:
    st.sidebar.error("Nessun marker valido trovato nei dati. Controlla il formato delle colonne 'X' e 'Y'.")

# Titolo e visualizzazione della mappa
st.title("🗺️ Mappa Interattiva – by Bobo")
folium_static(mappa, width=1000, height=700)
