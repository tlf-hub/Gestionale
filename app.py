"""⬡ Gestionale Aziendale — Home"""
import streamlit as st
from database import init_db
from utils.styles import COMMON_CSS
from utils.auth import check_auth, create_default_admin, logout_button

st.set_page_config(page_title="Gestionale Aziendale", page_icon="⬡",
                   layout="wide", initial_sidebar_state="expanded")

init_db()
create_default_admin()
st.markdown(COMMON_CSS, unsafe_allow_html=True)
check_auth()
logout_button()

# Header
st.markdown("""
<div class="page-header">
<h2>⬡ Gestionale Aziendale</h2>
<p>Prestazioni · Fatturazione Elettronica · Incassi SDD SEPA</p>
</div>
""", unsafe_allow_html=True)

# Quick stats
from database import get_session
from models import Cliente, Prestazione, Fattura, Incasso
from utils.helpers import format_currency

session = get_session()
try:
    n_clienti = session.query(Cliente).filter(Cliente.cliente_attivo == True).count()
    n_prest = session.query(Prestazione).count()
    n_fatt = session.query(Fattura).count()
    n_inc = session.query(Incasso).filter(Incasso.stato == "Caricato da confermare").count()
finally:
    session.close()

c1, c2, c3, c4 = st.columns(4)
c1.metric("👥 Clienti attivi", n_clienti)
c2.metric("📊 Prestazioni", n_prest)
c3.metric("📄 Fatture emesse", n_fatt)
c4.metric("⏳ SDD da confermare", n_inc)

st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("### 📊 Dashboard\nGestione prestazioni, filtri, emissione fatture, XML FatturaPA, SDD SEPA.")
with col2:
    st.markdown("### 👥 Clienti\nAnagrafica completa, SDD, rappresentante legale. Controllo doppioni.")
with col3:
    st.markdown("### 📤 Import/Export\nCaricamento massivo Excel/CSV con template. Export di tutte le tabelle.")

st.info("👈 Usa il menu laterale per navigare tra le sezioni.")
