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

# --- 2. CONFIGURAZIONE CENTRALE E FUNZIONI DI BASE ---

# URL del nuovo Google Sheet unificato
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRxitMYpUqvX6bxVaukG01lJDC8SUfXtr47Zv5ekR1IzfR1jmhUilBsxZPJ8hrktVHrBh6hUUWYUtox/pub?output=csv"

# Mappatura per rinominare le colonne "Legenda_" e renderle compatibili con il primo script
COL_MAP_LEGACY = {
    "Stazione": "Legenda_Stazione", "DESCRIZIONE": "Legenda_DESCRIZIONE", "COMUNE": "Legenda_COMUNE",
    "ALTITUDINE": "Legenda_ALTITUDINE", "X": "Longitudine", "Y": "Latitudine",
    "TEMPERATURA MEDIANA MINIMA": "Legenda_TEMPERATURA MEDIANA MINIMA", "TEMPERATURA MEDIANA": "Legenda_TEMPERATURA MEDIANA",
    "UMIDITA MEDIA 7GG": "Legenda_UMIDITA MEDIA 7GG", "PIOGGE RESIDUA": "Legenda_PIOGGE RESIDUA",
    "Piogge entro 5 gg": "Legenda_Piogge entro 5 gg", "Piogge entro 10 gg": "Legenda_Piogge entro 10 gg",
    "Totale Piogge Mensili": "Legenda_Totale Piogge Mensili", "MEDIA PORCINI CALDO BASE": "Legenda_MEDIA PORCINI CALDO BASE",
    "MEDIA PORCINI CALDO BOOST": "Legenda_MEDIA PORCINI CALDO BOOST", "DURATA RANGE CALDO": "Legenda_DURATA RANGE CALDO",
    "CONTEGGIO GG ALLA RACCOLTA CALDO": "Legenda_CONTEGGIO GG ALLA RACCOLTA CALDO", "MEDIA PORCINI FREDDO BASE": "Legenda_MEDIA PORCINI FREDDO BASE",
    "MEDIA PORCINI FREDDO BOOST": "Legenda_MEDIA PORCINI FREDDO BOOST", "DURATA RANGE FREDDO": "Legenda_DURATA RANGE FREDDO",
    "CONTEGGIO GG ALLA RACCOLTA FREDDO": "Legenda_CONTEGGIO GG ALLA RACCOLTA FREDDO", "SBALZO TERMICO MIGLIORE": "Legenda_SBALZO TERMICO MIGLIORE",
    "MEDIA PORCINI CALDO ST MIGLIORE": "Legenda_MEDIA PORCINI CALDO ST MIGLIORE", "MEDIA BOOST CALDO ST MIGLIORE": "Legenda_MEDIA BOOST CALDO ST MIGLIORE",
    "GG ST MIGLIORE CALDO": "Legenda_GG ST MIGLIORE CALDO", "MEDIA PORCINI FREDDO ST MIGLIORE": "Legenda_MEDIA PORCINI FREDDO ST MIGLIORE",
    "MEDIA BOOST FREDDO ST MIGLIORE": "Legenda_MEDIA BOOST FREDDO ST MIGLIORE", "GG ST MIGLIORE FREDDO": "Legenda_GG ST MIGLIORE FREDDO",
    "SBALZO TERMICO SECONDO": "Legenda_SBALZO TERMICO SECONDO", "MEDIA PORCINI CALDO ST SECONDO": "Legenda_MEDIA PORCINI CALDO ST SECONDO",
    "MEDIA BOOST CALDO ST SECONDO": "Legenda_MEDIA BOOST CALDO ST SECONDO", "GG ST SECONDO CALDO": "Legenda_GG ST SECONDO CALDO",
    "MEDIA PORCINI FREDDO ST SECONDO": "Legenda_MEDIA PORCINI FREDDO ST SECONDO", "MEDIA BOOST FREDDO ST SECONDO": "Legenda_MEDIA BOOST FREDDO ST SECONDO",
    "GG ST SECONDO FREDDO": "Legenda_GG ST SECONDO FREDDO", "COLORE": "Legenda_COLORE",
    "ULTIMO_AGGIORNAMENTO_SHEET": "Legenda_ULTIMO_AGGIORNAMENTO_SHEET"
}

# Colonne da usare per i filtri della mappa riepilogativa (rimosse quelle delle piogge a 5/10gg)
COLONNE_FILTRO_RIEPILOGO = [
    "TEMPERATURA MEDIANA", "PIOGGE RESIDUA", "MEDIA PORCINI CALDO BASE", "MEDIA PORCINI FREDDO BASE",
    "MEDIA PORCINI CALDO ST MIGLIORE", "MEDIA PORCINI FREDDO ST MIGLIORE",
    "MEDIA PORCINI CALDO ST SECONDO", "MEDIA PORCINI FREDDO ST SECONDO"
]

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
        st.text_input("Inserisci la password per accedere:", type="password", on_change=password_entered, key="password")
        if st.session_state.get("password_correct") is False and "password" in st.session_state and st.session_state["password"] != "":
             st.error("😕 Password errata. Riprova.")
        st.stop()
    return True

@st.cache_resource
def get_view_counter():
    return {"count": 0}

@st.cache_data(ttl=3600)
def load_and_prepare_data(url: str):
    """Carica, pulisce e prepara i dati per l'intera applicazione (versione definitiva)."""
    try:
        # Carica tutti i dati come testo per evitare conversioni automatiche errate
        df = pd.read_csv(url, na_values=["#N/D", "#N/A"], dtype=str, skiprows=[1])
        df.attrs['last_loaded'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # 1. Rinomina le colonne legacy
        rename_dict = {v: k for k, v in COL_MAP_LEGACY.items() if v in df.columns}
        df.rename(columns=rename_dict, inplace=True)

        # 2. Pulisci tutti i nomi delle colonne
        def clean_name(name):
            name = re.sub(r'\[.*?\]', '', str(name))
            name = name.strip().replace(' ', '_')
            return name
        df.columns = [clean_name(col) for col in df.columns]

        # 3. Colonne che devono rimanere testo e non essere convertite in numeri
        TEXT_COLUMNS = [
            'Stazione', 'COMUNE', 'DESCRIZIONE', 'COLORE',
            'ULTIMO_AGGIORNAMENTO_SHEET',
            'SBALZO_TERMICO_MIGLIORE', 'SBALZO_TERMICO_SECONDO'
        ]

        # 4. Itera su TUTTE le colonne per una conversione corretta e unificata
        for col in df.columns:
            if col == 'Data':
                # Gestisce la colonna Data
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
            elif col not in TEXT_COLUMNS:
                # Converte TUTTE le altre colonne (incluse X e Y) in numeri.
                # QUESTA È LA CORREZIONE CHIAVE: si converte prima in testo (.astype(str))
                # e solo dopo si usa l'accessor .str per la sostituzione.
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(',', '.', regex=False),
                    errors='coerce'
                )

        # 5. Rimuovi le righe solo se mancano i dati ESSENZIALI dopo la conversione
        df.dropna(subset=['Y', 'X', 'Data'], inplace=True)

        return df

    except Exception as e:
        st.error(f"Errore critico durante il caricamento dei dati: {e}")
        return None

    except Exception as e:
        st.error(f"Errore critico durante il caricamento dei dati: {e}")
        return None


# --- 3. LOGICA DI VISUALIZZAZIONE DELLE DIVERSE PAGINE ---

def display_main_map(df):
    """Visualizza la mappa riepilogativa (logica del primo script)."""
    st.header("🗺️ Mappa Riepilogativa (Situazione Attuale)")
    
    last_date = df['Data'].max()
    df_latest = df[df['Data'] == last_date].copy()
    st.info(f"Visualizzazione dati aggiornati al: **{last_date.strftime('%d/%m/%Y')}**")

    st.sidebar.title("Informazioni e Filtri Riepilogo")
    st.sidebar.markdown("---")
    map_tile = st.sidebar.selectbox("Tipo di mappa:", ["OpenStreetMap", "Stamen Terrain", "CartoDB positron"], key="tile_main")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Statistiche")
    counter = get_view_counter()
    st.sidebar.info(f"Visite totali: **{counter['count']}**")
    st.sidebar.info(f"App aggiornata il: **{df.attrs['last_loaded']}**")
    if 'ULTIMO_AGGIORNAMENTO_SHEET' in df_latest.columns and not df_latest['ULTIMO_AGGIORNAMENTO_SHEET'].empty:
        last_sheet_update = df_latest['ULTIMO_AGGIORNAMENTO_SHEET'].iloc[0]
        st.sidebar.info(f"Sheet aggiornato il: **{last_sheet_update}**")
        
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtri Dati")
    df_filtrato = df_latest.copy()
    colonne_filtro_esistenti = [col for col in COLONNE_FILTRO_RIEPILOGO if col in df_filtrato.columns]
    for colonna in colonne_filtro_esistenti:
        if not df_filtrato[colonna].dropna().empty:
            min_val, max_val = float(df_filtrato[colonna].min()), float(df_filtrato[colonna].max())
            val_selezionato = st.sidebar.slider(f"Filtra per {colonna}", min_val, max_val, (min_val, max_val))
            df_filtrato = df_filtrato[(df_filtrato[colonna].fillna(0) >= val_selezionato[0]) & (df_filtrato[colonna].fillna(0) <= val_selezionato[1])]
    
    st.sidebar.markdown("---")
    st.sidebar.success(f"Visualizzati {len(df_filtrato)} marker sulla mappa.")

    df_mappa = df_filtrato.dropna(subset=['Y', 'X']).copy()
    mappa = folium.Map(location=[43.5, 11.0], zoom_start=8, tiles=map_tile)
    Geocoder(collapsed=True, placeholder='Cerca un luogo...', add_marker=True).add_to(mappa)

    def create_popup_html(row):
        html = """<style>.popup-container{font-family:Arial,sans-serif;font-size:13px;max-height:350px;overflow-y:auto;overflow-x:hidden}h4{margin-top:12px;margin-bottom:5px;color:#0057e7;border-bottom:1px solid #ccc;padding-bottom:3px}table{width:100%;border-collapse:collapse;margin-bottom:10px}td{text-align:left;padding:4px;border-bottom:1px solid #eee}td:first-child{font-weight:bold;color:#333;width:65%}td:last-child{color:#555}.btn-container{text-align:center;margin-top:15px;}.btn{background-color:#007bff;color:white;padding:8px 12px;border-radius:5px;text-decoration:none;font-weight:bold;}</style><div class="popup-container">"""
        groups = { "Info Stazione": ["Stazione", "DESCRIZIONE", "COMUNE", "ALTITUDINE"], "Dati Meteo": ["TEMPERATURA MEDIANA MINIMA", "TEMPERATURA MEDIANA", "UMIDITA MEDIA 7GG", "PIOGGE RESIDUA", "Totale Piogge Mensili"], "Analisi Base": ["MEDIA PORCINI CALDO BASE", "MEDIA PORCINI CALDO BOOST", "DURATA RANGE CALDO", "CONTEGGIO GG ALLA RACCOLTA CALDO", "MEDIA PORCINI FREDDO BASE", "MEDIA PORCINI FREDDO BOOST", "DURATA RANGE FREDDO", "CONTEGGIO GG ALLA RACCOLTA FREDDO"], "Analisi Sbalzo Migliore": ["SBALZO TERMICO MIGLIORE", "MEDIA PORCINI CALDO ST MIGLIORE", "MEDIA BOOST CALDO ST MIGLIORE", "GG ST MIGLIORE CALDO", "MEDIA PORCINI FREDDO ST MIGLIORE", "MEDIA BOOST FREDDO ST MIGLIORE", "GG ST MIGLIORE FREDDO"], "Analisi Sbalzo Secondo": ["SBALZO TERMICO SECONDO", "MEDIA PORCINI CALDO ST SECONDO", "MEDIA BOOST CALDO ST SECONDO", "GG ST SECONDO CALDO", "MEDIA PORCINI FREDDO ST SECONDO", "MEDIA BOOST FREDDO ST SECONDO", "GG ST SECONDO FREDDO"] }
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
        station_name_for_url = row['Stazione']
        link = f'?station={station_name_for_url}'
        html += f'<div class="btn-container"><a href="{link}" target="_self" class="btn">📈 Mostra Storico Stazione</a></div>'
        html += "</div>"
        return html
    
    def get_marker_color(val):
        val = str(val).strip().upper(); return {"ROSSO": "red", "GIALLO": "yellow", "ARANCIONE": "orange", "VERDE": "green"}.get(val, "gray")

    for _, row in df_mappa.iterrows():
        try:
            lat = float(row['Y']); lon = float(row['X'])
            colore = get_marker_color(row.get('COLORE', 'gray')); popup_html = create_popup_html(row)
            folium.CircleMarker(location=[lat, lon], radius=6, color=colore, fill=True, fill_color=colore, fill_opacity=0.9, popup=folium.Popup(popup_html, max_width=380)).add_to(mappa)
        except (ValueError, TypeError): continue
            
    folium_static(mappa, width=1000, height=700)

def display_period_analysis(df):
    """Visualizza l'analisi di periodo con grafici Plotly interattivi nei popup."""
    st.header("📊 Analisi di Periodo con Piogge Aggregate")

    st.sidebar.title("Filtri di Periodo")
    map_tile = st.sidebar.selectbox("Tipo di mappa:", ["OpenStreetMap", "Stamen Terrain", "CartoDB positron"], key="tile_period")
    
    min_date, max_date = df['Data'].min().date(), df['Data'].max().date()
    date_range = st.sidebar.date_input(
        "Seleziona un periodo:", value=(max_date, max_date),
        min_value=min_date, max_value=max_date
    )

    if len(date_range) != 2:
        st.warning("Seleziona un intervallo di date valido.")
        st.stop()
    
    start_date, end_date = date_range
    df_filtered = df[df['Data'].dt.date.between(start_date, end_date)]

    agg_cols = {'Totale_Pioggia_Giorno': 'sum', 'Y': 'first', 'X': 'first'}
    df_agg = df_filtered.groupby('Stazione').agg(agg_cols).reset_index()
    df_agg = df_agg[df_agg['Totale_Pioggia_Giorno'] > 0]
    
    st.info(f"Visualizzando **{len(df_agg)}** stazioni con precipitazioni nel periodo selezionato.")
    
    if df_agg.empty:
        st.warning("Nessuna precipitazione registrata nel periodo per le stazioni disponibili.")
        return

    mappa = folium.Map(location=[df_agg['Y'].mean(), df_agg['X'].mean()], zoom_start=8, tiles=map_tile)
    
    for _, row in df_agg.iterrows():
        fig = go.Figure()
        fig.add_trace(go.Bar(x=['Pioggia Totale'], y=[row['Totale_Pioggia_Giorno']], marker_color='#007bff', text=[f"{row['Totale_Pioggia_Giorno']:.1f} mm"], textposition='auto'))
        fig.update_layout(title_text=f"<b>{row['Stazione']}</b>", title_font_size=14, yaxis_title="mm", width=250, height=200, margin=dict(l=40, r=20, t=40, b=20), showlegend=False)
        
        config = {'displayModeBar': False}
        html_chart = fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)

        iframe = folium.IFrame(html_chart, width=280, height=230)
        popup = folium.Popup(iframe, max_width=300)

        folium.Marker(
            location=[row['Y'], row['X']],
            popup=popup,
            tooltip=f"Clicca per vedere il grafico di: <b>{row['Stazione']}</b>",
            icon=folium.Icon(color="blue", icon="cloud")
        ).add_to(mappa)
        
    folium_static(mappa, width=1000, height=700)
    with st.expander("Vedi dati aggregati"):
        st.dataframe(df_agg)

def display_station_detail(df, station_name):
    """Visualizza la pagina di dettaglio con grafici e tabella per una stazione."""
    if st.button("⬅️ Torna alla Mappa Riepilogativa"):
        st.query_params.clear()

    st.header(f"📈 Storico Dettagliato: {station_name}")
    df_station = df[df['Stazione'] == station_name].sort_values('Data').copy()
    
    if df_station.empty:
        st.error("Dati non trovati per la stazione selezionata.")
        return

    st.subheader("Andamento Precipitazioni Giornaliere")
    fig1 = go.Figure(go.Bar(x=df_station['Data'], y=df_station['Totale_Pioggia_Giorno'], name='Pioggia (mm)'))
    fig1.update_layout(title="Pioggia Giornaliera", xaxis_title="Data", yaxis_title="Millimetri (mm)")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Correlazione Temperatura Mediana e Piogge Residue")
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Scatter(x=df_station['Data'], y=df_station['Piogge_Residua'], name='Piogge Residua', mode='lines', line=dict(color='blue')), secondary_y=False)
    fig2.add_trace(go.Scatter(x=df_station['Data'], y=df_station['TEMPERATURA_MEDIANA'], name='Temperatura Mediana', mode='lines', line=dict(color='red')), secondary_y=True)

    min_rain, max_rain = df_station['Piogge_Residua'].min(), df_station['Piogge_Residua'].max()
    temp_range_min = 0.1 * min_rain + 8; temp_range_max = 0.1 * max_rain + 8
    
    fig2.update_yaxes(title_text="<b>Piogge Residua</b>", range=[min_rain, max_rain], secondary_y=False, color='blue')
    fig2.update_yaxes(title_text="<b>Temperatura Mediana (°C)</b>", range=[temp_range_min, temp_range_max], secondary_y=True, color='red')
    
    def add_sbalzo_line(fig, sbalzo_series, name):
        sbalzo_str = sbalzo_series.dropna().iloc[-1] if not sbalzo_series.dropna().empty else None
        if sbalzo_str and isinstance(sbalzo_str, str) and ' - ' in sbalzo_str:
            try:
                val, date_str = sbalzo_str.split(' - ')
                sbalzo_date = datetime.strptime(date_str.strip(), '%d/%m/%Y')
                fig.add_vline(x=sbalzo_date, line_width=2, line_dash="dash", line_color="green", annotation_text=f"{name} ({val.strip()})", annotation_position="top left")
            except Exception: pass
    
    if 'SBALZO_TERMICO_MIGLIORE' in df_station.columns: add_sbalzo_line(fig2, df_station['SBALZO_TERMICO_MIGLIORE'], "Sbalzo Migliore")
    if 'SBALZO_TERMICO_SECONDO' in df_station.columns: add_sbalzo_line(fig2, df_station['SBALZO_TERMICO_SECONDO'], "2° Sbalzo")

    fig2.update_layout(title_text="Temperatura vs Piogge (50mm allineato a 13°C, 100mm a 18°C)")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Andamento Temperature Minime e Massime")
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df_station['Data'], y=df_station['Temp_Max'], name='Temp Max', line=dict(color='orangered')))
    fig3.add_trace(go.Scatter(x=df_station['Data'], y=df_station['Temp_Min'], name='Temp Min', line=dict(color='skyblue'), fill='tonexty', fillcolor='rgba(135,206,250,0.2)'))
    fig3.update_layout(title="Escursione Termica Giornaliera", xaxis_title="Data", yaxis_title="Temperatura (°C)")
    st.plotly_chart(fig3, use_container_width=True)
    
    with st.expander("Visualizza tabella dati storici completi"):
        cols_to_show = [col for col in df.columns if not col.startswith('Legenda_') and col not in ['Y', 'X']]
        st.dataframe(df_station[cols_to_show])

# --- 4. APPLICAZIONE PRINCIPALE ---
def main():
    st.set_page_config(page_title="Mappa Funghi Protetta", layout="wide")
    st.title("💧 Analisi Meteo Funghi – by Bobo 🍄")

    if not check_password(): st.stop()
    
    counter = get_view_counter()
    if st.session_state.get('just_logged_in', True):
        counter["count"] += 1
        st.session_state['just_logged_in'] = False

    df = load_and_prepare_data(SHEET_URL)
    if df is None or df.empty:
        st.warning("Dati non disponibili al momento. Riprova più tardi."); st.stop()

    query_params = st.query_params
    if "station" in query_params:
        display_station_detail(df, query_params["station"])
    else:
        mode = st.radio("Seleziona la modalità di visualizzazione:", ["Mappa Riepilogativa", "Analisi di Periodo"], horizontal=True)
        if mode == "Mappa Riepilogativa": display_main_map(df)
        elif mode == "Analisi di Periodo": display_period_analysis(df)

if __name__ == "__main__":
    main()




