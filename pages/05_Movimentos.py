import streamlit as st, pandas as pd
from services.containers_service import add_item_by_movimento
from services.movimentos_service import list_movimentos

st.title("Movimentos (Compra/Rifa)")
with st.form("add_mov"):
    tipo = st.selectbox("Tipo", ["COMPRA","RIFA"])
    telefone = st.text_input("Telefone do cliente")
    jogo_id = st.text_input("Jogo ID (uuid)")
    preco = st.number_input("Preço aplicado (BRL)", min_value=0.0, step=1.0)
    status_item = st.selectbox("Status do item", ["DISPONIVEL","PRE-VENDA","RESERVADO"])
    if st.form_submit_button("Registrar movimento"):
        try:
            r = add_item_by_movimento(tipo, telefone, jogo_id, preco, status_item)
            st.success(f"Movimento criado no container {r['container_id']}")
        except Exception as e:
            st.error(str(e))

st.subheader("Últimos movimentos")
df = pd.DataFrame(list_movimentos(100))
st.dataframe(df, use_container_width=True)

if not df.empty:
    st.download_button("Exportar CSV", df.to_csv(index=False), "movimentos.csv", "text/csv")
