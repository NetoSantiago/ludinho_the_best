import streamlit as st
from services.envios_service import listar_envios, atualizar_status_envio
from services.whatsapp_service import send_message_sync
from services.table_utils import TableData

st.title("Pedidos de Envio")

status = st.selectbox("Filtrar status", ["Todos","PENDENTE","EM_PREPARACAO","ENVIADO","CANCELADO"])
data = listar_envios(None if status=="Todos" else status)
table = TableData.from_records(data)
st.dataframe(table.as_streamlit_data(), use_container_width=True)
st.subheader("Atualizar & Notificar")
envio_id = st.text_input("ID do envio")
novo_status = st.selectbox("Novo status", ["PENDENTE","EM_PREPARACAO","ENVIADO","CANCELADO"])
telefone = st.text_input("Telefone do cliente")
col1, col2 = st.columns(2)

if col1.button("Atualizar status") and envio_id:
    try:
        r = atualizar_status_envio(envio_id, novo_status)
        st.success(f"Status: {r['status_envio']}")
    except Exception as e:
        st.error(str(e))

if col2.button("Notificar via WhatsApp") and telefone and envio_id:
    try:
        send_message_sync(telefone, f"Seu pedido {envio_id} agora está: {novo_status}.")
        st.success("Notificado!")
    except Exception as e:
        st.error(str(e))
