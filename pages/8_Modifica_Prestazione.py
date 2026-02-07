"""✏️ Modifica Prestazione — Aperta in nuova scheda dalla Dashboard."""
import streamlit as st
from datetime import date
from decimal import Decimal
from database import get_session, init_db
from models import Prestazione, Cliente, ContoRicavo, SoggettoFatturante, Incasso
from config import PERIODICITA_OPTIONS, MODALITA_INCASSO_OPTIONS, ALIQUOTA_OPTIONS
from utils.helpers import format_currency, calc_periodicity_label
from utils.styles import COMMON_CSS
from utils.auth import check_auth, logout_button

st.set_page_config(page_title="Modifica Prestazione", page_icon="✏️", layout="wide")
init_db(); st.markdown(COMMON_CSS, unsafe_allow_html=True); check_auth(); logout_button()

# Leggi ID dalla query string
params = st.query_params
prest_id = params.get("id")

if not prest_id:
    st.error("⚠️ Nessun ID prestazione specificato.")
    st.stop()

prest_id = int(prest_id)
session = get_session()

try:
    p = session.query(Prestazione).get(prest_id)
    if not p:
        st.error(f"Prestazione #{prest_id} non trovata.")
        st.stop()

    clienti = session.query(Cliente).order_by(Cliente.cognome_ragione_sociale).all()
    conti = session.query(ContoRicavo).order_by(ContoRicavo.codice).all()
    fatturanti = session.query(SoggettoFatturante).order_by(SoggettoFatturante.ragione_sociale).all()

    cl = next((c for c in clienti if c.id == p.cliente_id), None)
    pl = calc_periodicity_label(p.periodicita, p.data_inizio)

    st.markdown(f"""
    <div class="page-header">
    <h2>✏️ Modifica Prestazione #{p.id}</h2>
    <p>{cl.denominazione if cl else '-'} — {p.descrizione}{pl}</p>
    </div>""", unsafe_allow_html=True)

    # Info rapida
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Importo", format_currency(p.importo_unitario))
    m2.metric("Totale (+ IVA)", format_currency(p.totale))
    m3.metric("Incassato", format_currency(p.totale_incassato))
    m4.metric("Residuo", format_currency(p.credito_residuo))

    if p.is_fatturata:
        fa = session.query(st.session_state.get("_fa_model")).get(p.fattura_id) if hasattr(st.session_state, "_fa_model") else None
        st.info(f"📄 Fatturata — Fattura associata: #{p.fattura_id}")

    st.markdown("---")

    # Form modifica
    with st.form("edit_prest"):
        st.markdown("### Modifica dati")
        c1, c2 = st.columns(2)
        with c1:
            e_cl = st.selectbox("Cliente", clienti, format_func=lambda c: c.denominazione,
                index=next((i for i, c in enumerate(clienti) if c.id == p.cliente_id), 0))
            e_cr = st.selectbox("Conto Ricavo", conti,
                format_func=lambda c: f"{c.codice} - {c.descrizione}",
                index=next((i for i, c in enumerate(conti) if c.id == p.conto_ricavo_id), 0))
            e_desc = st.text_input("Descrizione *", value=p.descrizione)
            e_imp = st.number_input("Importo €", value=float(p.importo_unitario), min_value=0.0, step=0.01)
            e_note = st.text_area("Note", value=p.note or "")
        with c2:
            e_ft = st.selectbox("Fatturante", fatturanti, format_func=lambda f: f.ragione_sociale,
                index=next((i for i, f in enumerate(fatturanti) if f.id == p.fatturante_id), 0))
            e_per = st.selectbox("Periodicità", PERIODICITA_OPTIONS,
                index=PERIODICITA_OPTIONS.index(p.periodicita) if p.periodicita in PERIODICITA_OPTIONS else 0)
            e_aliq = st.selectbox("Aliquota IVA %", ALIQUOTA_OPTIONS,
                index=ALIQUOTA_OPTIONS.index(p.aliquota_iva) if p.aliquota_iva in ALIQUOTA_OPTIONS else 4)
            e_mod = st.selectbox("Mod. Incasso", MODALITA_INCASSO_OPTIONS,
                index=MODALITA_INCASSO_OPTIONS.index(p.modalita_incasso) if p.modalita_incasso in MODALITA_INCASSO_OPTIONS else 0)
        d1, d2 = st.columns(2)
        e_di = d1.date_input("Data Inizio", value=p.data_inizio)
        e_df = d2.date_input("Data Fine", value=p.data_fine)

        bc1, bc2 = st.columns(2)
        save = bc1.form_submit_button("💾 Salva modifiche", type="primary")
        # delete inside form doesn't work well, we'll add it outside

        if save and e_desc and e_imp > 0:
            p.cliente_id = e_cl.id; p.conto_ricavo_id = e_cr.id; p.fatturante_id = e_ft.id
            p.descrizione = e_desc; p.importo_unitario = Decimal(str(e_imp))
            p.aliquota_iva = e_aliq; p.periodicita = e_per; p.modalita_incasso = e_mod
            p.data_inizio = e_di; p.data_fine = e_df; p.note = e_note or ""
            session.commit()
            st.success("✅ Prestazione aggiornata!")
            st.rerun()

    # Elimina (fuori dal form)
    st.markdown("---")
    st.markdown("### ⚠️ Zona pericolosa")
    if st.button("🗑️ Elimina questa prestazione", type="secondary"):
        st.session_state["confirm_del_prest"] = True

    if st.session_state.get("confirm_del_prest"):
        st.warning("**Sei sicuro?** Questa azione eliminerà anche tutti gli incassi associati.")
        cd1, cd2 = st.columns(2)
        if cd1.button("✅ Sì, elimina definitivamente", type="primary"):
            session.query(Incasso).filter(Incasso.prestazione_id == p.id).delete()
            session.delete(p)
            session.commit()
            st.success("✅ Eliminata. Puoi chiudere questa scheda.")
            st.session_state.pop("confirm_del_prest", None)
        if cd2.button("❌ Annulla"):
            st.session_state.pop("confirm_del_prest", None)
            st.rerun()

finally:
    session.close()
