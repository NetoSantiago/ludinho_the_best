import re
import streamlit as st, pandas as pd
from services.supabase_client import get_client
from services.utils import format_ts

st.title("LudoCoins")

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

# ===== Seleção do cliente (com busca) =====
try:
    _clientes = (
        supa.table("clientes")
        .select("telefone,nome,ludocoins_saldo")
        .order("created_at", desc=True)
        .limit(2000)
        .execute()
        .data
        or []
    )
except Exception:
    _clientes = []

col_f1, col_f2 = st.columns([2, 3])
with col_f1:
    termo_cli = st.text_input("Buscar cliente (nome/telefone)")

if termo_cli:
    cli_filtrados = [
        c
        for c in _clientes
        if termo_cli.lower() in str(c.get("nome", "")).lower()
        or termo_cli in str(c.get("telefone", ""))
    ]
else:
    cli_filtrados = _clientes

cli_labels = [f"{c.get('nome','(sem nome)')} — {c.get('telefone')}" for c in cli_filtrados]
cli_opts = [c.get("telefone") for c in cli_filtrados]

telefone = st.selectbox(
    "Cliente",
    options=["— selecione —"] + cli_opts,
    format_func=lambda v: (
        "— selecione —"
        if v == "— selecione —"
        else next((lbl for lbl, val in zip(cli_labels, cli_opts) if val == v), v)
    ),
)

if telefone != "— selecione —":
    tel = re.sub(r"\D+", "", telefone or "")

    # ===== Saldo atual =====
    try:
        cli = (
            supa.table("clientes")
            .select("nome,ludocoins_saldo")
            .eq("telefone", tel)
            .maybe_single()
            .execute()
            .data
            or {}
        )
        saldo = float(cli.get("ludocoins_saldo", 0.0))
    except Exception:
        cli, saldo = {}, 0.0

    st.metric("Saldo atual (L$)", f"{saldo:.2f}")

    st.divider()

    # ===== Debitar LudoCoins =====
    st.subheader("Debitar LudoCoins (uso pelo cliente)")
    with st.form("debitar_lc"):
        valor = st.number_input("Valor a debitar (L$)", min_value=0.0, step=1.0)
        obs = st.text_input("Observação (opcional)", placeholder="Ex.: Uso em compra #1234")
        if st.form_submit_button("Debitar"):
            if valor <= 0:
                st.error("Informe um valor maior que zero.")
            elif valor > saldo:
                st.error("Saldo insuficiente para débito.")
            else:
                try:
                    # 1) registra a transação
                    supa.table("ludocoin_transacoes").insert(
                        {
                            "telefone_cliente": tel,
                            "tipo": "DEBITO_UTILIZACAO",
                            "valor": float(valor),
                            "observacao": obs or None,
                        }
                    ).execute()
                    # 2) atualiza o saldo do cliente
                    novo_saldo = saldo - float(valor)
                    supa.table("clientes").update({"ludocoins_saldo": novo_saldo}).eq(
                        "telefone", tel
                    ).execute()
                    st.success(f"Débito realizado. Novo saldo: {novo_saldo:.2f} L$.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    # ===== Últimas transações =====
    st.subheader("Últimas transações")
    try:
        txs = (
            supa.table("ludocoin_transacoes")
            .select("created_at,tipo,valor,referencia_item_id,observacao")
            .eq("telefone_cliente", tel)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
        df = pd.DataFrame(txs)
        if df.empty:
            st.caption("(sem transações)")
        else:
            df = format_ts(df)
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error("Falha ao carregar transações.")
        st.exception(e)
else:
    st.info("Selecione um cliente para visualizar saldo e transações.")
