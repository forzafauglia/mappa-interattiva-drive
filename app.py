import streamlit as st
import pandas as pd

# Link CSV del Google Sheet
sheet_url = (
    "https://docs.google.com/spreadsheets/d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(sheet_url)
    return df

st.title("🔍 Diagnostica colonne Google Sheet")

try:
    df = load_data()
    st.success("✅ Dati caricati correttamente!")
    st.write("Ecco i primi 5 record:")
    st.dataframe(df.head())

    st.write("🔑 Nomi reali delle colonne nel foglio:")
    for i, col in enumerate(df.columns):
        st.write(f"{i+1}. '{col}'")
except Exception as e:
    st.error(f"❌ Errore durante il caricamento dei dati:\n\n{e}")
