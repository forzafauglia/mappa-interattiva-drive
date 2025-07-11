import streamlit as st
import pandas as pd

@st.cache_data
def load_data():
    # Inserisci qui il tuo URL pubblico (non quello di editing)
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRxUEnVC0Z96lXZ0oSzHpMFdhwFMxiXCSZLb3yo06Fl5A5wB5aJJePSkzO9M9Ju5FRHbck-uLeN6tI7/pub?gid=0&single=true&output=csv"
    df = pd.read_csv(url)
    return df

df = load_data()

st.title("🧪 Diagnostica Google Sheet")
st.write("Prime 5 righe del foglio:")
st.dataframe(df.head())

st.write("Colonne riconosciute:")
st.write(df.columns.tolist())
