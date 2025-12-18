import streamlit as st
from services.supabase_client import get_client

st.set_page_config(page_title="Login — Ludinho", page_icon="🔐")
st.title("🔐 Login (Banco de Dados)")

supa = get_client()

# Já logado?
if st.session_state.get("auth_ok"):
    nome = st.session_state.get("auth_user_name")
    email = st.session_state.get("auth_user_email","?")
    role = st.session_state.get("auth_role","?")
    ident = f"{nome} <{email}>" if nome else email
    st.success(f"Você já está logado como *{ident}* (role: {role}).")

    # Apenas admin pode cadastrar novos usuários
    if role == "admin":
        with st.expander("Cadastrar novo usuário (admin)"):
            with st.form("novo_user"):
                novo_email = st.text_input("E-mail do novo usuário")
                novo_nome = st.text_input("Nome do novo usuário")
                novo_senha = st.text_input("Senha", type="password")
                novo_role = st.selectbox("Role", ["normal", "admin"], index=0)
                if st.form_submit_button("Criar usuário"):
                    if not novo_email or not novo_senha:
                        st.error("Preencha e-mail e senha.")
                    else:
                        try:
                            r = supa.rpc(
                                "auth_create_user",
                                {
                                    "p_email": novo_email,
                                    "p_password": novo_senha,
                                    "p_role": novo_role,
                                    "p_nome": novo_nome or None,
                                },
                            ).execute()
                            data = getattr(r, "data", None)
                            if data and data.get("email"):
                                label = data.get("nome") or data.get("email")
                                st.success(f"Usuário criado: {label} ({data.get('role')})")
                            else:
                                st.warning("Não foi possível criar (já existe?)")
                        except Exception as e:
                            st.error(str(e))

    col_a, col_b = st.columns([1,2])
    with col_a:
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()
    with col_b:
        st.page_link("pages/01_Dashboard.py", label="Ir para o Dashboard →")

    st.stop()

# Form de login
with st.form("login_db"):
    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")
    ok = st.form_submit_button("Entrar")

    if ok:
        try:
            r = supa.rpc("auth_verify_user", {"p_email": email, "p_password": senha}).execute()
            data = getattr(r, "data", None)
            if data and data.get("email"):
                st.session_state["auth_ok"] = True
                st.session_state["auth_user_email"] = data.get("email")
                st.session_state["auth_role"] = data.get("role")
                st.session_state["auth_user_name"] = data.get("nome")
                label = data.get("nome") or data.get("email")
                st.success(f"Login efetuado como {label}!")
                st.page_link("pages/01_Dashboard.py", label="Ir para o Dashboard →")
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
        except Exception as e:
            st.error(str(e))

st.caption("Autenticação usando funções SQL (pgcrypto/crypt) no banco.")
