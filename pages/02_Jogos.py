import streamlit as st, pandas as pd
from services.supabase_client import get_client
from services.utils import format_ts

st.title("Jogos")
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

# --- Busca/seleção de jogo existente ---
res_all = supa.table("jogos").select("*").order("created_at", desc=True).execute()
df_all = pd.DataFrame(res_all.data or [])

col_b1, col_b2 = st.columns([2, 1])
with col_b1:
    termo = st.text_input("Buscar por nome", placeholder="ex.: Zelda", help="Filtra a lista abaixo pelo nome do jogo")

# Aplica filtro local (mínima alteração; sem mudar chamadas ao backend)
if not df_all.empty and termo:
    df_filtrado = df_all[df_all["nome"].astype(str).str.contains(termo, case=False, na=False)].copy()
else:
    df_filtrado = df_all.copy()


# Selectbox para escolher um jogo e editar
opcoes = []
if not df_filtrado.empty:
    # Mostra identificação amigável: Nome (SKU) [id curto]
    id_short = df_filtrado.get("id").astype(str).str[:8] if "id" in df_filtrado.columns else pd.Series(["—"]*len(df_filtrado))
    labels = df_filtrado.apply(lambda r: f"{r.get('nome','(sem nome)')}" + (f" (SKU {r['sku']})" if r.get('sku') else "") + (f" [{id_short.loc[r.name]}]" if 'id' in df_filtrado.columns else ""), axis=1)
    opcoes = list(zip(labels.tolist(), df_filtrado.get("id", pd.Series([None]*len(df_filtrado))).tolist()))

with col_b2:
    idx_sel = 0
    if opcoes:
        label_list = [lbl for (lbl, _id) in opcoes]
        escolha = st.selectbox("Selecionar jogo", label_list, index=0 if label_list else None)
        # reobtem o id selecionado
        try:
            sel_id = opcoes[label_list.index(escolha)][1]
        except Exception:
            sel_id = None
    else:
        escolha = None
        sel_id = None

# Form de edição do jogo selecionado
if sel_id:
    jsel = df_all[df_all.get("id").astype(str) == str(sel_id)].iloc[0].to_dict()
    st.subheader("Editar jogo selecionado")
    with st.form("editar_jogo"):
        nome = st.text_input("Nome (público)", value=str(jsel.get("nome", "")))
        nome_evento = st.text_input("Nome para evento (interno/opcional)", value=str(jsel.get("nome_evento") or ""))
        preco = st.number_input("Preço (BRL)", min_value=0.0, step=1.0, value=float(jsel.get("preco_brl") or 0.0))
        status = st.selectbox("Status", ["DISPONIVEL","PRE-VENDA"], index=0 if str(jsel.get("status"))=="DISPONIVEL" else 1)
        sku = st.text_input("SKU", value=str(jsel.get("sku") or ""))
        categoria = st.text_input("Categoria", value=str(jsel.get("categoria") or ""))
        ativo = st.checkbox("Ativo", value=bool(jsel.get("ativo", True)))
        if st.form_submit_button("Salvar alterações"):
            supa.table("jogos").update({
                "nome": nome,
                "nome_evento": nome_evento or None,
                "preco_brl": preco,
                "status": status,
                "sku": sku or None,
                "categoria": categoria or None,
                "ativo": ativo
            }).eq("id", sel_id).execute()
            st.success("Jogo atualizado!")

st.divider()

# --- Cadastro de novo jogo (mantém bloco original) ---
st.subheader("Cadastrar novo jogo")
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
            "nome": nome,
            "nome_evento": nome_evento or None,
            "preco_brl": preco,
            "status": status,
            "sku": sku or None,
            "categoria": categoria or None,
            "ativo": ativo
        }).execute()
        st.success("Jogo salvo!")

# --- Tabela (id curto) ---
st.subheader("Jogos cadastrados")
if not df_all.empty:
    df_view = df_all.copy()
    if "id" in df_view.columns:
        df_view.insert(0, "id_curto", df_view["id"].astype(str).str[:8])
        # Opcionalmente esconde o id completo para uma visualização mais limpa
        df_view = df_view.drop(columns=["id"])  # mantém apenas id_curto
    df_view = format_ts(df_view)
    st.dataframe(df_view, use_container_width=True)
    st.download_button("Exportar CSV", df_view.to_csv(index=False), "jogos.csv", "text/csv")
else:
    st.info("Nenhum jogo cadastrado ainda.")
