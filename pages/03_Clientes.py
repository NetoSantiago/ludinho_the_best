import streamlit as st, pandas as pd
from services.supabase_client import get_client

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
df = pd.DataFrame(res.data or [])
st.dataframe(df, use_container_width=True)

if not df.empty:
    st.download_button("Exportar CSV", df.to_csv(index=False), "clientes.csv", "text/csv")
