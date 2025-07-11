import streamlit as st
import pandas as pd

st.set_page_config(page_title="Diagnostica Google Sheet", layout="wide")

# URL del tuo Google Sheet come CSV
sheet_url = "https://docs.google.com/spreadsheets/d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=3600)
def load_data():
    return pd.read_csv(sheet_url)

# App principale
st.title("🔍 Diagnostica colonne del Google Sheet")

try:
    df = load_data()

    st.success("✅ Dati caricati correttamente!")
    st.subheader("📌 Prime 5 righe del foglio:")
    st.dataframe(df.head())

    st.subheader("📋 Elenco delle colonne:")
    for i, col in enumerate(df.columns):
        st.markdown(f"**{i+1}.** `{col}`")
except Exception as e:
    st.error("❌ Errore durante il caricamento o la visualizzazione del foglio.")
    st.exception(e)
