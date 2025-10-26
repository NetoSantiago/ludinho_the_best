import streamlit as st
from services.reports_service import passivo_ludocoins, containers_por_status

st.title("Dashboard")

col1, col2 = st.columns(2)

try:
    st.metric("Passivo de Ludocoins (L$)", f"{passivo_ludocoins():.2f}")
except Exception as e:
    st.metric("Passivo de Ludocoins (L$)", "—")

try:
    table = containers_por_status()
    total_abertos = (
        sum(row.get("quantidade", 0) for row in table.as_streamlit_data() if row.get("status") == "ABERTO")
        if not table.empty
        else 0
    )
except Exception:
    total_abertos = 0
    
col2.metric("Containers Abertos", total_abertos)
