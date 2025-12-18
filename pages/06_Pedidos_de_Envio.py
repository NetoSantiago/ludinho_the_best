import streamlit as st, pandas as pd, asyncio, json
from services.envios_service import listar_envios, atualizar_status_envio
from services.supabase_client import get_client
from services.whatsapp_service import send_message
from services.utils import format_ts

st.title("Pedidos de Envio")

# ====== Auth guard ======
if not st.session_state.get("auth_ok"):
    st.info("Acesso restrito. Vá para a página **Login** no menu lateral e autentique-se.")
    st.stop()

# (opcional) botão de sair na sidebar
with st.sidebar:
    st.caption(f"Logado como: {st.session_state.get('auth_user_name','?')}")
    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()

# ===== Filtro e listagem =====
status = st.selectbox(
    "Filtrar status",
    ["Todos", "PENDENTE", "EM_PREPARACAO", "AGUARDANDO_PAGAMENTO", "ENVIADO", "CANCELADO"],
)

data = listar_envios(None if status == "Todos" else status)
df = pd.DataFrame(data or [])

if df.empty:
    st.info("Nenhum pedido encontrado para o filtro atual.")
else:
    # Tabela geral
    df = format_ts(df)
    st.dataframe(df, use_container_width=True)

    # ===== Seleção (itens clicáveis) =====
    st.subheader("Detalhes do envio")

    def _label(row):
        return f"{str(row.get('created_at',''))[:19]} • {str(row.get('id',''))[:8]} • {row.get('status_envio','?')} • {row.get('telefone_cliente','?')}"

    registros = df.to_dict("records")
    labels = [_label(r) for r in registros]
    escolha = st.selectbox("Selecione um envio", ["— selecione —"] + labels, index=0)

    if escolha != "— selecione —":
        envio = registros[labels.index(escolha)]
        envio_id = envio.get("id")

        # Metadados chave
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Status", envio.get("status_envio", "?"))
        with col2:
            st.caption(
                f"Cliente: {envio.get('nome_cliente','')} — {envio.get('telefone_cliente','')}"
            )
        with col3:
            st.caption(f"Container: {envio.get('container_id','')}")

        # Snapshot de itens
        st.markdown("**Itens do envio (snapshot)**")
        snapshot = envio.get("itens_snapshot_json")
        try:
            if isinstance(snapshot, str):
                snapshot = json.loads(snapshot)
        except Exception:
            pass
        if isinstance(snapshot, list) and snapshot:
            df_snap = pd.DataFrame(snapshot)
            st.dataframe(df_snap, use_container_width=True)
        else:
            st.caption("(sem itens no snapshot)")

        # ===== Atualizar status + Notificar =====
        st.divider()
        st.subheader("Atualizar & Notificar")
        statuses = [
            "PENDENTE",
            "EM_PREPARACAO",
            "AGUARDANDO_PAGAMENTO",
            "ENVIADO",
            "CANCELADO",
        ]
        cur = envio.get("status_envio", "PENDENTE")
        idx = statuses.index(cur) if cur in statuses else 0
        novo_status = st.selectbox("Novo status", statuses, index=idx)
        telefone = st.text_input(
            "Telefone do cliente", value=str(envio.get("telefone_cliente", ""))
        )
        info_extra = st.text_area(
            "Informação adicional (opcional)",
            placeholder="Ex.: Seu código de rastreio é XX123... ou Valor/Chave PIX...",
        )

        c1, c2 = st.columns(2)
        if c1.button("Salvar status"):
            try:
                r = atualizar_status_envio(envio_id, novo_status)
                st.success(f"Status atualizado: {r['status_envio']}")
            except Exception as e:
                st.error(str(e))

        if c2.button("Notificar via WhatsApp"):
            if not telefone:
                st.error("Informe o telefone do cliente.")
            else:
                try:
                    base = f"Seu pedido {envio_id} agora está: {novo_status}."
                    if novo_status == "AGUARDANDO_PAGAMENTO":
                        base += (
                            "\n\nPara concluir, efetue o pagamento conforme instruções. "
                            "Em seguida, envie o comprovante com: COMPROVANTE <ID_DA_TRANSACAO>."
                        )
                    if info_extra:
                        base += f"\n\n{info_extra}"
                    asyncio.run(send_message(telefone, base))
                    st.success("Notificado!")
                except Exception as e:
                    st.error(str(e))
