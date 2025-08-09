import streamlit as st
from services.reports_service import inventario_por_status, containers_por_status, passivo_ludocoins

st.title("Relatórios")
st.subheader("Inventário por status")
df1 = inventario_por_status()
st.dataframe(df1, use_container_width=True)

if not df1.empty:
    st.download_button("Exportar CSV", df1.to_csv(index=False), "inventario_por_status.csv", "text/csv")
st.subheader("Containers por status")

df2 = containers_por_status()
st.dataframe(df2, use_container_width=True)

if not df2.empty:
    st.download_button("Exportar CSV", df2.to_csv(index=False), "containers_por_status.csv", "text/csv")
st.subheader("Passivo total de Ludocoins")
try:
    st.metric("Total (L$)", f"{passivo_ludocoins():.2f}")
except Exception as e:
    st.error(str(e))
