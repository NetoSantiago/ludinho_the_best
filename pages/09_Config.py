import streamlit as st, os

# ====== Auth guard ======
if not st.session_state.get("auth_ok"):
    st.info("Acesso restrito. Vá para a página **Login** no menu lateral e autentique-se.")
    st.stop()

if st.session_state.get("auth_role") != "admin":
    st.info("Você não tem acesso a esta página.")
    st.stop()

# (opcional) botão de sair na sidebar
with st.sidebar:
    st.caption(f"Logado como: {st.session_state.get('auth_user_name','?')}")
    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()

st.title("Configurações (somente leitura)")

for k in ["SUPABASE_URL","TZ","WA_BASE_URL","PUBLIC_WEBHOOK_URL"]:
    st.write(f"**{k}** = `{os.getenv(k,'(não definido)')}`")

st.info("A taxa de conversão é fixa em 15%.")
