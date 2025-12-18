import re
import streamlit as st, pandas as pd
from services.supabase_client import get_client
from services.containers_service import get_or_create_open_container, list_container_items, list_trocaveis
from services.ludocoins_service import convert_item
from services.utils import format_ts

st.title('Containers')

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

# ==== Filtro por telefone (apenas dígitos) ====
col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    filtro_tel = st.text_input('Buscar por telefone do cliente', placeholder='ex.: 5585...', help='Filtra a listagem pelo telefone do cliente (apenas dígitos)')
    filtro_tel_norm = re.sub('[^0-9]+', '', filtro_tel or '')
with col_f2:
    page_size = 10
    if 'containers_page' not in st.session_state:
        st.session_state['containers_page'] = 0

# ==== Carrega containers ====
res = supa.table('containers').select('*').order('updated_at', desc=True).order('created_at', desc=True).execute()
df_cont = pd.DataFrame(res.data or [])
if not df_cont.empty and filtro_tel_norm:
    df_cont = df_cont[df_cont['telefone_cliente'].astype(str).str.contains(filtro_tel_norm, na=False)]

# ==== Paginação ====
num_rows = len(df_cont)
num_pages = max(1, (num_rows + page_size - 1) // page_size)
cur_page = min(st.session_state.get('containers_page', 0), num_pages - 1)
start = cur_page * page_size
end = start + page_size

st.subheader('Lista de containers')
if df_cont.empty:
    st.info('Nenhum container encontrado.')
else:
    df_view = df_cont.copy()
    df_view = format_ts(df_view)
    cols_show = [c for c in ['id','telefone_cliente','status','created_at','updated_at'] if c in df_view.columns]
    st.caption(f'Mostrando {min(page_size, len(df_view.iloc[start:end]))} de {num_rows} registros • Página {cur_page+1}/{num_pages}')
    st.dataframe(df_view.iloc[start:end][cols_show], use_container_width=True)

    # Navegação
    c_prev, c_page, c_next = st.columns([1,2,1])
    with c_prev:
        if st.button('◀️ Anterior', disabled=(cur_page<=0)):
            st.session_state['containers_page'] = max(0, cur_page-1)
            st.rerun()
    with c_page:
        st.write('')
    with c_next:
        if st.button('Próxima ▶️', disabled=(cur_page>=num_pages-1)):
            st.session_state['containers_page'] = min(num_pages-1, cur_page+1)
            st.rerun()

    # Seleção de um container por id completo (sem short id)
    st.markdown('**Abrir detalhes**')
    slice_ids = df_view.iloc[start:end]['id'].astype(str).tolist() if 'id' in df_view.columns else []
    slice_labels = [f"{i+1+start}. {sid} — {df_view.iloc[start+i]['telefone_cliente']} ({df_view.iloc[start+i]['status']})" for i, sid in enumerate(slice_ids)]
    escolha = st.selectbox('Selecione um container', ['— selecione —'] + slice_labels, index=0, key='select_container')
    if escolha != '— selecione —':
        try:
            idx = slice_labels.index(escolha)
            sel_container_id = slice_ids[idx]
            st.session_state['container_id'] = sel_container_id
        except Exception:
            pass

# ==== Atalho: Abrir/Obter container ABERTO pelo telefone (mantém comportamento) ====
st.divider()
st.subheader('Atalho: Container ABERTO do cliente')
telefone = st.text_input('Telefone do cliente (abrir/obter ABERTO)')
if st.button('Abrir/Obter container (ABERTO)') and telefone:
    st.session_state['container_id'] = get_or_create_open_container(re.sub('[^0-9]+','', telefone))

# ==== DETALHES DO CONTAINER SELECIONADO ====
cid = st.session_state.get('container_id')
if cid:
    st.markdown('**Detalhes do container**')
    st.info(f'Container atual: {cid}')

    # Metadados básicos
    try:
        meta = supa.table('containers').select('*').eq('id', cid).maybe_single().execute().data or {}
    except Exception:
        meta = {}
    if meta:
        colm1, colm2, colm3 = st.columns(3)
        with colm1:
            st.metric('Status', meta.get('status','?'))
        with colm2:
            st.caption(f"Criado em: {meta.get('created_at','')}")
        with colm3:
            st.caption(f"Atualizado em: {meta.get('updated_at','')}")

    # Itens do container
    itens = list_container_items(cid) or []
    if itens:
        df_it = pd.DataFrame([{ 
            'id': it.get('id'),
            'jogo': (it.get('jogos') or {}).get('nome'),
            'origem': it.get('origem'),
            'status_item': it.get('status_item'),
            'preco_aplicado_brl': it.get('preco_aplicado_brl'),
        } for it in itens])
        # Mantém short id para itens (são UUIDs longos); o pedido do cliente era para containers
        df_it.insert(0, 'id_curto', df_it['id'].astype(str).str[:8])
        st.subheader('Itens no container')
        st.dataframe(df_it.drop(columns=['id']), use_container_width=True)
    else:
        st.info('Este container não possui itens (ou apenas itens RESGATADO).')

    # Conversão por seleção (LISTINHA, DISPONIVEL/PRE-VENDA) — permitido só se container ABERTO
    st.subheader('Converter item em LudoCoins')
    if (meta or {}).get('status') != 'ABERTO':
        st.warning('Conversão só é permitida em containers ABERTO.')
    else:
        trocaveis = list_trocaveis(cid) or []
        if not trocaveis:
            st.caption('Nenhum item elegível à conversão no momento.')
        else:
            labels = [f"{(it.get('jogos') or {}).get('nome','(sem nome)')} — {it.get('origem')} / {it.get('status_item')} — crédito {(float(it.get('preco_aplicado_brl') or 0)*0.85):.2f} L$" for it in trocaveis]
            pick = st.selectbox('Selecione o item a converter', ['— selecione —'] + labels, index=0, key='conv_pick')
            atendente = st.text_input('E-mail do atendente (obrigatório)', value='atendente@ludolovers')
            if st.button('Converter agora', disabled=(pick=='— selecione —')):
                if not atendente or '@' not in atendente:
                    st.error('Informe um e-mail válido do atendente para auditoria.')
                else:
                    try:
                        it_sel = trocaveis[labels.index(pick)]
                        r = convert_item(it_sel.get('id'), atendente)
                        st.success(f'OK: {r}')
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
