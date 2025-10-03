import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import streamlit.components.v1 as components
import matplotlib.cm as cm
import matplotlib.colors as colors
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# --- 1. CONFIGURAZIONE CENTRALE ---
class Config:
    SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT2qK9kE_Cj-LdD3gYqJ7pM8b-p9B_H9-R_aL_F_gE4yT_hN-sX6wJ_cE7fP8uR-A-yTzR/pub?gid=0&single=true&output=csv"
    
    # Mappatura dei nomi originali delle colonne con nomi "puliti" per il codice
    COLUMN_MAP = {
        'Latitudine': 'lat',
        'Longitudine': 'lon',
        'Stazione': 'stazione',
        'Provincia': 'provincia',
        'Data': 'data',
        'ULTIMO_AGGIORNAMENTO_SHEET': 'ultimo_aggiornamento'
    }
    
    # Colonne da trattare come date
    DATE_COLS = ['data']
    
    # Colonna essenziale per i colori della mappa (default)
    DEFAULT_COLOR_METRIC = 'Piogge Residua Zoffoli'

# --- 2. FUNZIONI DI CARICAMENTO E PREPARAZIONE DATI ---

def clean_col_names(df):
    """Pulisce i nomi delle colonne per renderli utilizzabili in Python."""
    cols = df.columns.str.strip() # Rimuove spazi
    cols = cols.str.replace(r'\[.*\]', '', regex=True) # Rimuove [..]
    cols = cols.str.replace(' ', '_', regex=False) # Sostituisce spazi con _
    cols = cols.str.replace('[^A-Za-z0-9_]+', '', regex=True) # Rimuove caratteri speciali
    df.columns = cols
    # Rinomina in base alla mappatura per coerenza
    for original, new in Config.COLUMN_MAP.items():
        clean_original = original.strip().replace(r'\[.*\]', '', regex=True).replace(' ', '_', regex=False).replace('[^A-Za-z0-9_]+', '', regex=True)
        if clean_original in df.columns:
            df.rename(columns={clean_original: new}, inplace=True)
    return df


@st.cache_data(ttl=3600)
def load_and_prepare_data(url: str) -> pd.DataFrame | None:
    """Carica, pulisce e prepara i dati per l'analisi."""
    try:
        df = pd.read_csv(url, na_values=["#N/D", "#N/A"])
        df = clean_col_names(df)

        # Gestione date
        for col in Config.DATE_COLS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)

        # Conversione numerica robusta
        for col in df.select_dtypes(include=['object']).columns:
             if col not in ['stazione', 'provincia', 'ultimo_aggiornamento']:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce')

        df.dropna(subset=['lat', 'lon', 'data'], inplace=True)
        return df
    except Exception as e:
        st.error(f"Errore critico durante il caricamento dei dati: {e}")
        return None

# --- 3. SEZIONI DELL'INTERFACCIA (UI) ---

def ui_sidebar(df):
    """Crea la sidebar e restituisce tutte le selezioni dell'utente."""
    st.sidebar.title("🔍 Pannello di Controllo")
    
    mode = st.sidebar.radio(
        "Seleziona modalità di analisi:",
        ("Analisi per Periodo", "Storico Singola Stazione"),
        key="analysis_mode"
    )

    user_options = {"mode": mode}
    
    if mode == "Analisi per Periodo":
        st.sidebar.header("Filtri di Periodo")
        
        min_date, max_date = df['data'].min().date(), df['data'].max().date()
        date_range = st.sidebar.date_input(
            "Seleziona un periodo:",
            value=(max_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        user_options['date_range'] = date_range

        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        # Rimuove coordinate e colonne non utili per la metrica colore
        metrics_to_show = [c for c in numeric_cols if c not in ['lat', 'lon', 'Codice']]
        
        color_metric = st.sidebar.selectbox(
            "🎨 Metrica per colore mappa:",
            options=metrics_to_show,
            index=metrics_to_show.index(Config.DEFAULT_COLOR_METRIC) if Config.DEFAULT_COLOR_METRIC in metrics_to_show else 0
        )
        user_options['color_metric'] = color_metric

        if len(date_range) == 2:
            df_filtered_by_date = df[df['data'].dt.date.between(date_range[0], date_range[1])]
            min_val, max_val = df_filtered_by_date[color_metric].min(), df_filtered_by_date[color_metric].max()
            slider_val = st.sidebar.slider(
                f"Mostra stazioni con '{color_metric}' >= a:",
                min_value=float(min_val), max_value=float(max_val), value=float(min_val)
            )
            user_options['slider_val'] = slider_val

        provinces = sorted(df['provincia'].dropna().unique())
        selected_provinces = st.sidebar.multiselect("📍 Filtra per Provincia:", options=provinces)
        user_options['selected_provinces'] = selected_provinces

    elif mode == "Storico Singola Stazione":
        st.sidebar.header("Selezione Stazione")
        stations = sorted(df['stazione'].unique())
        selected_station = st.sidebar.selectbox("Scegli una stazione:", options=stations)
        user_options['selected_station'] = selected_station

    # Opzioni comuni
    st.sidebar.markdown("---")
    st.sidebar.header("Opzioni Visualizzazione")
    popup_cols = st.sidebar.multiselect(
        "ℹ️ Dati da mostrare nel popup/tabella:",
        options=[col for col in df.columns if col not in ['lat', 'lon']],
        default=[c for c in ['stazione', 'provincia', 'Totale_Pioggia_Giorno', 'Temperatura_mediana', 'Piogge_Residua_Zoffoli'] if c in df.columns]
    )
    user_options['popup_cols'] = popup_cols
    user_options['map_tile'] = st.sidebar.selectbox("Tipo di mappa:", ["OpenStreetMap", "Stamen Terrain", "CartoDB positron"])

    return user_options


# --- SOSTITUISCI QUESTA FUNZIONE NEL TUO CODICE ---

def page_period_analysis(df, options):
    """Mostra la pagina per l'analisi di periodo."""
    # Assicura che date_range sia una tupla/lista di due elementi
    if not isinstance(options['date_range'], (list, tuple)) or len(options['date_range']) != 2:
        st.warning("Per favore, seleziona un periodo valido nella sidebar (data di inizio e fine).")
        return
        
    start_date, end_date = options['date_range']
    st.header(f"📍 Analisi Mappa per il Periodo: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")

    # 1. Filtro dati
    df_filtered = df[df['data'].dt.date.between(start_date, end_date)]
    if options['selected_provinces']:
        df_filtered = df_filtered[df_filtered['provincia'].isin(options['selected_provinces'])]
    
    # 2. Aggregazione dati per stazione
    agg_dict = {col: 'mean' for col in df_filtered.select_dtypes(include=['number']).columns} # <-- RIGA CORRETTA
    # Per le piogge, è meglio la somma
    for col in df_filtered.columns:
        if 'piogg' in col.lower():
            agg_dict[col] = 'sum'
    
    df_agg = df_filtered.groupby(['stazione', 'lat', 'lon', 'provincia']).agg(agg_dict).reset_index()
    
    # Applica filtro slider sui dati aggregati
    if not df_agg.empty and options['color_metric'] in df_agg.columns:
        df_agg = df_agg[df_agg[options['color_metric']] >= options['slider_val']]
    else:
        st.warning("La metrica selezionata non è disponibile per il periodo scelto.")
        return

    st.info(f"Visualizzando **{len(df_agg)}** stazioni aggregate nel periodo selezionato.")

    if df_agg.empty:
        st.warning("Nessun dato trovato per i filtri selezionati.")
        return

    # 3. Creazione Mappa
    mappa = folium.Map(location=[df_agg['lat'].mean(), df_agg['lon'].mean()], zoom_start=8, tiles=options['map_tile'])
    
    metric = options['color_metric']
    
    # Gestisce il caso in cui tutti i valori siano uguali
    min_metric, max_metric = df_agg[metric].min(), df_agg[metric].max()
    if min_metric == max_metric:
        norm = colors.Normalize(vmin=min_metric - 1, vmax=max_metric + 1)
    else:
        norm = colors.Normalize(vmin=min_metric, vmax=max_metric)
        
    colormap = cm.get_cmap('Blues')

    for _, row in df_agg.iterrows():
        popup_html = f"<h4>{row['stazione']}</h4><hr>"
        for col in options['popup_cols']:
            if col in row and pd.notna(row[col]):
                val = row[col]
                formatted_val = f"{val:.2f}" if isinstance(val, float) else val
                popup_html += f"<b>{col.replace('_', ' ').title()}</b>: {formatted_val}<br>"
        
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=8,
            color=colors.to_hex(colormap(norm(row[metric]))),
            fill=True, fill_color=colors.to_hex(colormap(norm(row[metric]))), fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=f"<b>{row['stazione']}</b><br>{metric.replace('_', ' ')}: {row[metric]:.2f}"
        ).add_to(mappa)

    folium_static(mappa, width=1000, height=600)
    
    # 4. Tabella Dati
    with st.expander("Visualizza dati tabellari aggregati"):
        st.dataframe(df_agg[options['popup_cols']])

def page_station_history(df, options):
    """Mostra la pagina per lo storico di una singola stazione."""
    station = options['selected_station']
    st.header(f"📈 Storico per la Stazione: {station}")
    
    df_station = df[df['stazione'] == station].sort_values('data')

    if df_station.empty:
        st.warning("Nessun dato storico trovato per questa stazione.")
        return

    # 1. Grafici
    st.subheader("Andamento Precipitazioni")
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Bar(x=df_station['data'], y=df_station['Totale_Pioggia_Giorno'], name='Pioggia Giorno'), secondary_y=False)
    fig1.add_trace(go.Scatter(x=df_station['data'], y=df_station['Piogge_Residua_Zoffoli'], name='Pioggia Residua', mode='lines+markers'), secondary_y=True)
    fig1.update_layout(title_text="Pioggia Giornaliera vs Residua")
    fig1.update_yaxes(title_text="<b>Pioggia Giorno (mm)</b>", secondary_y=False)
    fig1.update_yaxes(title_text="<b>Pioggia Residua</b>", secondary_y=True)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Andamento Temperature e Sbalzi")
    fig2 = px.line(df_station, x='data', y=['Temperatura_mediana', 'Sbalzo_Termico'], 
                   title='Temperatura Mediana e Sbalzo Termico',
                   labels={'value': 'Valore', 'variable': 'Metrica'})
    st.plotly_chart(fig2, use_container_width=True)

    # 2. Mappa (Opzionale)
    st.subheader("Posizione Geografica")
    station_info = df_station.iloc[0]
    map_station = folium.Map(location=[station_info['lat'], station_info['lon']], zoom_start=12)
    folium.Marker(
        [station_info['lat'], station_info['lon']], 
        popup=f"<b>{station}</b><br>Quota: {station_info['Quota_m_slm']}m",
        tooltip=station
    ).add_to(map_station)
    folium_static(map_station, width=1000, height=300)

    # 3. Tabella Dati
    with st.expander("Visualizza tutti i dati storici per questa stazione"):
        st.dataframe(df_station[options['popup_cols']])


# --- 4. APPLICAZIONE PRINCIPALE ---
def main():
    """Funzione principale che orchestra l'applicazione Streamlit."""
    st.set_page_config(page_title="Analisi Meteo Avanzata", layout="wide")
    st.title("💧 Analisi Meteo Avanzata 💧")

    df = load_and_prepare_data(Config.SHEET_URL)
    
    if df is None:
        st.stop()

    if 'ultimo_aggiornamento' in df.columns and not df['ultimo_aggiornamento'].dropna().empty:
        last_update = df['ultimo_aggiornamento'].dropna().iloc[0]
        st.markdown(f"**Ultimo aggiornamento dati:** `{last_update}`")
    
    user_options = ui_sidebar(df)

    if user_options['mode'] == "Analisi per Periodo":
        if len(user_options.get('date_range', [])) == 2:
            page_period_analysis(df, user_options)
        else:
            st.warning("Per favore, seleziona un periodo valido nella sidebar.")
            
    elif user_options['mode'] == "Storico Singola Stazione":
        page_station_history(df, user_options)

if __name__ == "__main__":
    main()

