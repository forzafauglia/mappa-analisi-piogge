# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import streamlit.components.v1 as components

# Import per la gestione dei colori
import matplotlib.cm as cm
import matplotlib.colors as colors

# --- 1. FUNZIONE PER GOOGLE ANALYTICS ---
def inject_ga():
    """Inserisce lo script di Google Analytics nell'app."""
    GA_MEASUREMENT_ID = st.secrets.get("ga_measurement_id", "")
    if GA_MEASUREMENT_ID:
        GA_SCRIPT = f"""
            <script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
            <script>
              window.dataLayer = window.dataLayer || [];
              function gtag(){{dataLayer.push(arguments);}}
              gtag('js', new Date());
              gtag('config', '{GA_MEASUREMENT_ID}');
            </script>
        """
        components.html(GA_SCRIPT, height=0)

# --- 2. CONFIGURAZIONE E TITOLO ---
st.set_page_config(page_title="Analisi Piogge", layout="wide")
inject_ga() # Inietta il codice di Google Analytics
st.title("?? Analisi Precipitazioni per Stazione ??")

# --- 3. CARICAMENTO E PREPARAZIONE DATI ---
SHEET_URL = (
    "https://docs.google.com/spreadsheets/"
    "d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(SHEET_URL, na_values=["#N/D", "#N/A"])
    df.columns = df.columns.str.strip()
    return df

df = load_data()

# Identifichiamo le colonne per nome (più robusto che per indice)
# Indici Python: 2, 3, 4, 9, 12, 13, 14, 15, 16
# Corrispondono a:
COLS_TO_SHOW_NAMES = [
    'COMUNE', 'ALTITUDINE', 'LEGENDA', 'SBALZO TERMICO MIGLIORE', 
    'PIOGGE RESIDUA', 'Piogge entro 5 gg', 'Piogge entro 10 gg', 
    'Totale Piogge Mensili', 'MEDIA PORCINI CALDO BASE'
]
# Colonna per il colore e il filtro
COL_PIOGGIA = 'Piogge entro 5 gg'

# Pulizia della colonna numerica: sostituisce la virgola e converte in numero
# 'coerce' imposta a NaN (Not a Number) i valori che non riesce a convertire
df[COL_PIOGGIA] = pd.to_numeric(df[COL_PIOGGIA].str.replace(',', '.', na=False), errors='coerce')
df.dropna(subset=[COL_PIOGGIA, 'X', 'Y'], inplace=True) # Rimuove righe con dati mancanti essenziali

# --- 4. FILTRI NELLA SIDEBAR ---
st.sidebar.title("Filtri e Opzioni")
min_pioggia = int(df[COL_PIOGGIA].min())
max_pioggia = int(df[COL_PIOGGIA].max())

filtro_pioggia = st.sidebar.slider(
    f"Mostra stazioni con '{COL_PIOGGIA}' >= a:",
    min_value=min_pioggia,
    max_value=max_pioggia,
    value=min_pioggia, # Valore di default
    step=1
)

# Applica il filtro al DataFrame
df_filtrato = df[df[COL_PIOGGIA] >= filtro_pioggia].copy()

st.sidebar.info(f"Mostrate **{len(df_filtrato)}** stazioni su **{len(df)}** totali.")


# --- 5. LOGICA DEI COLORI E CREAZIONE MAPPA ---

# Crea una scala di colori da celeste a blu scuro
# Usiamo il valore massimo del set di dati *originale* per una scala consistente
norm = colors.Normalize(vmin=df[COL_PIOGGIA].min(), vmax=df[COL_PIOGGIA].max())
colormap = cm.get_cmap('Blues')

def get_color_from_value(value):
    """Converte un valore numerico in un colore esadecimale."""
    return colors.to_hex(colormap(norm(value)))

mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)

if not df_filtrato.empty:
    for _, row in df_filtrato.iterrows():
        try:
            lat = float(str(row['Y']).replace(',', '.'))
            lon = float(str(row['X']).replace(',', '.'))
            
            valore_pioggia = row[COL_PIOGGIA]
            colore = get_color_from_value(valore_pioggia)
            
            # Costruisci il popup solo con le colonne richieste
            popup_html = f"<h4>{row['STAZIONE']}</h4><hr>"
            for col_name in COLS_TO_SHOW_NAMES:
                if col_name in row and pd.notna(row[col_name]):
                    popup_html += f"<b>{col_name}</b>: {row[col_name]}<br>"
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=6, # Raggio fisso, il colore indica il valore
                color=colore,
                fill=True,
                fill_color=colore,
                fill_opacity=0.9,
                popup=folium.Popup(popup_html, max_width=350)
            ).add_to(mappa)
        except (ValueError, TypeError):
            continue
else:
    st.warning("Nessuna stazione corrisponde ai filtri selezionati.")

# Aggiunta di una legenda per i colori
# (Questa è una legenda semplificata, si può rendere più complessa)
st.markdown(f"""
<div style="position: fixed; bottom: 20px; left: 20px; z-index:1000; background-color: white; padding: 10px; border-radius: 5px; border: 1px solid grey;">
    <b>Legenda: {COL_PIOGGIA}</b><br>
    <i style="background: {get_color_from_value(min_pioggia)};">       </i> Min ({min_pioggia})<br>
    <i style="background: {get_color_from_value(max_pioggia)};">       </i> Max ({max_pioggia})
</div>
""", unsafe_allow_html=True)

# Visualizza la mappa
folium_static(mappa, width=1000, height=700)