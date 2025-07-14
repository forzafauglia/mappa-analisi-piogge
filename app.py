import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("🕵️‍♀️ Modalità Diagnostica 🕵️‍♀️")

# URL del tuo Google Sheet
SHEET_URL = (
    "https://docs.google.com/spreadsheets/"
    "d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)

st.write("Sto provando a caricare i dati da questo URL:", SHEET_URL)

try:
    # Carichiamo i dati nel modo più semplice possibile
    df = pd.read_csv(SHEET_URL)
    
    st.success("✅ Dati caricati con successo! Ora analizzo la struttura.")
    
    st.subheader("1. Nomi Esatti delle Colonne (così come letti da Pandas)")
    st.write("Questa è la lista dei nomi delle colonne. Controlla spazi extra o caratteri strani.")
    
    # Stampiamo la lista per vederla chiaramente
    column_list = df.columns.tolist()
    st.code(column_list)
    
    st.subheader("2. Tipi di Dati delle Colonne (`df.dtypes`)")
    st.write("Questo ci dice come Pandas ha interpretato ogni colonna (numero, testo, ecc.).")
    st.code(df.dtypes)
    
    st.subheader("3. Prime 5 Righe del DataFrame (`df.head()`)")
    st.write("Questo ci mostra se la prima riga di dati è corretta o se è l'intestazione.")
    st.dataframe(df.head())
    
except Exception as e:
    st.error(f"❌ Si è verificato un errore durante il caricamento o l'analisi iniziale dei dati.")
    st.error("Dettagli dell'errore:")
    st.exception(e)