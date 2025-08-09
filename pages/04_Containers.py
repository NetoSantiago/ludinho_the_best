import streamlit as st, pandas as pd
from services.supabase_client import get_client
from services.containers_service import get_or_create_open_container, list_container_items
from services.ludocoins_service import convert_item

st.title("Containers")

supa = get_client()
telefone = st.text_input("Telefone do cliente")

if st.button("Abrir/Obter container (ABERTO)") and telefone:
    st.session_state["container_id"] = get_or_create_open_container(telefone)
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
    st.dataframe(df, use_container_width=True)
    st.subheader("Converter item elegível")
    item_id = st.text_input("ID do item")
    atendente = st.text_input("Seu e-mail", value="atendente@ludolovers")

    if st.button("Converter"):
        try:
            r = convert_item(item_id, atendente)
            st.success(f"OK: {r}")
        except Exception as e:
            st.error(str(e))
