import re

import streamlit as st, pandas as pd
from services.containers_service import get_or_create_open_container, list_container_items
from services.ludocoins_service import convert_item

st.title("Containers")

telefone_input = st.text_input("Telefone do cliente", placeholder="11999998888")
telefone = re.sub(r"\D+", "", telefone_input or "")

if telefone_input and telefone != telefone_input:
    st.caption("Somente números serão considerados para localizar o cliente.")

abrir_container = st.button("Abrir/Obter container (ABERTO)")

if abrir_container:
    if telefone:
        container_id = get_or_create_open_container(telefone)
        if container_id:
            st.session_state["container_id"] = container_id
            st.success("Container carregado com sucesso.")
        else:
            st.error("Não foi possível localizar ou criar o container. Verifique o telefone informado.")
    else:
        st.warning("Informe um telefone válido antes de continuar.")
cid = st.session_state.get("container_id")

if cid:
    st.info(f"Container atual: {cid}")
    itens = list_container_items(cid)
    df = pd.DataFrame([{
        "id": it["id"],
        "jogo": (it.get("jogos") or {}).get("nome","Jogo"),
        "origem": it["origem"],
        "status_item": it["status_item"],
        "preco_aplicado_brl": it["preco_aplicado_brl"],
        "elegivel_ludocoin": it["elegivel_ludocoin"]
    } for it in itens])
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Este container ainda não possui itens cadastrados.")
    st.subheader("Converter item elegível")
    item_id = st.text_input("ID do item")
    atendente = st.text_input("Seu e-mail", value="atendente@ludolovers")

    if st.button("Converter"):
        if not item_id.strip():
            st.warning("Informe o ID do item que deseja converter.")
        else:
            try:
                r = convert_item(item_id.strip(), atendente)
                st.success(f"OK: {r}")
            except Exception as e:
                st.error(str(e))
