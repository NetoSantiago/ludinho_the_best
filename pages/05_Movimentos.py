import streamlit as st, pandas as pd
from services.supabase_client import get_client
from services.movimentos_service import add_item_by_movimento, list_movimentos
from services.utils import format_ts

st.title("Movimentos (Compra/Listinha)")

supa = get_client()

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

# ---- Dados auxiliares para os dropdowns ----
try:
    _jogos = supa.table("jogos").select("id,nome,sku,status,ativo").order("nome").execute().data or []
except Exception:
    _jogos = []
try:
    _clientes = supa.table("clientes").select("telefone,nome").order("created_at", desc=True).limit(1000).execute().data or []
except Exception:
    _clientes = []

# ---- Formulário para registrar novo movimento ----
st.subheader("Novo movimento")
with st.form("add_mov"):
    tipo = st.selectbox("Tipo", ["COMPRA","LISTINHA"])

    # Cliente (dropdown com busca)
    colc1, colc2 = st.columns([2,3])
    with colc1:
        termo_cli = st.text_input("Buscar cliente (nome/telefone)")
    if termo_cli:
        cli_filtrados = [c for c in _clientes if termo_cli.lower() in str(c.get("nome","")) .lower() or termo_cli in str(c.get("telefone",""))]
    else:
        cli_filtrados = _clientes
    cli_labels = [f"{c.get('nome','(sem nome)')} — {c.get('telefone')}" for c in cli_filtrados]
    cli_opts = [c.get("telefone") for c in cli_filtrados]
    telefone = st.selectbox("Telefone do cliente", options=["— selecione —"] + cli_opts, format_func=lambda v: ("— selecione —" if v=="— selecione —" else next((lbl for lbl, val in zip(cli_labels, cli_opts) if val==v), v)))

    # Jogo (dropdown com busca)
    colj1, colj2 = st.columns([2,3])
    with colj1:
        termo_jogo = st.text_input("Buscar jogo (nome/SKU)")
    if termo_jogo:
        jogos_filtrados = [j for j in _jogos if termo_jogo.lower() in str(j.get("nome","")) .lower() or termo_jogo.lower() in str(j.get("sku","")) .lower()]
    else:
        jogos_filtrados = _jogos
    jogos_labels = [f"{j.get('nome','(sem nome)')}" + (f" (SKU {j['sku']})" if j.get('sku') else "") + f" [{str(j.get('id',''))[:8]}]" for j in jogos_filtrados]
    jogos_opts = [j.get("id") for j in jogos_filtrados]
    jogo_id = st.selectbox("Jogo", options=["— selecione —"] + jogos_opts, format_func=lambda v: ("— selecione —" if v=="— selecione —" else next((lbl for lbl, val in zip(jogos_labels, jogos_opts) if val==v), str(v))))

    preco = st.number_input("Preço aplicado (BRL)", min_value=0.0, step=1.0)
    status_item = st.selectbox("Status do item", ["DISPONIVEL","PRE-VENDA","RESERVADO"])

    if st.form_submit_button("Registrar movimento"):
        if jogo_id == "— selecione —" or telefone == "— selecione —":
            st.error("Selecione um cliente e um jogo.")
        else:
            try:
                r = add_item_by_movimento(tipo, telefone, jogo_id, preco, status_item)
                cid = (r or {}).get("container_id", "—")
                st.success(f"Movimento criado no container {cid}")
            except Exception as e:
                st.error("Falha ao criar movimento.")
                st.exception(e)

# ---- Lista de movimentos ----
st.subheader("Últimos movimentos")
try:
    df = pd.DataFrame(list_movimentos(200))
    if df.empty:
        st.info("Nenhum movimento encontrado.")
    else:
        df = format_ts(df)
        st.dataframe(df, use_container_width=True)
        st.download_button("Exportar CSV", df.to_csv(index=False), "movimentos.csv", "text/csv")

        # Detalhe de uma transação específica
        st.markdown("**Detalhe do movimento**")
        # Opções com label amigável
        def _label_mov(row):
            return f"{str(row.get('created_at',''))[:19]} • {row.get('tipo','?')} • {row.get('telefone_cliente','?')} • jogo {str(row.get('jogo_id',''))[:8]} • R$ {row.get('preco_aplicado_brl',0)}"
        opts = df.to_dict("records")
        labels = [_label_mov(r) for r in opts]
        pick = st.selectbox("Selecionar movimento", ["— selecione —"] + labels, index=0, key="mov_pick")
        if pick != "— selecione —":
            sel = opts[labels.index(pick)]
            st.json(sel)
except Exception as e:
    st.error("Falha ao carregar movimentos.")
    st.exception(e)
