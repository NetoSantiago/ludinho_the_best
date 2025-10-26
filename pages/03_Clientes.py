import streamlit as st
from services.supabase_client import get_client
from services.table_utils import TableData

st.title("Clientes")
supa = get_client()

with st.form("novo_cliente"):
    telefone = st.text_input("Telefone (PK)")
    nome = st.text_input("Nome")
    optin = st.checkbox("Opt-in WhatsApp", value=True)
    if st.form_submit_button("Salvar"):
        supa.table("clientes").upsert({"telefone": telefone, "nome": nome, "opt_in_whatsapp": optin}).execute()
        st.success("Cliente salvo!")

res = supa.table("clientes").select("*").order("created_at", desc=True).execute()
table = TableData.from_records(res.data)
st.dataframe(table.as_streamlit_data(), use_container_width=True)

if not table.empty:
    st.download_button("Exportar CSV", table.to_csv(), "clientes.csv", "text/csv")
