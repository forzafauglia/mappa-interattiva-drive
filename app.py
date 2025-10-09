# --- 1. IMPORT NECESSARI ---
import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import Geocoder
from streamlit_folium import folium_static
from datetime import datetime
import re
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from branca.colormap import linear

# --- 2. CONFIGURAZIONE CENTRALE E FUNZIONI DI BASE ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRxitMYpUqvX6bxVaukG01lJDC8SUfXtr47Zv5ekR1IzfR1jmhUilBsxZPJ8hrktVHrBh6hUUWYUtox/pub?output=csv"

COLONNE_FILTRO_RIEPILOGO = [
    "LEGENDA_TEMPERATURA_MEDIANA", "LEGENDA_PIOGGE_RESIDUA", "LEGENDA_MEDIA_PORCINI_CALDO_BASE", "LEGENDA_MEDIA_PORCINI_FREDDO_BASE",
    "LEGENDA_MEDIA_PORCINI_CALDO_ST_MIGLIORE", "LEGENDA_MEDIA_PORCINI_FREDDO_ST_MIGLIORE",
    "LEGENDA_MEDIA_PORCINI_CALDO_ST_SECONDO", "LEGENDA_MEDIA_PORCINI_FREDDO_ST_SECONDO"
]

def check_password():
    def password_entered():
        if st.session_state.get("password") == st.secrets.get("password"): st.session_state["password_correct"] = True; del st.session_state["password"]
        else: st.session_state["password_correct"] = False
    if st.session_state.get("password_correct", False): return True
    st.text_input("Inserisci la password per accedere:", type="password", on_change=password_entered, key="password")
    if "password" in st.session_state and st.session_state.get("password") and not st.session_state.get("password_correct", False): st.error("😕 Password errata. Riprova.")
    if not st.session_state.get("password_correct", False): st.stop()
    return False

@st.cache_resource
def get_view_counter(): return {"count": 0}

@st.cache_data(ttl=3600)
def load_and_prepare_data(url: str):
    load_timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        df = pd.read_csv(url, na_values=["#N/D", "#N/A"], dtype=str, header=0, skiprows=[1])
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(map(str, col)).strip() for col in df.columns.values]
        cleaned_cols = {}
        for col in df.columns:
            cleaned_name = re.sub(r'\[.*?\]|\(.*?\)|\'', '', str(col)).strip().replace(' ', '_').upper()
            if col.upper().startswith('LEGENDA_'):
                base_name = re.sub(r'^LEGENDA_', '', cleaned_name)
                cleaned_cols[col] = f"LEGENDA_{base_name}"
            else:
                cleaned_cols[col] = cleaned_name
        df.rename(columns=cleaned_cols, inplace=True)
        df = df.loc[:, ~df.columns.duplicated()]

        for sbalzo_col, suffisso in [("LEGENDA_SBALZO_TERMICO_MIGLIORE", "MIGLIORE"), ("LEGENDA_SBALZO_TERMICO_SECONDO", "SECONDO")]:
            if sbalzo_col in df.columns:
                split_cols = df[sbalzo_col].str.split(' - ', n=1, expand=True)
                if split_cols.shape[1] == 2:
                    df[f"LEGENDA_SBALZO_NUMERICO_{suffisso}"] = pd.to_numeric(split_cols[0].str.replace(',', '.'), errors='coerce')

        TEXT_COLUMNS = ['STAZIONE', 'LEGENDA_DESCRIZIONE', 'LEGENDA_COMUNE', 'LEGENDA_COLORE', 'LEGENDA_ULTIMO_AGGIORNAMENTO_SHEET', 'LEGENDA_SBALZO_TERMICO_MIGLIORE', 'LEGENDA_SBALZO_TERMICO_SECONDO', 'PORCINI_CALDO_NOTE', 'PORCINI_FREDDO_NOTE', 'SBALZO_TERMICO_MIGLIORE', '2°_SBALZO_TERMICO_MIGLIORE', 'LEGENDA']
        for col in df.columns:
            if col == 'DATA':
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
            elif col not in TEXT_COLUMNS:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce')
        
        temp_cols_to_fill = ['TEMP_MIN', 'TEMP_MAX', 'TEMPERATURA_MEDIANA', 'TEMPERATURA_MEDIANA_MINIMA']
        df_source_temps = df[df['STAZIONE'].str.startswith('TOS', na=False)][['STAZIONE', 'DATA'] + temp_cols_to_fill].copy()
        df_merged = pd.merge(df, df_source_temps, left_on=['LEGENDA', 'DATA'], right_on=['STAZIONE', 'DATA'], how='left', suffixes=('', '_sorgente'))
        for col in temp_cols_to_fill:
            if f'{col}_sorgente' in df_merged.columns:
                df_merged[col] = df_merged[col].fillna(df_merged[f'{col}_sorgente'])
        source_cols_to_drop = ['STAZIONE_sorgente'] + [f'{col}_sorgente' for col in temp_cols_to_fill if f'{col}_sorgente' in df_merged.columns]
        df = df_merged.drop(columns=source_cols_to_drop)
        
        df.dropna(subset=['LONGITUDINE', 'LATITUDINE', 'DATA'], inplace=True, how='any')
        return df, load_timestamp
    except Exception as e:
        st.error(f"Errore critico durante il caricamento dei dati: {e}")
        return None, None

def create_map(tile, location=[43.8, 11.0], zoom=8):
    return folium.Map(location=location, zoom_start=zoom, tiles=tile)

# SOSTITUISCI QUESTA FUNZIONE
def display_main_map(df, last_loaded_ts):
    st.header("🗺️ Mappa Riepilogativa (Situazione Attuale)")
    last_date = df['DATA'].max()
    df_latest = df[df['DATA'] == last_date].copy()
    st.info(f"Visualizzazione dati aggiornati al: **{last_date.strftime('%d/%m/%Y')}**")
    
    st.sidebar.title("Informazioni e Filtri Riepilogo")
    st.sidebar.markdown("---")
    map_tile_options = ["OpenStreetMap", "CartoDB positron"]
    map_tile = st.sidebar.selectbox("Tipo di mappa:", map_tile_options, key="tile_main")
    st.sidebar.markdown("---")
    st.sidebar.subheader("Statistiche")
    counter = get_view_counter()
    st.sidebar.info(f"Visite totali: **{counter['count']}**")
    if last_loaded_ts:
        st.sidebar.info(f"App aggiornata il: **{last_loaded_ts}**")
    if 'LEGENDA_ULTIMO_AGGIORNAMENTO_SHEET' in df_latest.columns and not df_latest['LEGENDA_ULTIMO_AGGIORNAMENTO_SHEET'].empty:
        st.sidebar.info(f"Sheet aggiornato il: **{df_latest['LEGENDA_ULTIMO_AGGIORNAMENTO_SHEET'].iloc[0]}**")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtri Dati Standard")
    df_filtrato = df_latest.copy()
    for colonna in COLONNE_FILTRO_RIEPILOGO:
        if colonna in df_filtrato.columns and not df_filtrato[colonna].dropna().empty:
            max_val = float(df_filtrato[colonna].max())
            slider_label = colonna.replace('LEGENDA_', '').replace('_', ' ').title()
            val_selezionato = st.sidebar.slider(f"Filtra per {slider_label}", 0.0, max_val, (0.0, max_val))
            df_filtrato = df_filtrato[df_filtrato[colonna].fillna(0).between(val_selezionato[0], val_selezionato[1])]
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtri Sbalzo Termico")
    for sbalzo_col, suffisso in [("LEGENDA_SBALZO_NUMERICO_MIGLIORE", "Migliore"), ("LEGENDA_SBALZO_NUMERICO_SECONDO", "Secondo")]:
        if sbalzo_col in df_filtrato.columns and not df_filtrato[sbalzo_col].dropna().empty:
            max_val = float(df_filtrato[sbalzo_col].max())
            val_selezionato = st.sidebar.slider(f"Sbalzo Termico {suffisso}", 0.0, max_val, (0.0, max_val))
            df_filtrato = df_filtrato[df_filtrato[sbalzo_col].fillna(0).between(val_selezionato[0], val_selezionato[1])]
    
    st.sidebar.markdown("---")
    st.sidebar.success(f"Visualizzati {len(df_filtrato)} marker sulla mappa.")
    df_mappa = df_filtrato.dropna(subset=['LATITUDINE', 'LONGITUDINE']).copy()

    if 'map_center' not in st.session_state: st.session_state.map_center = [43.8, 11.0]
    if 'map_zoom' not in st.session_state: st.session_state.map_zoom = 8

    mappa = create_map(map_tile, location=st.session_state.map_center, zoom=st.session_state.map_zoom)
    Geocoder(collapsed=True, placeholder='Cerca un luogo...', add_marker=True).add_to(mappa)
    
    def create_popup_html(row):
        html = """<style>.popup-container{font-family:Arial,sans-serif;font-size:13px;max-height:350px;overflow-y:auto;overflow-x:hidden}h4{margin-top:12px;margin-bottom:5px;color:#0057e7;border-bottom:1px solid #ccc;padding-bottom:3px}table{width:100%;border-collapse:collapse;margin-bottom:10px}td{text-align:left;padding:4px;border-bottom:1px solid #eee}td:first-child{font-weight:bold;color:#333;width:65%}td:last-child{color:#555}.btn-container{text-align:center;margin-top:15px;}.btn{background-color:#007bff;color:white;padding:8px 12px;border-radius:5px;text-decoration:none;font-weight:bold;}</style><div class="popup-container">"""
        groups = {"Info Stazione": ["STAZIONE", "LEGENDA_DESCRIZIONE", "LEGENDA_COMUNE", "LEGENDA_ALTITUDINE"], "Dati Meteo": ["LEGENDA_TEMPERATURA_MEDIANA_MINIMA", "LEGENDA_TEMPERATURA_MEDIANA", "LEGENDA_UMIDITA_MEDIA_7GG", "LEGENDA_PIOGGE_RESIDUA", "LEGENDA_TOTALE_PIOGGE_MENSILI"], "Analisi Base": ["LEGENDA_MEDIA_PORCINI_CALDO_BASE", "LEGENDA_MEDIA_PORCINI_CALDO_BOOST", "LEGENDA_DURATA_RANGE_CALDO", "LEGENDA_CONTEGGIO_GG_ALLA_RACCOLTA_CALDO", "LEGENDA_MEDIA_PORCINI_FREDDO_BASE", "LEGENDA_MEDIA_PORCINI_FREDDO_BOOST", "LEGENDA_DURATA_RANGE_FREDDO", "LEGENDA_CONTEGGIO_GG_ALLA_RACCOLTA_FREDDO"], "Analisi Sbalzo Migliore": ["LEGENDA_SBALZO_TERMICO_MIGLIORE", "LEGENDA_MEDIA_PORCINI_CALDO_ST_MIGLIORE", "LEGENDA_MEDIA_BOOST_CALDO_ST_MIGLIORE", "LEGENDA_GG_ST_MIGLIORE_CALDO", "LEGENDA_MEDIA_PORCINI_FREDDO_ST_MIGLIORE", "LEGENDA_MEDIA_BOOST_FREDDO_ST_MIGLIORE", "LEGENDA_GG_ST_MIGLIORE_FREDDO"], "Analisi Sbalzo Secondo": ["LEGENDA_SBALZO_TERMICO_SECONDO", "LEGENDA_MEDIA_PORCINI_CALDO_ST_SECONDO", "LEGENDA_MEDIA_BOOST_CALDO_ST_SECONDO", "LEGENDA_GG_ST_SECONDO_CALDO", "LEGENDA_MEDIA_PORCINI_FREDDO_ST_SECONDO", "LEGENDA_MEDIA_BOOST_FREDDO_ST_SECONDO", "LEGENDA_GG_ST_SECONDO_FREDDO"]}
        for title, columns in groups.items():
            table_html = "<table>"; has_content = False
            for col_name_actual in columns:
                if col_name_actual in row.index and pd.notna(row[col_name_actual]) and str(row[col_name_actual]).strip() != '':
                    has_content = True; value = row[col_name_actual]
                    col_name_label = col_name_actual.replace('LEGENDA_', '').replace('_', ' ').title()
                    if isinstance(value, (int, float)): value_str = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    else: value_str = str(value)
                    table_html += f"<tr><td>{col_name_label}</td><td>{value_str}</td></tr>"
            table_html += "</table>"
            if has_content: html += f"<h4>{title}</h4>{table_html}"
        
        # --- FIX LINK STORICO con JavaScript ---
        link = f'?station={row["STAZIONE"]}'
        # Usiamo 'onclick' per eseguire JavaScript che cambia l'URL della finestra principale.
        html += f"""
        <div class='btn-container'>
            <a href='#' onclick="window.top.location.href='{link}'; return false;" class='btn'>
                📈 Mostra Storico Stazione
            </a>
        </div></div>"""
        return html
    
    def get_marker_color(val): return {"ROSSO": "red", "GIALLO": "yellow", "ARANCIONE": "orange", "VERDE": "green"}.get(str(val).strip().upper(), "gray")
    
    for _, row in df_mappa.iterrows():
        try:
            lat, lon = float(row['LONGITUDINE']), float(row['LATITUDINE'])
            colore = get_marker_color(row.get('LEGENDA_COLORE', 'gray'))
            popup_html = create_popup_html(row)
            folium.CircleMarker(location=[lat, lon], radius=6, color=colore, fill=True, fill_color=colore, fill_opacity=0.9, popup=folium.Popup(popup_html, max_width=380)).add_to(mappa)
        except (ValueError, TypeError): continue
    
    map_data = folium_static(mappa, width=1000, height=700)
    if isinstance(map_data, dict) and 'center' in map_data and 'zoom' in map_data:
        st.session_state.map_center = map_data['center']
        st.session_state.map_zoom = map_data['zoom']

# SOSTITUISCI QUESTA FUNZIONE
def display_period_analysis(df):
    st.header("📊 Analisi di Periodo con Dati Aggregati")
    st.sidebar.title("Filtri di Periodo")
    map_tile_options = ["OpenStreetMap", "CartoDB positron"]
    map_tile = st.sidebar.selectbox("Tipo di mappa:", map_tile_options, key="tile_period")
    min_date, max_date = df['DATA'].min().date(), df['DATA'].max().date()
    date_range = st.sidebar.date_input("Seleziona un periodo:", value=(max_date, max_date), min_value=min_date, max_value=max_date)
    
    if len(date_range) != 2: st.warning("Seleziona un intervallo di date valido."); st.stop()
    
    start_date, end_date = date_range
    df_filtered = df[df['DATA'].dt.date.between(start_date, end_date)]
    agg_cols = {'TOTALE_PIOGGIA_GIORNO': 'sum', 'LATITUDINE': 'first', 'LONGITUDINE': 'first', 'TEMP_MAX': 'mean', 'TEMP_MIN': 'mean', 'TEMPERATURA_MEDIANA': 'mean'}
    df_agg = df_filtered.groupby('STAZIONE').agg(agg_cols).reset_index().dropna(subset=['LATITUDINE', 'LONGITUDINE'])
    df_agg.rename(columns={'TEMP_MAX': 'MEDIA_TEMP_MAX', 'TEMP_MIN': 'MEDIA_TEMP_MIN', 'TEMPERATURA_MEDIANA': 'MEDIA_TEMP_MEDIANA'}, inplace=True)
    
    df_agg_filtered = df_agg.copy()
    st.sidebar.subheader("Filtri Dati Aggregati")
    if not df_agg_filtered.empty:
        max_rain = float(df_agg_filtered['TOTALE_PIOGGIA_GIORNO'].max()) if not df_agg_filtered['TOTALE_PIOGGIA_GIORNO'].empty else 100.0
        rain_range = st.sidebar.slider("Pioggia Totale (mm)", 0.0, max_rain, (0.0, max_rain))

        max_tmax = float(df_agg_filtered['MEDIA_TEMP_MAX'].max()) if df_agg_filtered['MEDIA_TEMP_MAX'].notna().any() else 40.0
        tmax_range = st.sidebar.slider("Temp. Max Media (°C)", 0.0, max_tmax, (0.0, max_tmax))

        max_tmin = float(df_agg_filtered['MEDIA_TEMP_MIN'].max()) if df_agg_filtered['MEDIA_TEMP_MIN'].notna().any() else 30.0
        min_tmin_slider = -20.0 
        tmin_range = st.sidebar.slider("Temp. Min Media (°C)", min_tmin_slider, max_tmin, (min_tmin_slider, max_tmin))

        max_tmed = float(df_agg_filtered['MEDIA_TEMP_MEDIANA'].max()) if df_agg_filtered['MEDIA_TEMP_MEDIANA'].notna().any() else 35.0
        tmed_range = st.sidebar.slider("Temp. Mediana Media (°C)", 0.0, max_tmed, (0.0, max_tmed))

        df_agg_filtered = df_agg_filtered[df_agg_filtered['TOTALE_PIOGGIA_GIORNO'].between(rain_range[0], rain_range[1])]
        if df_agg_filtered['MEDIA_TEMP_MAX'].notna().any(): df_agg_filtered = df_agg_filtered[df_agg_filtered['MEDIA_TEMP_MAX'].between(tmax_range[0], tmax_range[1])]
        if df_agg_filtered['MEDIA_TEMP_MIN'].notna().any(): df_agg_filtered = df_agg_filtered[df_agg_filtered['MEDIA_TEMP_MIN'].between(tmin_range[0], tmin_range[1])]
        if df_agg_filtered['MEDIA_TEMP_MEDIANA'].notna().any(): df_agg_filtered = df_agg_filtered[df_agg_filtered['MEDIA_TEMP_MEDIANA'].between(tmed_range[0], tmed_range[1])]

    st.info(f"Visualizzando **{len(df_agg_filtered)}** stazioni che corrispondono ai filtri.")
    if df_agg_filtered.empty: st.warning("Nessuna stazione corrisponde ai filtri selezionati."); return
    
    # --- FIX CENTRAGGIO MAPPA ---
    # Usiamo un centro di default (Toscana) se il dataframe è vuoto, altrimenti calcoliamo la media
    default_center = [43.8, 11.0] # LONGITUDINE, LATITUDINE
    map_center = [df_agg_filtered['LONGITUDINE'].mean(), df_agg_filtered['LATITUDINE'].mean()] if not df_agg_filtered.empty else default_center
    mappa = create_map(map_tile, location=map_center, zoom=8)

    min_rain, max_rain = df_agg_filtered['TOTALE_PIOGGIA_GIORNO'].min(), df_agg_filtered['TOTALE_PIOGGIA_GIORNO'].max()
    colormap = linear.YlGnBu_09.scale(vmin=min_rain, vmax=max_rain if max_rain > min_rain else min_rain + 1)
    colormap.caption = 'Totale Piogge (mm) nel Periodo'; mappa.add_child(colormap)
    
    for _, row in df_agg_filtered.iterrows():
        fig = go.Figure(go.Bar(x=['Pioggia Totale'], y=[row['TOTALE_PIOGGIA_GIORNO']], marker_color='#007bff', text=[f"{row['TOTALE_PIOGGIA_GIORNO']:.1f} mm"], textposition='auto'))
        fig.update_layout(title_text=f"<b>{row['STAZIONE']}</b>", title_font_size=14, yaxis_title="mm", width=250, height=200, margin=dict(l=40, r=20, t=40, b=20), showlegend=False)
        config = {'displayModeBar': False}; html_chart = fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)
        
        # --- FIX LINK STORICO con JavaScript ---
        link = f'?station={row["STAZIONE"]}'
        # Usiamo 'onclick' per eseguire JavaScript che cambia l'URL della finestra principale.
        html_button = f"""
        <div style='text-align:center; margin-top:10px;'>
            <a href='#' onclick="window.top.location.href='{link}'; return false;" 
               style='background-color:#28a745;color:white;padding:8px 12px;border-radius:5px;text-decoration:none;font-weight:bold;font-family:Arial,sans-serif;font-size:13px;'>
               📈 Mostra Storico
            </a>
        </div>"""
        full_html_popup = f"<div>{html_chart}{html_button}</div>"
        
        iframe = folium.IFrame(full_html_popup, width=280, height=260)
        popup = folium.Popup(iframe, max_width=300)
        
        lat, lon = float(row['LONGITUDINE']), float(row['LATITUDINE'])
        color = colormap(row['TOTALE_PIOGGIA_GIORNO'])
        tooltip_text = (f"Stazione: {row['STAZIONE']}<br>" f"Pioggia Totale: {row['TOTALE_PIOGGIA_GIORNO']:.1f} mm<br>" f"T.Max Media: {row.get('MEDIA_TEMP_MAX', 'N/D'):.1f}°C<br>" f"T.Min Media: {row.get('MEDIA_TEMP_MIN', 'N/D'):.1f}°C<br>" f"T.Mediana Media: {row.get('MEDIA_TEMP_MEDIANA', 'N/D'):.1f}°C")
        folium.CircleMarker(location=[lat, lon], radius=8, color=color, fill=True, fill_color=color, fill_opacity=0.7, popup=popup, tooltip=tooltip_text).add_to(mappa)
        
    folium_static(mappa, width=1000, height=700)
    with st.expander("Vedi dati aggregati filtrati"): st.dataframe(df_agg_filtered)

if __name__ == "__main__":
    main()

