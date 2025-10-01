import streamlit as st
import pandas as pd
import folium
from folium.plugins import Geocoder # <-- 1. NUOVO IMPORT
from streamlit_folium import folium_static
from datetime import datetime
import requests

# --- 1. FUNZIONE DI CONTROLLO PASSWORD (invariato) ---
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

# --- Contatore di Visualizzazioni (invariato) ---
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
    
    # --- Caricamento Dati e Pre-Elaborazione ---
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
    COL_LAT = "Y"; COL_LON = "X"; COL_COLORE = "COLORE"
    COLONNE_NUMERICHE = [ "TEMPERATURA MEDIANA", "PIOGGE RESIDUA", "Piogge entro 5 gg", "Piogge entro 10 gg", "MEDIA PORCINI CALDO BASE", "MEDIA PORCINI FREDDO BASE", "MEDIA PORCINI CALDO ST MIGLIORE", "MEDIA PORCINI FREDDO ST MIGLIORE", "MEDIA PORCINI CALDO ST SECONDO", "MEDIA PORCINI FREDDO ST SECONDO", "TEMPERATURA MEDIANA MINIMA", "UMIDITA MEDIA 7GG", "Totale Piogge Mensili", "MEDIA PORCINI CALDO BOOST", "DURATA RANGE CALDO", "CONTEGGIO GG ALLA RACCOLTA CALDO", "MEDIA PORCINI FREDDO BOOST", "DURATA RANGE FREDDO", "CONTEGGIO GG ALLA RACCOLTA FREDDO", "MEDIA BOOST CALDO ST MIGLIORE", "GG ST MIGLIORE CALDO", "MEDIA BOOST FREDDO ST MIGLIORE", "GG ST MIGLIORE FREDDO", "MEDIA BOOST CALDO ST SECONDO", "GG ST SECONDO CALDO", "MEDIA BOOST FREDDO ST SECONDO", "GG ST SECONDO FREDDO", "ALTITUDINE" ]
    
    @st.cache_data(ttl=3600)
    def load_data():
        try:
            df = pd.read_csv(SHEET_URL, na_values=["#N/D", "#N/A"], dtype=str)
            df.columns = df.columns.str.strip()
            df.attrs['last_loaded'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            return df
        except Exception as e:
            st.error(f"Impossibile caricare i dati dal Google Sheet. Errore: {e}"); return pd.DataFrame()
            
    df = load_data()
    if df.empty: st.warning("Il DataFrame è vuoto o non è stato possibile caricarlo."); st.stop()
        
    sbalzo_cols_map = { "SBALZO TERMICO MIGLIORE": "Migliore", "SBALZO TERMICO SECONDO": "Secondo" }
    for col_originale, suffisso in sbalzo_cols_map.items():
        if col_originale in df.columns:
            split_cols = df[col_originale].str.split(' - ', n=1, expand=True)
            col_numerica = f"Sbalzo Numerico {suffisso}"; df[col_numerica] = pd.to_numeric(split_cols[0].str.replace(',', '.'), errors='coerce')
            col_data = f"Data Sbalzo {suffisso}"; df[col_data] = pd.to_datetime(split_cols[1], format='%d/%m/%Y', errors='coerce')
            df[col_numerica] = df[col_numerica].fillna(0)
            if not df[col_data].dropna().empty:
                min_date_in_col = df[col_data].min(); df[col_data] = df[col_data].fillna(min_date_in_col)
                
    for col in COLONNE_NUMERICHE:
        if col in df.columns: df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
            
    COLONNE_FILTRO = [ "TEMPERATURA MEDIANA", "PIOGGE RESIDUA", "Piogge entro 5 gg", "Piogge entro 10 gg", "MEDIA PORCINI CALDO BASE", "MEDIA PORCINI FREDDO BASE", "MEDIA PORCINI CALDO ST MIGLIORE", "MEDIA PORCINI FREDDO ST MIGLIORE", "MEDIA PORCINI CALDO ST SECONDO", "MEDIA PORCINI FREDDO ST SECONDO" ]
    COLONNE_FILTRO_ESISTENTI = [col for col in COLONNE_FILTRO if col in df.columns]

    layers_geojson = [
        { "url": "https://raw.githubusercontent.com/forzafauglia/mappa-interattiva-drive/main/Bobo1.json", "name": "Punti Bobo 1", "style": {'color': '#007bff'} },
        { "url": "https://raw.githubusercontent.com/forzafauglia/mappa-interattiva-drive/main/Bobo2.json", "name": "Punti Bobo 2", "style": {'color': '#17a2b8'} },
        { "url": "https://raw.githubusercontent.com/forzafauglia/mappa-interattiva-drive/main/Professore1.json", "name": "Punti Professore 1", "style": {'color': '#dc3545'} },
        { "url": "https://raw.githubusercontent.com/forzafauglia/mappa-interattiva-drive/main/Professore2.json", "name": "Punti Professore 2", "style": {'color': '#fd7e14'} },
        { "url": "https://raw.githubusercontent.com/forzafauglia/mappa-interattiva-drive/main/Wikiloc1.json", "name": "Punti Wikiloc 1", "style": {'color': '#28a745'} },
        { "url": "https://raw.githubusercontent.com/forzafauglia/mappa-interattiva-drive/main/Wikiloc2.json", "name": "Punti Wikiloc 2", "style": {'color': '#6f42c1'} }
    ]

    # --- Sidebar ---
    st.sidebar.title("Informazioni e Filtri")
    st.sidebar.markdown("---")
    st.sidebar.subheader("Statistiche")
    st.sidebar.info(f"Visite totali: **{counter['count']}**")
    if 'last_loaded' in df.attrs:
        st.sidebar.info(f"App aggiornata il: **{df.attrs['last_loaded']}**")
    if 'ULTIMO_AGGIORNAMENTO_SHEET' in df.columns and not df['ULTIMO_AGGIORNAMENTO_SHEET'].empty:
        last_sheet_update = df['ULTIMO_AGGIORNAMENTO_SHEET'].iloc[0]
        st.sidebar.info(f"Sheet aggiornato il: **{last_sheet_update}**")
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtri Dati Standard")
    df_filtrato = df.copy()
    for colonna in COLONNE_FILTRO_ESISTENTI:
        if not df[colonna].dropna().empty:
            min_val, max_val = float(df[colonna].min()), float(df[colonna].max()); val_selezionato = st.sidebar.slider(f"Filtra per {colonna}", 0.0, max_val, (0.0, max_val)); df_filtrato = df_filtrato[(df_filtrato[colonna].fillna(0) >= val_selezionato[0]) & (df_filtrato[colonna].fillna(0) <= val_selezionato[1])]
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtri Sbalzo Termico")
    for col_originale, suffisso in sbalzo_cols_map.items():
        col_numerica = f"Sbalzo Numerico {suffisso}"; col_data = f"Data Sbalzo {suffisso}"
        if col_numerica in df.columns and not df[col_numerica].dropna().empty:
            st.sidebar.markdown(f"**{suffisso}**"); min_val, max_val = float(df[col_numerica].min()), float(df[col_numerica].max()); val_selezionato = st.sidebar.slider(f"Valore Sbalzo {suffisso}", 0.0, max_val, (0.0, max_val)); df_filtrato = df_filtrato[(df_filtrato[col_numerica].fillna(0) >= val_selezionato[0]) & (df_filtrato[col_numerica].fillna(0) <= val_selezionato[1])]
        if col_data in df.columns and not df[col_data].dropna().empty:
            min_data, max_data = df[col_data].min(), df[col_data].max(); data_selezionata = st.sidebar.date_input(f"Data Sbalzo {suffisso}", value=(min_data, max_data), min_value=min_data, max_value=max_data, key=f"date_{suffisso}")
            if len(data_selezionata) == 2: df_filtrato = df_filtrato[(df_filtrato[col_data].dt.date >= data_selezionata[0]) & (df_filtrato[col_data].dt.date <= data_selezionata[1])]
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtri Livelli Mappa")
    for layer in layers_geojson:
        layer['is_visible'] = st.sidebar.checkbox(label=layer["name"], value=False, key=f"geojson_{layer['name']}")
    st.sidebar.markdown("---")
    st.sidebar.success(f"Visualizzati {len(df_filtrato.dropna(subset=[COL_LAT, COL_LON]))} marker sulla mappa.")

    # --- Preparazione e Visualizzazione Mappa ---
    required_cols = [COL_LAT, COL_LON, COL_COLORE];
    if not all(col in df_filtrato.columns for col in required_cols): st.error(f"❌ Colonne necessarie non trovate!"); st.stop()
    df_mappa = df_filtrato.dropna(subset=[COL_LAT, COL_LON]).copy()
    mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

    
    # --- AGGIUNTA DEL BOX DI RICERCA LUOGHI ---
    # Questa riga aggiunge la lente d'ingrandimento e la funzionalità di ricerca
    Geocoder().add_to(mappa)
    # -------------------------------------------
    
    # --- BLOCCO GEOJSON DEFINITIVO E A PROVA DI ERRORE ---
    for layer_info in layers_geojson:
        if layer_info['is_visible']:
            try:
                # Carica i dati dall'URL
                response = requests.get(layer_info['url'])
                response.raise_for_status()
                geojson_data = response.json()

                # Crea un gruppo per contenere tutti gli elementi di questo file
                feature_group = folium.FeatureGroup(name=layer_info['name'])

                # Itera su ogni "feature" (oggetto) nel file
                for feature in geojson_data.get('features', []):
                    geom = feature.get('geometry', {})
                    geom_type = geom.get('type')
                    coords = geom.get('coordinates')
                    
                    if not geom_type or not coords:
                        continue # Salta se la geometria è malformata

                    # Crea un popup e tooltip semplici e sicuri
                    popup_text = layer_info['name']
                    tooltip_text = layer_info['name']
                    
                    if geom_type == 'Point':
                        # GeoJSON è [lon, lat], Folium vuole [lat, lon]
                        location = [coords[1], coords[0]]
                        folium.CircleMarker(
                            location=location,
                            radius=5,
                            color='white',
                            weight=1,
                            fill_color=layer_info['style']['color'],
                            fill_opacity=0.8,
                            popup=popup_text,
                            tooltip=tooltip_text
                        ).add_to(feature_group)
                    
                    elif geom_type in ['LineString', 'MultiLineString']:
                        # Per LineString, le coordinate sono una lista di punti
                        # Per MultiLineString, sono una lista di liste di punti
                        if geom_type == 'LineString':
                            path_data = [coords]
                        else: # MultiLineString
                            path_data = coords
                        
                        for path in path_data:
                            # Inverti lon/lat per ogni punto del tracciato
                            locations = [[point[1], point[0]] for point in path]
                            folium.PolyLine(
                                locations=locations,
                                color=layer_info['style']['color'],
                                weight=3,
                                opacity=0.8,
                                popup=popup_text,
                                tooltip=tooltip_text
                            ).add_to(feature_group)
                
                # Aggiungi l'intero gruppo alla mappa
                feature_group.add_to(mappa)

            except Exception as e:
                st.warning(f"Impossibile caricare o processare il livello '{layer_info['name']}'. Errore: {e}")

    # --- Codice per marker e popup stazioni (invariato) ---
    def create_popup_html(row):
        html = """<style>.popup-container{font-family:Arial,sans-serif;font-size:13px;max-height:350px;overflow-y:auto;overflow-x:hidden}h4{margin-top:12px;margin-bottom:5px;color:#0057e7;border-bottom:1px solid #ccc;padding-bottom:3px}table{width:100%;border-collapse:collapse;margin-bottom:10px}td{text-align:left;padding:4px;border-bottom:1px solid #eee}td:first-child{font-weight:bold;color:#333;width:65%}td:last-child{color:#555}</style><div class="popup-container">"""
        groups = { "Info Stazione": ["Stazione", "DESCRIZIONE", "COMUNE", "ALTITUDINE"], "Dati Meteo": ["TEMPERATURA MEDIANA MINIMA", "TEMPERATURA MEDIANA", "UMIDITA MEDIA 7GG", "PIOGGE RESIDUA", "Piogge entro 5 gg", "Piogge entro 10 gg", "Totale Piogge Mensili"], "Analisi Base": ["MEDIA PORCINI CALDO BASE", "MEDIA PORCINI CALDO BOOST", "DURATA RANGE CALDO", "CONTEGGIO GG ALLA RACCOLTA CALDO", "MEDIA PORCINI FREDDO BASE", "MEDIA PORCINI FREDDO BOOST", "DURATA RANGE FREDDO", "CONTEGGIO GG ALLA RACCOLTA FREDDO"], "Analisi Sbalzo Migliore": ["SBALZO TERMICO MIGLIORE", "MEDIA PORCINI CALDO ST MIGLIORE", "MEDIA BOOST CALDO ST MIGLIORE", "GG ST MIGLIORE CALDO", "MEDIA PORCINI FREDDO ST MIGLIORE", "MEDIA BOOST FREDDO ST MIGLIORE", "GG ST MIGLIORE FREDDO"], "Analisi Sbalzo Secondo": ["SBALZO TERMICO SECONDO", "MEDIA PORCINI CALDO ST SECONDO", "MEDIA BOOST CALDO ST SECONDO", "GG ST SECONDO CALDO", "MEDIA PORCINI FREDDO ST SECONDO", "MEDIA BOOST FREDDO ST SECONDO", "GG ST SECONDO FREDDO"] }
        for title, columns in groups.items():
            table_html = "<table>"; has_content = False
            for col_name in columns:
                if col_name in row and pd.notna(row[col_name]) and str(row[col_name]).strip() != '':
                    has_content = True; value = row[col_name]
                    if isinstance(value, (int, float)): value_str = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    else: value_str = str(value)
                    table_html += f"<tr><td>{col_name.replace('_', ' ')}</td><td>{value_str}</td></tr>"
            table_html += "</table>"
            if has_content: html += f"<h4>{title}</h4>{table_html}"
        html += "</div>"
        return html
    def get_marker_color(val):
        val = str(val).strip().upper(); return {"ROSSO": "red", "GIALLO": "yellow", "ARANCIONE": "orange", "VERDE": "green"}.get(val, "gray")
    for _, row in df_mappa.iterrows():
        try:
            lat = float(str(row[COL_LAT]).replace(',', '.')); lon = float(str(row[COL_LON]).replace(',', '.'))
            if not (42 < lat < 45 and 9 < lon < 13): continue
            colore = get_marker_color(row[COL_COLORE]); popup_html = create_popup_html(row)
            folium.CircleMarker(location=[lat, lon], radius=6, color=colore, fill=True, fill_color=colore, fill_opacity=0.9, popup=folium.Popup(popup_html, max_width=380)).add_to(mappa)
        except (ValueError, TypeError): continue
            
    folium_static(mappa, width=1000, height=700)

