import pandas as pd
import json
import streamlit as st

@st.cache_data
def load_all_data():
    # Пути к файлам (используем / для совместимости с Linux/Streamlit Cloud)
    df_dtp = pd.read_csv('Datasets/traffic_accidents_by_region_and_year.csv').dropna(subset=['region'])
    df_cars_total = pd.read_csv('Datasets/car_ownership_by_year_and_region.csv').dropna(subset=['region'])
    df_speeding = pd.read_csv('Datasets/accidents_due_to_speeding_by_year.csv')
    df_registrations = pd.read_csv('Datasets/Car_registrations_per_region.csv').dropna(subset=['region'])
    df_cameras = pd.read_csv('Datasets/сameras_by_region.csv').dropna(subset=['region'])
    
    # Очистка числовых данных
    for df in [df_cars_total, df_registrations, df_cameras]:
        for yr in df.columns:
            if yr.isdigit():
                df[yr] = df[yr].astype(str).str.replace(' ', '').str.replace(',', '.').replace('nan', '0')
                df[yr] = pd.to_numeric(df[yr], errors='coerce').fillna(0)

    # Объединение Киева и области
    for df in [df_dtp, df_cars_total, df_registrations, df_cameras]:
        kyiv_city_mask = df['region'] == 'Київ'
        kyiv_region_mask = df['region'] == 'Київська область'
        if kyiv_city_mask.any() and kyiv_region_mask.any():
            for yr in df.columns:
                if yr.isdigit():
                    df.loc[kyiv_region_mask, yr] += df.loc[kyiv_city_mask, yr].values[0]
            df.drop(df[df['region'] == 'Київ'].index, inplace=True)

    with open('Geojson_map/UA_FULL_Ukraine.geojson', 'r', encoding='utf-8') as f:
        geojson = json.load(f)
        
    return df_dtp, df_cars_total, df_speeding, df_registrations, df_cameras, geojson