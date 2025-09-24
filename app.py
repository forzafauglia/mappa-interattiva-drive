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
        if st.session_state.get("password_correct") is False and "password" in st.session_state and st.session_state["password"] != "":
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
if check_password():

    # --- 2. IL CODICE DELL'APP ---
    st.set_page_config(page_title="Mappa Funghi Protetta", layout="wide")
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

    # --- PRE-ELABORAZIONE E INIZIALIZZAZIONE DATI SBALZO TERMICO ---
    sbalzo_cols_map = {
        "SBALZO TERMICO MIGLIORE": "Migliore",
        "SBALZO TERMICO SECONDO": "Secondo"
    }
    for col_originale, suffisso in sbalzo_cols_map.items():
        if col_originale in df.columns:
            split_cols = df[col_originale].str.split(' - ', n=1, expand=True)
            col_numerica = f"Sbalzo Numerico {suffisso}"
            df[col_numerica] = pd.to_numeric(split_cols[0].str.replace(',', '.'), errors='coerce')
            col_data = f"Data Sbalzo {suffisso}"
            df[col_data] = pd.to_datetime(split_cols[1], format='%d/%m/%Y', errors='coerce')

            # Riempi i valori numerici mancanti con 0
            df[col_numerica] = df[col_numerica].fillna(0)

            # Riempi le date mancanti con la data PIÙ VECCHIA trovata nella colonna
            if not df[col_data].dropna().empty:
                min_date_in_col = df[col_data].min()
                df[col_data] = df[col_data].fillna(min_date_in_col)

    # --- MODIFICA: LISTA FILTRI STANDARD AGGIORNATA COME RICHIESTO ---
    COLONNE_FILTRO = [
        "TEMPERATURA MEDIANA",
        "PIOGGE RESIDUA",
        "Piogge entro 5 gg",
        "Piogge entro 10 gg",
        "MEDIA PORCINI CALDO BASE",
        "MEDIA PORCINI FREDDO BASE",
        "MEDIA PORCINI CALDO ST MIGLIORE",
        "MEDIA PORCINI FREDDO ST MIGLIORE",
        "MEDIA PORCINI CALDO ST SECONDO",
        "MEDIA PORCINI FREDDO ST SECONDO"
    ]
    
    # Sezione di preparazione (invariata)
    COLONNE_FILTRO_ESISTENTI = [col for col in COLONNE_FILTRO if col in df.columns]
    for col in COLONNE_FILTRO_ESISTENTI:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')

    # --- Sidebar ---
    st.sidebar.title("Informazioni e Filtri")
    st.sidebar.markdown("---")
    st.sidebar.subheader("Statistiche")
    st.sidebar.info(f"Visite totali: **{counter['count']}**")
    if 'last_loaded' in df.attrs:
        st.sidebar.info(f"Dati aggiornati il: **{df.attrs['last_loaded']}**")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtri Dati Standard")
    
    df_filtrato = df.copy()

    # Ciclo per i filtri numerici standard
    for colonna in COLONNE_FILTRO_ESISTENTI:
        if not df[colonna].dropna().empty:
            min_val, max_val = float(df[colonna].min()), float(df[colonna].max())
            val_selezionato = st.sidebar.slider(
                f"Filtra per {colonna}", 0.0, max_val, (0.0, max_val)
            )
            df_filtrato = df_filtrato[
                (df_filtrato[colonna].fillna(0) >= val_selezionato[0]) &
                (df_filtrato[colonna].fillna(0) <= val_selezionato[1])
            ]

    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtri Sbalzo Termico")

    # Ciclo per i filtri avanzati dello sbalzo termico
    for col_originale, suffisso in sbalzo_cols_map.items():
        col_numerica = f"Sbalzo Numerico {suffisso}"
        col_data = f"Data Sbalzo {suffisso}"

        if col_numerica in df_filtrato.columns and not df_filtrato[col_numerica].dropna().empty:
            st.sidebar.markdown(f"**{suffisso}**")
            min_val, max_val = float(df_filtrato[col_numerica].min()), float(df_filtrato[col_numerica].max())
            val_selezionato = st.sidebar.slider(
                f"Valore Sbalzo {suffisso}", 0.0, max_val, (0.0, max_val)
            )
            df_filtrato = df_filtrato[
                (df_filtrato[col_numerica].fillna(0) >= val_selezionato[0]) &
                (df_filtrato[col_numerica].fillna(0) <= val_selezionato[1])
            ]
        
        if col_data in df_filtrato.columns and not df_filtrato[col_data].dropna().empty:
            min_data, max_data = df_filtrato[col_data].min(), df_filtrato[col_data].max()
            data_selezionata = st.sidebar.date_input(
                f"Data Sbalzo {suffisso}",
                value=(min_data, max_data),
                min_value=min_data,
                max_value=max_data,
                key=f"date_{suffisso}"
            )
            if len(data_selezionata) == 2:
                df_filtrato = df_filtrato[
                    (df_filtrato[col_data].dt.date >= data_selezionata[0]) &
                    (df_filtrato[col_data].dt.date <= data_selezionata[1])
                ]

    st.sidebar.markdown("---")
    st.sidebar.success(f"Visualizzati {len(df_filtrato.dropna(subset=[COL_LAT, COL_LON]))} marker sulla mappa.")

    # --- Preparazione e Visualizzazione Mappa ---
    required_cols = [COL_LAT, COL_LON, COL_COLORE]
    if not all(col in df_filtrato.columns for col in required_cols):
        st.error(f"❌ Colonne necessarie non trovate! Controlla che nel file esistano '{COL_LAT}', '{COL_LON}' e '{COL_COLORE}'.")
        st.stop()

    df_mappa = df_filtrato.dropna(subset=[COL_LAT, COL_LON]).copy()
    mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

    def get_marker_color(val):
        val = str(val).strip().upper()
        return {"ROSSO": "red", "GIALLO": "yellow", "ARANCIONE": "orange", "VERDE": "green"}.get(val, "gray")

    for _, row in df_mappa.iterrows():
        try:
            lat = float(str(row[COL_LAT]).replace(',', '.'))
            lon = float(str(row[COL_LON]).replace(',', '.'))
            if not (42 < lat < 45 and 9 < lon < 13):
                continue
            colore = get_marker_color(row[COL_COLORE])
            
            popup_html = ""
            for col_name, col_value in row.items():
                # Non mostriamo le colonne "virtuali" che abbiamo creato
                if 'Sbalzo Numerico' not in col_name and 'Data Sbalzo' not in col_name:
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
