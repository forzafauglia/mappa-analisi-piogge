import streamlit as st
import pandas as pd
import pydeck as pdk  # ### NUOVO ###: Importiamo pydeck
import streamlit.components.v1 as components
import matplotlib.cm as cm
import matplotlib.colors as colors

# --- 1. FUNZIONE PER GOOGLE ANALYTICS ---
# (Questa parte rimane invariata)
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
# (Questa parte rimane invariata)
st.set_page_config(page_title="Analisi Piogge 3D", layout="wide")
inject_ga()
st.title("💧 Analisi Precipitazioni 3D – by Bobo56043 💧")

# --- 3. CARICAMENTO E PREPARAZIONE DATI ---
# (Questa parte rimane invariata)
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

COLS_TO_SHOW_NAMES = [
    'DESCRIZIONE', 'COMUNE', 'ALTITUDINE', 'UMIDITA MEDIA 7GG',
    'TEMPERATURA MEDIANA', 'PIOGGE RESIDUA', 'Piogge entro 5 gg',
    'Piogge entro 10 gg', 'Totale Piogge Mensili'
]
COL_FILTRO = 'PIOGGE RESIDUA'

numeric_cols_to_clean = [
    COL_FILTRO, 'X', 'Y', 'Piogge entro 5 gg', 'Piogge entro 10 gg',
    'Totale Piogge Mensili', 'UMIDITA MEDIA 7GG', 'TEMPERATURA MEDIANA', 'ALTITUDINE'
]
for col in numeric_cols_to_clean:
    if col in df.columns:
        # Errore comune: 'UMIDITA MEDIA 77GG' nel tuo codice originale, correggo a 7GG
        if col == 'UMIDITA MEDIA 77GG':
            df.rename(columns={'UMIDITA MEDIA 77GG': 'UMIDITA MEDIA 7GG'}, inplace=True)
            col = 'UMIDITA MEDIA 7GG'
        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce')

df.dropna(subset=[COL_FILTRO, 'X', 'Y'], inplace=True)

# --- 4. FILTRI NELLA SIDEBAR ---
# (Questa parte rimane invariata)
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

# --- 5. LOGICA DEI COLORI E CREAZIONE MAPPA 3D CON PYDECK --- ### MODIFICATO ###

if not df_filtrato.empty:
    # Definiamo la vista iniziale della mappa (posizione della "camera")
    # L'argomento 'pitch' è quello che crea l'angolo 3D
    view_state = pdk.ViewState(
        latitude=43.5,
        longitude=11.0,
        zoom=7,
        pitch=45, # Angolo della visuale, 0 è dall'alto, 60 è molto inclinato
        bearing=0
    )

    # Creiamo una funzione per mappare i valori a un colore, come prima
    # Pydeck vuole colori nel formato [R, G, B, A] con valori da 0 a 255
    norm = colors.Normalize(vmin=df[COL_FILTRO].min(), vmax=df[COL_FILTRO].max())
    colormap = cm.get_cmap('Blues')

    def get_color_array_from_value(value):
        rgb_tuple = colormap(norm(value))[:3]  # Prende i valori R, G, B (0-1)
        return [int(c * 255) for c in rgb_tuple] # Converte in formato 0-255

    # Applichiamo la funzione per creare una nuova colonna 'colore' nel DataFrame
    df_filtrato['colore'] = df_filtrato[COL_FILTRO].apply(get_color_array_from_value)

    # Definiamo il "Layer" che disegnerà le colonne 3D
    # Ogni riga del DataFrame diventerà una colonna sulla mappa
    column_layer = pdk.Layer(
        'ColumnLayer',  # Tipo di layer per le colonne 3D
        data=df_filtrato,
        get_position='[X, Y]',  # Nomi delle colonne per longitudine e latitudine
        get_elevation=COL_FILTRO, # L'altezza della colonna è data da questo valore
        elevation_scale=200,     # Moltiplicatore per l'altezza (da aggiustare)
        radius=1000,              # Raggio delle colonne in metri
        get_fill_color='colore',  # Colore di riempimento dalla colonna che abbiamo creato
        pickable=True,            # Rende le colonne cliccabili per il tooltip
        auto_highlight=True,      # Evidenzia la colonna al passaggio del mouse
    )

    # Definiamo il contenuto del tooltip (le informazioni che appaiono al passaggio del mouse)
    # È molto più pulito che creare stringhe HTML a mano!
    tooltip_data = {col: f"{{{col}}}" for col in COLS_TO_SHOW_NAMES}
    tooltip_html = "<br/>".join([f"<b>{k}</b>: {v}" for k, v in tooltip_data.items()])
    tooltip = {"html": tooltip_html, "style": {"backgroundColor": "steelblue", "color": "white"}}


    # Creiamo l'oggetto mappa "Deck" combinando vista, layer e tooltip
    r = pdk.Deck(
        layers=[column_layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/light-v9', # Stile della mappa di base
        tooltip=tooltip
    )

    # Mostriamo la mappa 3D in Streamlit
    st.pydeck_chart(r)

    # La legenda HTML di Folium non funziona più, quindi ne creiamo una simile con st.markdown
    min_val_legenda = df[COL_FILTRO].min()
    max_val_legenda = df[COL_FILTRO].max()
    legenda_html = f"""
    <div style="position: fixed; bottom: 20px; left: 20px; z-index:1000; background-color: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 5px; border: 1px solid grey; font-family: sans-serif; font-size: 14px;">
        <b>Legenda: {COL_FILTRO}</b><br>
        <div style="display: flex; align-items: center; margin-top: 5px;">
            <div style="width: 20px; height: 20px; background: {colors.to_hex(colormap(norm(min_val_legenda)))}; border: 1px solid #ccc; margin-right: 5px;"></div>
            <span>Min ({min_val_legenda:.1f})</span>
        </div>
        <div style="display: flex; align-items: center; margin-top: 5px;">
            <div style="width: 20px; height: 20px; background: {colors.to_hex(colormap(norm(max_val_legenda)))}; border: 1px solid #ccc; margin-right: 5px;"></div>
            <span>Max ({max_val_legenda:.1f})</span>
        </div>
    </div>
    """
    # L'integrazione di una legenda con Pydeck è meno diretta. Questo è un "workaround"
    # che funziona bene in Streamlit.
    st.markdown(legenda_html, unsafe_allow_html=True)


else:
    st.warning("Nessuna stazione corrisponde ai filtri selezionati.")
