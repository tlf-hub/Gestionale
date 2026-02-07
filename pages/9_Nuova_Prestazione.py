"""➕ Nuova Prestazione — Aperta in nuova scheda dalla Dashboard."""
import streamlit as st
from datetime import date
from decimal import Decimal
import calendar
from database import get_session, init_db
from models import Prestazione, Cliente, ContoRicavo, SoggettoFatturante
from config import PERIODICITA_OPTIONS, MODALITA_INCASSO_OPTIONS, ALIQUOTA_OPTIONS
from utils.styles import COMMON_CSS
from utils.auth import check_auth, logout_button

st.set_page_config(page_title="Nuova Prestazione", page_icon="➕", layout="wide")
init_db(); st.markdown(COMMON_CSS, unsafe_allow_html=True); check_auth(); logout_button()

params = st.query_params
default_month = int(params.get("month", date.today().month))
default_year = int(params.get("year", date.today().year))

st.markdown("""
<div class="page-header">
<h2>➕ Nuova Prestazione</h2>
</div>""", unsafe_allow_html=True)

session = get_session()
try:
    clienti = session.query(Cliente).filter(Cliente.cliente_attivo == True).order_by(Cliente.cognome_ragione_sociale).all()
    conti = session.query(ContoRicavo).order_by(ContoRicavo.codice).all()
    fatturanti = session.query(SoggettoFatturante).order_by(SoggettoFatturante.ragione_sociale).all()

    if not clienti or not conti or not fatturanti:
        st.warning("⚠️ Serve almeno un Cliente, Conto Ricavo e Soggetto Fatturante.")
        st.stop()

    with st.form("new_prest"):
        c1, c2 = st.columns(2)
        with c1:
            n_cl = st.selectbox("Cliente *", clienti, format_func=lambda c: c.denominazione)
            n_cr = st.selectbox("Conto Ricavo *", conti, format_func=lambda c: f"{c.codice} - {c.descrizione}")
            n_desc = st.text_input("Descrizione *")
            n_imp = st.number_input("Importo € *", min_value=0.0, step=0.01)
        with c2:
            n_ft = st.selectbox("Fatturante *", fatturanti, format_func=lambda f: f.ragione_sociale)
            n_per = st.selectbox("Periodicità", PERIODICITA_OPTIONS)
            n_aliq = st.selectbox("Aliquota IVA %", ALIQUOTA_OPTIONS, index=4)
            n_mod = st.selectbox("Mod. Incasso", MODALITA_INCASSO_OPTIONS)
        d1, d2 = st.columns(2)
        n_di = d1.date_input("Data Inizio", value=date(default_year, default_month, 1))
        ld = calendar.monthrange(default_year, default_month)[1]
        n_df = d2.date_input("Data Fine", value=date(default_year, default_month, ld))
        n_note = st.text_area("Note")

        submitted = st.form_submit_button("💾 Salva", type="primary", use_container_width=True)
        if submitted:
            if not n_desc:
                st.error("La descrizione è obbligatoria.")
            elif n_imp <= 0:
                st.error("L'importo deve essere maggiore di zero.")
            else:
                new_p = Prestazione(
                    cliente_id=n_cl.id, conto_ricavo_id=n_cr.id, fatturante_id=n_ft.id,
                    periodicita=n_per, descrizione=n_desc,
                    importo_unitario=Decimal(str(n_imp)), aliquota_iva=n_aliq,
                    data_inizio=n_di, data_fine=n_df, modalita_incasso=n_mod, note=n_note or "")
                session.add(new_p)
                session.commit()
                st.success(f"✅ Prestazione creata (ID: {new_p.id})! Puoi chiudere questa scheda o crearne un'altra.")
                st.balloons()
finally:
    session.close()
