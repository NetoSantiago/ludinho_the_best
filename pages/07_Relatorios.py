import streamlit as st
from services.reports_service import inventario_por_status, containers_por_status, passivo_ludocoins

st.title("Relatórios")

# ====== Auth guard ======
if not st.session_state.get("auth_ok"):
    st.info("Acesso restrito. Vá para a página **Login** no menu lateral e autentique-se.")
    st.stop()

if st.session_state.get("auth_role") != "admin":
    st.info("Você não tem acesso a esta página.")
    st.stop()

# (opcional) botão de sair na sidebar
with st.sidebar:
    st.caption(f"Logado como: {st.session_state.get('auth_user_name','?')}")
    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()

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
