import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import streamlit.components.v1 as components
import matplotlib.cm as cm
import matplotlib.colors as colors

# --- 1. FUNZIONE PER GOOGLE ANALYTICS ---
def inject_ga():
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
inject_ga()
st.title("💧 Analisi Precipitazioni – by Bobo56043 💧")

# --- 3. CARICAMENTO E PREPARAZIONE DATI ---
SHEET_URL = (
    "https://docs.google.com/spreadsheets/"
    "d/1G4cJPBAYdb8Xv-mHNX3zmVhsz6FqWf_zE14mBXcs5_A/gviz/tq?tqx=out:csv"
)

@st.cache_data(ttl=3600)
def load_and_clean_data():
    df = pd.read_csv(SHEET_URL, na_values=["#N/D", "#N/A"])
    df.columns = df.columns.str.strip()
    return df

try:
    df = load_and_clean_data()
except Exception as e:
    st.error(f"Errore durante il caricamento dei dati: {e}")
    st.stop()

# --- MODIFICA CHIAVE: Lista delle colonne per il popup aggiornata alla tua ultima richiesta ---
COLS_TO_SHOW_NAMES = [
    'DESCRIZIONE', 'COMUNE', 'ALTITUDINE', 'UMIDITA MEDIA 7GG',
    'TEMPERATURA MEDIANA', 'PIOGGE RESIDUA', 'Piogge entro 5 gg',
    'Piogge entro 10 gg', 'Totale Piogge Mensili'
]
# La colonna per il filtro e il colore rimane 'PIOGGE RESIDUA'
COL_FILTRO = 'PIOGGE RESIDUA'

# Pulizia robusta di tutte le colonne numeriche che useremo
# Aggiungiamo tutte le colonne che devono essere trattate come numeri
numeric_cols_to_clean = [
    COL_FILTRO, 'X', 'Y', 'Piogge entro 5 gg', 'Piogge entro 10 gg',
    'Totale Piogge Mensili', 'UMIDITA MEDIA 77GG', 'TEMPERATURA MEDIANA', 'ALTITUDINE'
]
for col in numeric_cols_to_clean:
    if col in df.columns:
        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Rimuove righe con dati mancanti essenziali
df.dropna(subset=[COL_FILTRO, 'X', 'Y'], inplace=True)

# --- 4. FILTRI NELLA SIDEBAR ---
st.sidebar.title("Filtri e Opzioni")
if not df.empty:
    min_val = int(df[COL_FILTRO].min())
    max_val = int(df[COL_FILTRO].max())
    filtro_valore = st.sidebar.slider(
        f"Mostra stazioni con '{COL_FILTRO}' >= a:",
        min_value=min_val,
        max_value=max_val,
        value=min_val,
        step=1
    )
    df_filtrato = df[df[COL_FILTRO] >= filtro_valore].copy()
    st.sidebar.info(f"Mostrate **{len(df_filtrato)}** stazioni su **{len(df)}** totali.")
else:
    st.sidebar.warning("Nessun dato valido da filtrare.")
    df_filtrato = pd.DataFrame()

# --- 5. LOGICA DEI COLORI E CREAZIONE MAPPA ---
mappa = folium.Map(location=[43.5, 11.0], zoom_start=8)
if not df_filtrato.empty:
    norm = colors.Normalize(vmin=df[COL_FILTRO].min(), vmax=df[COL_FILTRO].max())
    colormap = cm.get_cmap('Blues')
    def get_color_from_value(value):
        return colors.to_hex(colormap(norm(value)))

    for _, row in df_filtrato.iterrows():
        try:
            lat = row['Y']
            lon = row['X']
            valore_filtro = row[COL_FILTRO]
            colore = get_color_from_value(valore_filtro)
            
            # Il popup ora userà la nuova lista COLS_TO_SHOW_NAMES
            popup_html = f"<h4>{row.get('STAZIONE', 'N/A')}</h4><hr>"
            for col_name in COLS_TO_SHOW_NAMES:
                if col_name in row and pd.notna(row[col_name]):
                    val = row[col_name]
                    # Formattazione per rendere i numeri più leggibili
                    if isinstance(val, float):
                        popup_html += f"<b>{col_name}</b>: {val:.2f}<br>"
                    else:
                        popup_html += f"<b>{col_name}</b>: {val}<br>"

            folium.CircleMarker(
                location=[lat, lon],
                radius=6,
                color=colore,
                fill=True,
                fill_color=colore,
                fill_opacity=0.9,
                popup=folium.Popup(popup_html, max_width=350)
            ).add_to(mappa)
        except (ValueError, TypeError, KeyError):
            continue
else:
    st.warning("Nessuna stazione corrisponde ai filtri selezionati.")

if not df.empty:
    min_val_legenda = df[COL_FILTRO].min()
    max_val_legenda = df[COL_FILTRO].max()
    norm_legenda = colors.Normalize(vmin=min_val_legenda, vmax=max_val_legenda)
    colormap_legenda = cm.get_cmap('Blues')
    legenda_html = f"""
    <div style="position: fixed; bottom: 20px; left: 20px; z-index:1000; background-color: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 5px; border: 1px solid grey; font-family: sans-serif; font-size: 14px;">
        <b>Legenda: {COL_FILTRO}</b><br>
        <i style="background: {colors.to_hex(colormap_legenda(norm_legenda(min_val_legenda)))}; border: 1px solid #ccc;">       </i> Min ({min_val_legenda:.1f})<br>
        <i style="background: {colors.to_hex(colormap_legenda(norm_legenda(max_val_legenda)))}; border: 1px solid #ccc;">       </i> Max ({max_val_legenda:.1f})
    </div>
    """
    st.markdown(legenda_html, unsafe_allow_html=True)

folium_static(mappa, width=1000, height=700)
