import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from datetime import datetime

# --- 1. FUNZIONE DI CONTROLLO PASSWORD (INVARIATA) ---
def check_password():
    # ... (il resto della funzione è identico, lo ometto per brevità)
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

# --- Contatore di Visualizzazioni (INVARIATO) ---
@st.cache_resource
def get_view_counter():
    return {"count": 0}
counter = get_view_counter()
counter["count"] += 1

# Esegui il controllo della password
check_password()

# --- 2. IL CODICE DELLA TUA APP ---
st.set_page_config(page_title="Mappa Funghi Protetta", layout="wide")
st.title("🗺️ Mappa Interattiva – by Bobo")

# --- Caricamento Dati (INVARIATO) ---
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

# --- MODIFICA IMPORTANTE: Assicurati che i nomi qui sotto siano IDENTICI a quelli del tuo Sheet
COLONNE_FILTRO = [
    "PIOGGE RESIDUA",
    "MEDIA PORCINI CALDO BASE",
    "MEDIA PORCINI CALDO BOOST",
    "MEDIA PORCINI FREDDO BASE",
    "MEDIA PORCINI FREDDO BOOST",
    "MEDIA PORCINI CALDO BASE DA ST",
    "MEDIA PORCINI FREDDO BASE DA ST"
]

# --- STRUMENTI DI DIAGNOSI (Migliorati) ---
with st.expander("✅ FASE 1: Controlla i Nomi Esatti delle Colonne"):
    st.info("Nomi esatti delle colonne trovati nel file (copia e incolla da qui per correggere la lista `COLONNE_FILTRO` nel codice):")
    st.json(df.columns.tolist())

# --- NUOVO: STRUMENTO DI ANALISI AVANZATA ---
with st.expander("🔬 FASE 2: Analisi Avanzata delle Colonne con Problemi"):
    st.warning("Questo strumento controlla le colonne che danno problemi. Verifica il 'Tipo di Dati' (dtype). Se è 'object', significa che la colonna contiene testo e non può essere usata per un filtro numerico.")
    colonne_problematiche = [
        "MEDIA PORCINI FREDDO BOOST",
        "MEDIA PORCINI CALDO BASE DA ST",
        "MEDIA PORCINI FREDDO BASE DA ST"
    ]
    for col in colonne_problematiche:
        st.markdown(f"--- \n### Analisi per: `{col}`")
        if col in df.columns:
            st.success(f"✔️ Il nome della colonna '{col}' è stato **TROVATO**.")
            st.write(f"**Tipo di Dati (dtype):** `{df[col].dtype}`")
            st.write("**Primi 10 valori trovati nella colonna:**")
            st.dataframe(df[col].head(10))
            if df[col].dtype == 'object':
                st.error("PROBLEMA: Il tipo di dati è 'object' (testo). Controlla nel Google Sheet che in questa colonna ci siano solo numeri e che il separatore decimale sia il punto (.), non la virgola (,).")
        else:
            st.error(f"❌ PROBLEMA: Il nome della colonna '{col}' **NON è stato trovato**. Controlla che sia scritto correttamente nella lista `COLONNE_FILTRO` e confrontalo con la lista nella FASE 1.")


# Convertiamo le colonne in numerico, gestendo eventuali errori
for col in COLONNE_FILTRO:
    if col in df.columns:
        # Sostituiamo le virgole con i punti PRIMA di convertire in numerico
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')


# --- Sidebar ---
st.sidebar.title("Informazioni e Filtri")
# ... (il resto della sidebar e della mappa rimane identico, lo ometto per brevità)
st.sidebar.markdown("---")
st.sidebar.subheader("Statistiche")
st.sidebar.info(f"Visite totali: **{counter['count']}**")
if 'last_loaded' in df.attrs:
    st.sidebar.info(f"Dati aggiornati il: **{df.attrs['last_loaded']}**")

st.sidebar.markdown("---")
st.sidebar.subheader("Filtri Dati")

df_filtrato = df.copy()

for colonna in COLONNE_FILTRO:
    if colonna in df.columns and not df[colonna].dropna().empty:
        max_val = float(df[colonna].max())
        valore_selezionato = st.sidebar.slider(
            label=f"Filtra per {colonna}",
            min_value=0.0,
            max_value=max_val,
            value=(0.0, max_val)
        )
        df_filtrato = df_filtrato[
            (df_filtrato[colonna].fillna(0) >= valore_selezionato[0]) &
            (df_filtrato[colonna].fillna(0) <= valore_selezionato[1])
        ]
    else:
        st.sidebar.warning(f"La colonna per il filtro '{colonna}' non è presente o non contiene dati numerici validi.")

st.sidebar.markdown("---")
st.sidebar.success(f"Visualizzati {len(df_filtrato.dropna(subset=[COL_LAT, COL_LON]))} marker sulla mappa.")

# --- Preparazione e Visualizzazione Mappa (INVARIATA) ---
required_cols = [COL_LAT, COL_LON, COL_COLORE]
if not all(col in df_filtrato.columns for col in required_cols):
    st.error(f"❌ Colonne necessarie non trovate! Assicurati che nel Google Sheet esistano: '{COL_LAT}', '{COL_LON}' e '{COL_COLORE}'.")
    st.stop()

df_filtrato.dropna(subset=[COL_LAT, COL_LON], inplace=True)
mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

def get_marker_color(val):
    val = str(val).strip().upper()
    return {"ROSSO": "red", "GIALLO": "yellow", "ARANCIONE": "orange", "VERDE": "green"}.get(val, "gray")

for _, row in df_filtrato.iterrows():
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
            location=[lat, lon], radius=6, color=colore, fill=True,
            fill_color=colore, fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=350)
        ).add_to(mappa)
    except (ValueError, TypeError):
        continue

folium_static(mappa, width=1000, height=700)
