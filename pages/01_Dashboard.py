import streamlit as st
from services.reports_service import passivo_ludocoins, containers_por_status

st.title("Dashboard")

col1, col2 = st.columns(2)

try:
    st.metric("Passivo de Ludocoins (L$)", f"{passivo_ludocoins():.2f}")
except Exception as e:
    st.metric("Passivo de Ludocoins (L$)", "—")

try:
    df = containers_por_status()
    total_abertos = int(df[df["status"]=="ABERTO"]["quantidade"].sum()) if not df.empty else 0
except Exception:
    total_abertos = 0
    
col2.metric("Containers Abertos", total_abertos)
