import streamlit as st
from services.reports_service import inventario_por_status, containers_por_status, passivo_ludocoins

st.title("Relatórios")
st.subheader("Inventário por status")
table_inv = inventario_por_status()
st.dataframe(table_inv.as_streamlit_data(), use_container_width=True)

if not table_inv.empty:
    st.download_button("Exportar CSV", table_inv.to_csv(), "inventario_por_status.csv", "text/csv")
st.subheader("Containers por status")

table_containers = containers_por_status()
st.dataframe(table_containers.as_streamlit_data(), use_container_width=True)

if not table_containers.empty:
    st.download_button("Exportar CSV", table_containers.to_csv(), "containers_por_status.csv", "text/csv")
st.subheader("Passivo total de Ludocoins")
try:
    st.metric("Total (L$)", f"{passivo_ludocoins():.2f}")
except Exception as e:
    st.error(str(e))
