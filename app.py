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

COL_MAP_LEGACY = {
    "Stazione": "Legenda_Stazione", "DESCRIZIONE": "Legenda_DESCRIZIONE", "COMUNE": "Legenda_COMUNE", "ALTITUDINE": "Legenda_ALTITUDINE", "X": "Longitudine", "Y": "Latitudine",
    "TEMPERATURA MEDIANA MINIMA": "Legenda_TEMPERATURA MEDIANA MINIMA", "TEMPERATURA MEDIANA": "Legenda_TEMPERATURA MEDIANA", "UMIDITA MEDIA 7GG": "Legenda_UMIDITA MEDIA 7GG", "PIOGGE RESIDUA": "Legenda_PIOGGE RESIDUA",
    "Totale Piogge Mensili": "Legenda_Totale Piogge Mensili", "MEDIA PORCINI CALDO BASE": "Legenda_MEDIA PORCINI CALDO BASE", "MEDIA PORCINI CALDO BOOST": "Legenda_MEDIA PORCINI CALDO BOOST", "DURATA RANGE CALDO": "Legenda_DURATA RANGE CALDO",
    "CONTEGGIO GG ALLA RACCOLTA CALDO": "Legenda_CONTEGGIO GG ALLA RACCOLTA CALDO", "MEDIA PORCINI FREDDO BASE": "Legenda_MEDIA PORCINI FREDDO BASE", "MEDIA PORCINI FREDDO BOOST": "Legenda_MEDIA PORCINI FREDDO BOOST", "DURATA RANGE FREDDO": "Legenda_DURATA RANGE FREDDO",
    "CONTEGGIO GG ALLA RACCOLTA FREDDO": "Legenda_CONTEGGIO GG ALLA RACCOLTA FREDDO", "SBALZO TERMICO MIGLIORE": "Legenda_SBALZO TERMICO MIGLIORE", "MEDIA PORCINI CALDO ST MIGLIORE": "Legenda_MEDIA PORCINI CALDO ST MIGLIORE", "MEDIA BOOST CALDO ST MIGLIORE": "Legenda_MEDIA BOOST CALDO ST MIGLIORE",
    "GG ST MIGLIORE CALDO": "Legenda_GG ST MIGLIORE CALDO", "MEDIA PORCINI FREDDO ST MIGLIORE": "Legenda_MEDIA PORCINI FREDDO ST MIGLIORE", "MEDIA BOOST FREDDO ST MIGLIORE": "Legenda_MEDIA BOOST FREDDO ST MIGLIORE", "GG ST MIGLIORE FREDDO": "Legenda_GG ST MIGLIORE FREDDO",
    "SBALZO TERMICO SECONDO": "Legenda_SBALZO TERMICO SECONDO", "MEDIA PORCINI CALDO ST SECONDO": "Legenda_MEDIA PORCINI CALDO ST SECONDO", "MEDIA BOOST CALDO ST SECONDO": "Legenda_MEDIA BOOST CALDO ST SECONDO", "GG ST SECONDO CALDO": "Legenda_GG ST SECONDO CALDO",
    "MEDIA PORCINI FREDDO ST SECONDO": "Legenda_MEDIA PORCINI FREDDO ST SECONDO", "MEDIA BOOST FREDDO ST SECONDO": "Legenda_MEDIA BOOST FREDDO ST SECONDO", "GG ST SECONDO FREDDO": "Legenda_GG ST SECONDO FREDDO", "COLORE": "Legenda_COLORE", "ULTIMO_AGGIORNAMENTO_SHEET": "Legenda_ULTIMO_AGGIORNAMENTO_SHEET"
}

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
    if st.session_state.get("password_correct") is False and "password" in st.session_state and st.session_state.get("password"): st.error("😕 Password errata. Riprova.")
    st.stop()
    return False

@st.cache_resource
def get_view_counter(): return {"count": 0}

@st.cache_data(ttl=3600)
def load_and_prepare_data(url: str):
    try:
        df = pd.read_csv(url, na_values=["#N/D", "#N/A"], dtype=str, header=0, skiprows=[1])
        df.attrs['last_loaded'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if isinstance(df.columns, pd.MultiIndex): df.columns = ['_'.join(map(str, col)).strip() for col in df.columns.values]
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
        TEXT_COLUMNS = ['STAZIONE', 'LEGENDA_DESCRIZIONE', 'LEGENDA_COMUNE', 'LEGENDA_COLORE', 'LEGENDA_ULTIMO_AGGIORNAMENTO_SHEET', 'LEGENDA_SBALZO_TERMICO_MIGLIORE', 'LEGENDA_SBALZO_TERMICO_SECONDO', 'PORCINI_CALDO_NOTE', 'PORCINI_FREDDO_NOTE']
        for col in df.columns:
            if col == 'DATA': df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
            elif col not in TEXT_COLUMNS:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce')
        df.dropna(subset=['LONGITUDINE', 'LATITUDINE', 'DATA'], inplace=True, how='any')
        return df
    except Exception as e:
        st.error(f"Errore critico durante il caricamento dei dati: {e}"); return None

def create_map(tile, location=[43.8, 11.0], zoom=8):
    if "Stamen" in tile:
        return folium.Map(location=location, zoom_start=zoom, tiles=tile, attr='&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors')
    return folium.Map(location=location, zoom_start=zoom, tiles=tile)

def display_main_map(df):
    st.header("🗺️ Mappa Riepilogativa (Situazione Attuale)")
    last_date = df['DATA'].max(); df_latest = df[df['DATA'] == last_date].copy()
    st.info(f"Visualizzazione dati aggiornati al: **{last_date.strftime('%d/%m/%Y')}**")
    st.sidebar.title("Informazioni e Filtri Riepilogo"); st.sidebar.markdown("---"); map_tile = st.sidebar.selectbox("Tipo di mappa:", ["OpenStreetMap", "Stamen Terrain", "CartoDB positron"], key="tile_main")
    st.sidebar.markdown("---"); st.sidebar.subheader("Statistiche"); counter = get_view_counter(); st.sidebar.info(f"Visite totali: **{counter['count']}**"); st.sidebar.info(f"App aggiornata il: **{df.attrs['last_loaded']}**")
    if 'LEGENDA_ULTIMO_AGGIORNAMENTO_SHEET' in df_latest.columns and not df_latest['LEGENDA_ULTIMO_AGGIORNAMENTO_SHEET'].empty: st.sidebar.info(f"Sheet aggiornato il: **{df_latest['LEGENDA_ULTIMO_AGGIORNAMENTO_SHEET'].iloc[0]}**")
    st.sidebar.markdown("---"); st.sidebar.subheader("Filtri Dati Standard"); df_filtrato = df_latest.copy()
    for colonna in COLONNE_FILTRO_RIEPILOGO:
        if colonna in df_filtrato.columns and not df_filtrato[colonna].dropna().empty:
            max_val = float(df_filtrato[colonna].max()); slider_label = colonna.replace('LEGENDA_', '').replace('_', ' ').title()
            val_selezionato = st.sidebar.slider(f"Filtra per {slider_label}", 0.0, max_val, (0.0, max_val))
            df_filtrato = df_filtrato[df_filtrato[colonna].fillna(0).between(val_selezionato[0], val_selezionato[1])]
    st.sidebar.markdown("---"); st.sidebar.subheader("Filtri Sbalzo Termico")
    for sbalzo_col, suffisso in [("LEGENDA_SBALZO_NUMERICO_MIGLIORE", "Migliore"), ("LEGENDA_SBALZO_NUMERICO_SECONDO", "Secondo")]:
        if sbalzo_col in df_filtrato.columns and not df_filtrato[sbalzo_col].dropna().empty:
            max_val = float(df_filtrato[sbalzo_col].max()); val_selezionato = st.sidebar.slider(f"Sbalzo Termico {suffisso}", 0.0, max_val, (0.0, max_val))
            df_filtrato = df_filtrato[df_filtrato[sbalzo_col].fillna(0).between(val_selezionato[0], val_selezionato[1])]
    st.sidebar.markdown("---"); st.sidebar.success(f"Visualizzati {len(df_filtrato)} marker sulla mappa.")
    df_mappa = df_filtrato.dropna(subset=['LATITUDINE', 'LONGITUDINE']).copy()
    mappa = create_map(map_tile); Geocoder(collapsed=True, placeholder='Cerca un luogo...', add_marker=True).add_to(mappa)
    
    # --- FIX POPUP A TABELLA ---
    def create_popup_html(row):
        html = """<style>.popup-container{font-family:Arial,sans-serif;font-size:13px;max-height:350px;overflow-y:auto;overflow-x:hidden}h4{margin-top:12px;margin-bottom:5px;color:#0057e7;border-bottom:1px solid #ccc;padding-bottom:3px}table{width:100%;border-collapse:collapse;margin-bottom:10px}td{text-align:left;padding:4px;border-bottom:1px solid #eee}td:first-child{font-weight:bold;color:#333;width:65%}td:last-child{color:#555}.btn-container{text-align:center;margin-top:15px;}.btn{background-color:#007bff;color:white;padding:8px 12px;border-radius:5px;text-decoration:none;font-weight:bold;}</style><div class="popup-container">"""
        groups = { 
            "Info Stazione": ["STAZIONE", "LEGENDA_DESCRIZIONE", "LEGENDA_COMUNE", "LEGENDA_ALTITUDINE"], 
            "Dati Meteo": ["LEGENDA_TEMPERATURA_MEDIANA_MINIMA", "LEGENDA_TEMPERATURA_MEDIANA", "LEGENDA_UMIDITA_MEDIA_7GG", "LEGENDA_PIOGGE_RESIDUA", "LEGENDA_TOTALE_PIOGGE_MENSILI"], 
            "Analisi Base": ["LEGENDA_MEDIA_PORCINI_CALDO_BASE", "LEGENDA_MEDIA_PORCINI_CALDO_BOOST", "LEGENDA_DURATA_RANGE_CALDO", "LEGENDA_CONTEGGIO_GG_ALLA_RACCOLTA_CALDO", "LEGENDA_MEDIA_PORCINI_FREDDO_BASE", "LEGENDA_MEDIA_PORCINI_FREDDO_BOOST", "LEGENDA_DURATA_RANGE_FREDDO", "LEGENDA_CONTEGGIO_GG_ALLA_RACCOLTA_FREDDO"], 
            "Analisi Sbalzo Migliore": ["LEGENDA_SBALZO_TERMICO_MIGLIORE", "LEGENDA_MEDIA_PORCINI_CALDO_ST_MIGLIORE", "LEGENDA_MEDIA_BOOST_CALDO_ST_MIGLIORE", "LEGENDA_GG_ST_MIGLIORE_CALDO", "LEGENDA_MEDIA_PORCINI_FREDDO_ST_MIGLIORE", "LEGENDA_MEDIA_BOOST_FREDDO_ST_MIGLIORE", "LEGENDA_GG_ST_MIGLIORE_FREDDO"], 
            "Analisi Sbalzo Secondo": ["LEGENDA_SBALZO_TERMICO_SECONDO", "LEGENDA_MEDIA_PORCINI_CALDO_ST_SECONDO", "LEGENDA_MEDIA_BOOST_CALDO_ST_SECONDO", "LEGENDA_GG_ST_SECONDO_CALDO", "LEGENDA_MEDIA_PORCini_FREDDO_ST_SECONDO", "LEGENDA_MEDIA_BOOST_FREDDO_ST_SECONDO", "LEGENDA_GG_ST_SECONDO_FREDDO"] 
        }
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
        station_name_for_url = row['STAZIONE']; link = f'?station={station_name_for_url}'; html += f'<div class="btn-container"><a href="{link}" target="_self" class="btn">📈 Mostra Storico Stazione</a></div>'; html += "</div>"
        return html

    def get_marker_color(val): return {"ROSSO": "red", "GIALLO": "yellow", "ARANCIONE": "orange", "VERDE": "green"}.get(str(val).strip().upper(), "gray")
    
    for _, row in df_mappa.iterrows():
        try:
            # --- FIX DEFINITIVO COORDINATE ---
            lat, lon = float(row['LONGITUDINE']), float(row['LATITUDINE'])
            
            colore = get_marker_color(row.get('LEGENDA_COLORE', 'gray')); popup_html = create_popup_html(row)
            folium.CircleMarker(location=[lat, lon], radius=6, color=colore, fill=True, fill_color=colore, fill_opacity=0.9, popup=folium.Popup(popup_html, max_width=380)).add_to(mappa)
        except (ValueError, TypeError): continue
    folium_static(mappa, width=1000, height=700)

def display_period_analysis(df):
    st.header("📊 Analisi di Periodo con Piogge Aggregate"); st.sidebar.title("Filtri di Periodo")
    map_tile = st.sidebar.selectbox("Tipo di mappa:", ["OpenStreetMap", "Stamen Terrain", "CartoDB positron"], key="tile_period")
    min_date, max_date = df['DATA'].min().date(), df['DATA'].max().date()
    date_range = st.sidebar.date_input("Seleziona un periodo:", value=(max_date, max_date), min_value=min_date, max_value=max_date)
    if len(date_range) != 2: st.warning("Seleziona un intervallo di date valido."); st.stop()
    start_date, end_date = date_range; df_filtered = df[df['DATA'].dt.date.between(start_date, end_date)]
    agg_cols = {'TOTALE_PIOGGIA_GIORNO': 'sum', 'LATITUDINE': 'first', 'LONGITUDINE': 'first'}; df_agg = df_filtered.groupby('STAZIONE').agg(agg_cols).reset_index()
    df_agg = df_agg[df_agg['TOTALE_PIOGGIA_GIORNO'] > 0]
    if not df_agg.empty:
        max_rain_filter = float(df_agg['TOTALE_PIOGGIA_GIORNO'].max())
        rain_range = st.sidebar.slider("Filtra per Pioggia Totale (mm)", 0.0, max_rain_filter, (0.0, max_rain_filter))
        df_agg = df_agg[df_agg['TOTALE_PIOGGIA_GIORNO'].between(rain_range[0], rain_range[1])]
    st.info(f"Visualizzando **{len(df_agg)}** stazioni con precipitazioni nel periodo selezionato.")
    if df_agg.empty: st.warning("Nessuna stazione corrisponde ai filtri selezionati."); return
    mappa = create_map(map_tile, location=[df_agg['LONGITUDINE'].mean(), df_agg['LATITUDINE'].mean()])
    min_rain, max_rain = df_agg['TOTALE_PIOGGIA_GIORNO'].min(), df_agg['TOTALE_PIOGGIA_GIORNO'].max()
    colormap = linear.YlGnBu_09.scale(vmin=min_rain, vmax=max_rain if max_rain > min_rain else min_rain + 1)
    colormap.caption = 'Totale Piogge (mm) nel Periodo'; mappa.add_child(colormap)
    for _, row in df_agg.iterrows():
        fig = go.Figure(go.Bar(x=['Pioggia Totale'], y=[row['TOTALE_PIOGGIA_GIORNO']], marker_color='#007bff', text=[f"{row['TOTALE_PIOGGIA_GIORNO']:.1f} mm"], textposition='auto'))
        fig.update_layout(title_text=f"<b>{row['STAZIONE']}</b>", title_font_size=14, yaxis_title="mm", width=250, height=200, margin=dict(l=40, r=20, t=40, b=20), showlegend=False)
        config = {'displayModeBar': False}; html_chart = fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)
        iframe = folium.IFrame(html_chart, width=280, height=230); popup = folium.Popup(iframe, max_width=300)
        lat, lon = float(row['LONGITUDINE']), float(row['LATITUDINE'])
        color = colormap(row['TOTALE_PIOGGIA_GIORNO'])
        folium.CircleMarker(location=[lat, lon], radius=8, color=color, fill=True, fill_color=color, fill_opacity=0.7, popup=popup, tooltip=f"{row['STAZIONE']}: {row['TOTALE_PIOGGIA_GIORNO']:.1f} mm").add_to(mappa)
    folium_static(mappa, width=1000, height=700)
    with st.expander("Vedi dati aggregati"): st.dataframe(df_agg)

def display_station_detail(df, station_name):
    if st.button("⬅️ Torna alla Mappa Riepilogativa"):
        st.session_state['password_correct'] = True
        st.query_params.clear()

    st.header(f"📈 Storico Dettagliato: {station_name}")
    df_station = df[df['STAZIONE'] == station_name].sort_values('DATA').copy()

    if df_station.empty:
        st.error("Dati non trovati.")
        return

    # --- Grafico Piogge Giorno ---
    st.subheader("Andamento Precipitazioni Giornaliere")
    fig1 = go.Figure(go.Bar(
        x=df_station['DATA'],
        y=df_station['TOTALE_PIOGGIA_GIORNO']
    ))
    fig1.update_layout(
        title="Pioggia Giornaliera",
        xaxis_title="Data",
        yaxis_title="mm"
    )
    st.plotly_chart(fig1, use_container_width=True)

    # --- Grafico Correlazione Temperatura Mediana e Piogge Residue ---
    st.subheader("Correlazione Temperatura Mediana e Piogge Residue")
    cols_needed = ['PIOGGE_RESIDUA_ZOFFOLI', 'TEMPERATURA_MEDIANA']

    if all(c in df_station.columns for c in cols_needed) and not df_station[cols_needed].dropna().empty:
        df_chart = df_station.dropna(subset=cols_needed)

        if not df_chart.empty:
            fig2 = make_subplots(specs=[[{"secondary_y": True}]])
            fig2.add_trace(go.Scatter(
                x=df_chart['DATA'],
                y=df_chart['PIOGGE_RESIDUA_ZOFFOLI'],
                name='Piogge Residua',
                mode='lines',
                line=dict(color='blue')
            ), secondary_y=False)

            fig2.add_trace(go.Scatter(
                x=df_chart['DATA'],
                y=df_chart['TEMPERATURA_MEDIANA'],
                name='Temperatura Mediana',
                mode='lines',
                line=dict(color='red')
            ), secondary_y=True)

            # Imposta range asse
            min_rain, max_rain = df_chart['PIOGGE_RESIDUA_ZOFFOLI'].min(), df_chart['PIOGGE_RESIDUA_ZOFFOLI'].max()
            temp_range_min, temp_range_max = 0.1 * min_rain + 8, 0.1 * max_rain + 8
            fig2.update_yaxes(title_text="<b>Piogge Residua</b>", range=[min_rain, max_rain], secondary_y=False, fixedrange=True)
            fig2.update_yaxes(title_text="<b>Temperatura Mediana (°C)</b>", range=[temp_range_min, temp_range_max], secondary_y=True, fixedrange=True)

            # --- Funzione linee sbalzo con data ---
            
              from datetime import datetime # Assicurati che questo import sia all'inizio del file

def add_sbalzo_line(fig, df_data, sbalzo_col_name, label):
    # --- Blocco di Diagnosi ---
    if sbalzo_col_name not in df_data.columns:
        st.warning(f"DEBUG: La colonna '{sbalzo_col_name}' NON è stata trovata.")
        return # Esce dalla funzione se la colonna non esiste
        
    df_valid_sbalzo = df_data.dropna(subset=[sbalzo_col_name])
    
    if df_valid_sbalzo.empty:
        st.info(f"DEBUG: La colonna '{sbalzo_col_name}' esiste, ma non ci sono valori per questa stazione.")
        return # Esce se non ci sono dati
    # --- Fine Blocco di Diagnosi ---

    # Ciclo di processamento vero e proprio
    for index, row in df_valid_sbalzo.iterrows():
        sbalzo_str = str(row[sbalzo_col_name])
        
        if " - " in sbalzo_str:
            try:
                valore, data_str = sbalzo_str.split(" - ", 1)
                sbalzo_val = valore.strip().replace(",", ".")
                # Prova a convertire la data
                sbalzo_date = datetime.strptime(data_str.strip(), "%d/%m/%Y")
                
                # Se tutto va bene, aggiunge la linea
                fig.add_vline(
                    x=sbalzo_date,
                    line_width=2,
                    line_dash="dash",
                    line_color="green",
                    annotation_text=f"{label} ({sbalzo_val})",
                    annotation_position="top left"
                )
            except ValueError:
                # Questo errore si verifica se il formato della data è sbagliato
                st.error(f"DEBUG: Impossibile processare il valore '{sbalzo_str}' nella colonna '{sbalzo_col_name}'. Il formato della data non è 'gg/mm/aaaa'.")
                continue # Va al prossimo valore
        else:
            # Se manca il separatore " - "
            st.warning(f"DEBUG: Trovato valore '{sbalzo_str}' in '{sbalzo_col_name}' ma non è nel formato atteso ('valore - data').")
            
    # --- Tabella dati storici completi ---
    with st.expander("Visualizza tabella dati storici completi"):
        # Prende tutte le colonne non legenda e coordinate
        all_cols_historic = sorted([col for col in df_station.columns if not col.startswith('LEGENDA_') and col not in ['LATITUDINE', 'LONGITUDINE', 'COORDINATEGOOGLE']])

        # Ordina colonne default, includendo anche gli sbalzi
        default_cols_ordered = [
            'DATA', 'STAZIONE', 'TOTALE_PIOGGIA_GIORNO', 'PIOGGE_RESIDUA_ZOFFOLI',
            'TEMP_MIN', 'TEMP_MAX', 'TEMPERATURA_MEDIANA', 'TEMPERATURA_MEDIANA_MINIMA',
            'SBALZO_TERMICO_MIGLIORE', '2°_SBALZO_TERMICO_MIGLIORE',
            'UMIDITA_DEL_GIORNO', 'UMIDITA_MEDIA_7GG', 'VENTO',
            'PORCINI_CALDO_NOTE', 'DURATA_RANGE', 'CONTEGGIO_GG_ALLA_RACCOLTA',
            'PORCINI_FREDDO_NOTE', 'BOOST'
        ]

        default_cols_exist = [col for col in default_cols_ordered if col in all_cols_historic]
        selected_cols = st.multiselect("Seleziona le colonne da visualizzare:", options=all_cols_historic, default=default_cols_exist)

        if selected_cols:
            st.markdown("""<style>div[data-testid="stDataFrame"] { overflow-x: auto; }</style>""", unsafe_allow_html=True)
            st.dataframe(df_station[selected_cols].sort_values('DATA', ascending=False))
        else:
            st.info("Seleziona almeno una colonna per visualizzare i dati.")


def main():
    st.set_page_config(page_title="Mappa Funghi Protetta", layout="wide")
    st.title("💧 Analisi Meteo Funghi – by Bobo 🍄")
    query_params = st.query_params
    df = load_and_prepare_data(SHEET_URL)
    if df is None or df.empty: st.warning("Dati non disponibili o caricamento fallito."); st.stop()
    if "station" in query_params:
        st.session_state['password_correct'] = True
        display_station_detail(df, query_params["station"])
    else:
        if check_password():
            counter = get_view_counter()
            if st.session_state.get('just_logged_in', True): counter["count"] += 1; st.session_state['just_logged_in'] = False
            mode = st.radio("Seleziona la modalità:", ["Mappa Riepilogativa", "Analisi di Periodo"], horizontal=True)
            if mode == "Mappa Riepilogativa": display_main_map(df)
            elif mode == "Analisi di Periodo": display_period_analysis(df)

if __name__ == "__main__":
    main()




