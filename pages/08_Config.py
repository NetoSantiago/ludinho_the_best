import streamlit as st, os

st.title("Configurações (somente leitura)")

for k in ["SUPABASE_URL","TZ","WA_BASE_URL","PUBLIC_WEBHOOK_URL"]:
    st.write(f"**{k}** = `{os.getenv(k,'(não definido)')}`")

st.info("A taxa de conversão é fixa em 15%.")
