import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from services.reports_service import passivo_ludocoins, containers_por_status
from services.supabase_client import get_client
from services.utils import format_ts

st.title("Dashboard")
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

col1, col2, col3, col4 = st.columns(4)

# --- Métrica: Passivo de LudoCoins ---
try:
    col1.metric("Passivo de LudoCoins (L$)", f"{passivo_ludocoins():.2f}")
except Exception:
    col1.metric("Passivo de LudoCoins (L$)", "—")

# --- Métrica: Containers Abertos ---
try:
    df_ct = containers_por_status()
    total_abertos = int(df_ct[df_ct["status"] == "ABERTO"]["quantidade"].sum()) if not df_ct.empty else 0
except Exception:
    total_abertos = 0
col2.metric("Containers Abertos", total_abertos)

# --- Métrica: Jogos Ativos ---
try:
    jogos = supa.table("jogos").select("id").eq("ativo", True).execute().data or []
    col3.metric("Jogos Ativos", len(jogos))
except Exception:
    col3.metric("Jogos Ativos", "—")

# --- Métrica: Clientes ---
try:
    clientes = supa.table("clientes").select("telefone").execute().data or []
    col4.metric("Clientes", len(clientes))
except Exception:
    col4.metric("Clientes", "—")

st.divider()

# --- Tendências (7 e 30 dias) ---
st.subheader("Tendências")

now_utc = datetime.now(timezone.utc)

def _date_index(days: int):
    start = (now_utc - timedelta(days=days-1)).date()
    end = now_utc.date()
    return pd.date_range(start=start, end=end, freq="D")

def _load_window(days: int):
    since_iso = (now_utc - timedelta(days=days)).isoformat()
    # Movimentos por dia e tipo
    try:
        _mov = supa.table("movimentos").select("tipo,created_at").gte("created_at", since_iso).execute().data or []
        dfm = pd.DataFrame(_mov)
        if not dfm.empty:
            dfm["dia"] = pd.to_datetime(dfm["created_at"]).dt.date
            mov_by_day = dfm.groupby(["dia","tipo"]).size().unstack(fill_value=0)
            mov_by_day.index = pd.to_datetime(mov_by_day.index)
            mov_by_day = mov_by_day.reindex(_date_index(days), fill_value=0).sort_index()
        else:
            mov_by_day = pd.DataFrame()
    except Exception:
        mov_by_day = pd.DataFrame()
    # Abertura de containers por dia
    try:
        _cont = supa.table("containers").select("created_at").gte("created_at", since_iso).execute().data or []
        dfc = pd.DataFrame(_cont)
        if not dfc.empty:
            dfc["dia"] = pd.to_datetime(dfc["created_at"]).dt.date
            open_by_day = dfc.groupby("dia").size().rename("aberturas").to_frame()
            open_by_day.index = pd.to_datetime(open_by_day.index)
            open_by_day = open_by_day.reindex(_date_index(days), fill_value=0).sort_index()
        else:
            open_by_day = pd.DataFrame()
    except Exception:
        open_by_day = pd.DataFrame()
    # LudoCoins: variação acumulada (no período) do total em circulação
    try:
        _lc = supa.table("ludocoin_transacoes").select("tipo,valor,created_at").gte("created_at", since_iso).execute().data or []
        dfl = pd.DataFrame(_lc)
        if not dfl.empty:
            dfl["dia"] = pd.to_datetime(dfl["created_at"]).dt.date
            dfl["valor"] = pd.to_numeric(dfl["valor"], errors="coerce").fillna(0.0)
            # créditos entram (+), débitos saem (-), ajustes conforme sinal
            cred = dfl[dfl["tipo"]=="CREDITO_CONVERSAO"].groupby("dia")["valor"].sum()
            deb = dfl[dfl["tipo"]=="DEBITO_UTILIZACAO"].groupby("dia")["valor"].sum()
            adj = dfl[dfl["tipo"]=="AJUSTE"].groupby("dia")["valor"].sum()
            daily = pd.concat([cred, -deb, adj], axis=1).fillna(0.0).sum(axis=1).rename("var_dia")
            daily.index = pd.to_datetime(daily.index)
            # completa dias faltantes com 0 e faz cumulativo no período
            daily = daily.reindex(_date_index(days), fill_value=0.0).sort_index()
            ludo_var = daily.cumsum().to_frame("variacao_acumulada")
        else:
            ludo_var = pd.DataFrame()
    except Exception:
        ludo_var = pd.DataFrame()
    return mov_by_day, open_by_day, ludo_var

aba7, aba30 = st.tabs(["Últimos 7 dias", "Últimos 30 dias"])
for tab, window in [(aba7,7),(aba30,30)]:
    with tab:
        mov_by_day, open_by_day, ludo_var = _load_window(window)
        st.markdown("**Movimentos por tipo / dia**")
        if not mov_by_day.empty:
            st.line_chart(mov_by_day)
        else:
            st.caption("(sem movimentos no período)")
        st.markdown("**Abertura de containers por dia**")
        if not open_by_day.empty:
            st.bar_chart(open_by_day)
        else:
            st.caption("(sem aberturas no período)")
        st.markdown("**Variação do total em circulação de LudoCoins (acumulada no período)**")
        # KPI: delta no período (L$)
        try:
            _delta = float(ludo_var["variacao_acumulada"].iloc[-1]) if not ludo_var.empty else 0.0
        except Exception:
            _delta = 0.0
        st.metric("Δ no período (L$)", f"{_delta:.2f}")
        if not ludo_var.empty:
            st.line_chart(ludo_var)
        else:
            st.caption("(sem transações no período)")

# --- Containers por status (inclui AGUARDANDO_PAGAMENTO) ---
st.subheader("Containers por status")
try:
    if df_ct.empty:
        st.info("Sem containers.")
    else:
        df_ct = format_ts(df_ct)
        st.dataframe(df_ct.sort_values("quantidade", ascending=False), use_container_width=True)
except Exception as e:
    st.error("Falha ao carregar containers por status.")
    st.exception(e)

# --- Envios por status ---
st.subheader("Envios por status")
try:
    envs = supa.table("envios").select("status_envio").execute().data or []
    df_env = pd.DataFrame(envs)
    if df_env.empty:
        st.info("Sem envios cadastrados.")
    else:
        df_agg = df_env.groupby("status_envio").size().reset_index(name="quantidade").sort_values("quantidade", ascending=False)
        df_agg = format_ts(df_agg)
        st.dataframe(df_agg, use_container_width=True)
except Exception as e:
    st.error("Falha ao carregar envios por status.")
    st.exception(e)

st.divider()

# --- Últimos envios ---
st.subheader("Últimos envios")
try:
    ult_env = supa.table("envios").select("id, status_envio, telefone_cliente, created_at").order("created_at", desc=True).limit(10).execute().data or []
    df_ult_env = pd.DataFrame(ult_env)
    df_ult_env = format_ts(df_ult_env)
    if df_ult_env.empty:
        st.caption("(sem registros)")
    else:
        st.dataframe(df_ult_env, use_container_width=True)
except Exception as e:
    st.error("Falha ao carregar últimos envios.")
    st.exception(e)

# --- Últimos movimentos ---
st.subheader("Últimos movimentos")
try:
    movs = supa.table("movimentos").select("tipo, telefone_cliente, jogo_id, preco_aplicado_brl, created_at").order("created_at", desc=True).limit(10).execute().data or []
    df_movs = pd.DataFrame(movs)
    df_movs = format_ts(df_movs)
    if df_movs.empty:
        st.caption("(sem registros)")
    else:
        st.dataframe(df_movs, use_container_width=True)
except Exception as e:
    st.error("Falha ao carregar últimos movimentos.")
    st.exception(e)
