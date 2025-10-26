import streamlit as st
from services.supabase_client import get_client
from services.table_utils import TableData

st.title("Jogos")
supa = get_client()

with st.form("novo_jogo"):
    nome = st.text_input("Nome (público)")
    nome_evento = st.text_input("Nome para evento (interno/opcional)")
    preco = st.number_input("Preço (BRL)", min_value=0.0, step=1.0)
    status = st.selectbox("Status", ["DISPONIVEL","PRE-VENDA"])
    sku = st.text_input("SKU")
    categoria = st.text_input("Categoria")
    ativo = st.checkbox("Ativo", value=True)

    if st.form_submit_button("Salvar"):
        supa.table("jogos").insert({
            "nome": nome, "nome_evento": nome_evento or None, "preco_brl": preco,
            "status": status, "sku": sku or None, "categoria": categoria or None, "ativo": ativo
        }).execute()
        st.success("Jogo salvo!")
res = supa.table("jogos").select("*").order("created_at", desc=True).execute()
table = TableData.from_records(res.data)
st.dataframe(table.as_streamlit_data(), use_container_width=True)

if not table.empty:
    st.download_button("Exportar CSV", table.to_csv(), "jogos.csv", "text/csv")
