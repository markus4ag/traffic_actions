import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from main import load_all_data  # Импортируем нашу функцию

# Настройка страницы
st.set_page_config(page_title="Traffic Actions: UA Safety", layout="wide")

# Загрузка данных
df_dtp, df_cars_total, df_speeding, df_regs, df_cams, geojson_data = load_all_data()
years = [col for col in df_dtp.columns if col.isdigit()]

# --- БОКОВАЯ ПАНЕЛЬ  ---
st.sidebar.title("Налаштування")
selected_year = st.sidebar.select_slider("Оберіть рік:", options=sorted(years), value="2024")

# --- Расчет корреляции ---
corr_data = pd.merge(
    df_dtp[['region', selected_year]], 
    df_cams[['region', selected_year]], 
    on='region', 
    suffixes=('_dtp', '_cam')
)

# Считаем корреляцию
correlation = corr_data[f'{selected_year}_dtp'].corr(corr_data[f'{selected_year}_cam'])

st.sidebar.markdown("---")
st.sidebar.subheader("Аналітика")

# Проверка на NaN (если камер было 0 везде, корреляция не определена)
if pd.isna(correlation):
    st.sidebar.info("Коефіцієнт кореляції: **Немає даних (0 камер)**")
else:
    st.sidebar.info(f"Коефіцієнт кореляції кількості ДТП та камер: **{correlation:.2f}**")
    
    if correlation > 0.5:
        st.sidebar.caption("💡 Висока пряма кореляція: камери встановлюють там, де найбільше ДТП.")
    elif correlation < -0.5:
        st.sidebar.caption("💡 Зворотна кореляція: там де камер більше, ДТП стає менше.")

mode = st.sidebar.radio(
    "Тип даних на карті:",
    ("Абсолютні значення", "На 1000 автомобілів")
)

# Подготовка данных для графиков
total_stock_by_year = df_cars_total[years].sum()

# --- ПОДГОТОВКА ДАННЫХ ДЛЯ ОТОБРАЖЕНИЯ ---
if mode == "На 1000 автомобілів":
    plot_df = df_dtp.copy()
    for yr in years:
        plot_df[yr] = (df_dtp[yr] / df_cars_total[yr]) * 1000
    dtp_total = (df_dtp[years].sum() / total_stock_by_year) * 1000
    speed_data_rel = (df_speeding.set_index('action')[years] / total_stock_by_year) * 1000
    metric_label = "К-сть ДТП"
    hover_map_template = "<b>%{hovertext}</b><br>На 1000 авто: %{z:.2f}<br>Камери: %{customdata[0]}<extra></extra>"
    common_hover = "Рік: %{x}<br>Кількість: %{y:.2f}<extra></extra>"
else:
    plot_df = df_dtp.copy()
    dtp_total = df_dtp[years].sum()
    speed_data_rel = df_speeding.set_index('action')[years]
    metric_label = "К-сть ДТП"
    hover_map_template = "<b>%{hovertext}</b><br>ДТП: %{z}<br>Камери: %{customdata[0]}<extra></extra>"
    common_hover = "Рік: %{x}<br>Кількість: %{y}<extra></extra>"

# Добавляем колонку с камерами в plot_df для текущего года
plot_df['cameras'] = plot_df['region'].map(df_cams.set_index('region')[selected_year]).fillna(0).astype(int)

# --- ОСНОВНОЙ ЭКРАН ---
st.title(f"📊 Аналіз безпеки дорожнього руху ({mode})")

# --- СЕРЕДИНА: ТОП-10 + КАРТА ---
col_table, col_map = st.columns([1, 2.5])

with col_table:
    st.subheader(f"ТОП-10 областей")
    top_ten = plot_df[['region', selected_year, 'cameras']].sort_values(by=selected_year, ascending=False).head(10).copy()
    top_ten.insert(0, '№', range(1, 11))
    
    if mode == "На 1000 автомобілів":
        top_ten[selected_year] = top_ten[selected_year].map('{:.2f}'.format)
    else:
        top_ten[selected_year] = top_ten[selected_year].astype(int)
        
    top_ten.columns = ['№', 'Область', metric_label, 'Камери']
    st.dataframe(top_ten, hide_index=True, use_container_width=True)

with col_map:
    # Изумрудная шкала
    emerald_scale = ["#d1fae5", "#10b981", "#064e3b"]
    fig_map = px.choropleth(
        plot_df, geojson=geojson_data, locations='region', featureidkey="properties.name",
        color=selected_year, color_continuous_scale=emerald_scale,
        range_color=(0, plot_df[selected_year].max()), hover_name='region',
        custom_data=['cameras']
    )
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_traces(hovertemplate=hover_map_template)
    fig_map.update_layout(dragmode=False, margin={"r":0,"t":0,"l":0,"b":0}, height=550)
    st.plotly_chart(fig_map, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

# --- ПАНЕЛЬ 2: ДИНАМИКА И СКОРОСТЬ ---
st.divider()
col_graph1, col_graph2 = st.columns(2)

with col_graph1:
    st.subheader("📈 Динаміка: Загальні ДТП та ДТП через Швидкість")
    fig_dyn = go.Figure()
    fig_dyn.add_trace(go.Scatter(x=years, y=dtp_total, name="Усі ДТП", line=dict(color='#10b981', width=3), hovertemplate=common_hover))
    fig_dyn.add_trace(go.Scatter(x=years, y=speed_data_rel.loc['Кількість ДТП'], name="Через швидкість", line=dict(color='orange', dash='dash'), hovertemplate=common_hover))
    fig_dyn.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=0, r=0, t=30, b=0), height=350)
    st.plotly_chart(fig_dyn, use_container_width=True)

with col_graph2:
    st.subheader("🚑 Наслідки перевищення швидкості")
    fig_health = go.Figure()
    fig_health.add_trace(go.Bar(x=years, y=speed_data_rel.loc['Травмовано людей'], name="Травмовано", marker_color='#34d399', hovertemplate=common_hover))
    fig_health.add_trace(go.Bar(x=years, y=speed_data_rel.loc['Загинуло людей'], name="Загинуло", marker_color='#064e3b', hovertemplate=common_hover))
    fig_health.update_layout(barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=0, r=0, t=30, b=0), height=350)
    st.plotly_chart(fig_health, use_container_width=True)

# --- ПАНЕЛЬ 3: РЕГИСТРАЦИИ И КАМЕРЫ ---
st.divider()
st.subheader("⚙️ Технічні показники")
col_reg, col_cam = st.columns(2)

with col_reg:
    st.markdown("**Кількість зареєстрованих авто**")
    total_regs = df_regs[[c for c in df_regs.columns if c.isdigit()]].sum()
    fig_reg = px.line(x=total_regs.index, y=total_regs.values, markers=True)
    fig_reg.update_traces(line_color='#059669', hovertemplate="Рік: %{x}<br>Кількість: %{y}<extra></extra>")
    fig_reg.update_layout(xaxis_title="", yaxis_title="", margin=dict(l=0, r=0, t=10, b=0), height=300)
    st.plotly_chart(fig_reg, use_container_width=True)

with col_cam:
    st.markdown("**Кількість працюючих дорожніх камер**")
    cam_years = [c for c in df_cams.columns if c.isdigit()]
    total_cams = df_cams[cam_years].sum()
    fig_cam = px.bar(x=total_cams.index, y=total_cams.values)
    fig_cam.update_traces(marker_color='#064e3b', hovertemplate="Рік: %{x}<br>Кількість: %{y}<extra></extra>")
    fig_cam.update_layout(xaxis_title="", yaxis_title="", margin=dict(l=0, r=0, t=10, b=0), height=300)
    st.plotly_chart(fig_cam, use_container_width=True)