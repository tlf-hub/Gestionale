"""💰 Incassi Prestazione — Gestione incassi per una singola prestazione."""
import streamlit as st
import pandas as pd
from datetime import date
from decimal import Decimal
from database import get_session, init_db
from models import Prestazione, Incasso
from config import MODALITA_INCASSO_OPTIONS
from utils.helpers import format_currency, calc_periodicity_label
from utils.styles import COMMON_CSS
from utils.auth import check_auth, logout_button

st.set_page_config(page_title="Incassi Prestazione", page_icon="💰", layout="wide")
init_db(); st.markdown(COMMON_CSS, unsafe_allow_html=True); check_auth(); logout_button()

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

    cl = p.cliente
    pl = calc_periodicity_label(p.periodicita, p.data_inizio)

    st.markdown(f"""
    <div class="page-header">
    <h2>💰 Incassi — Prestazione #{p.id}</h2>
    <p>{cl.denominazione if cl else '-'} — {p.descrizione}{pl}</p>
    </div>""", unsafe_allow_html=True)

    # Metriche
    m1, m2, m3 = st.columns(3)
    m1.metric("Totale prestazione", format_currency(p.totale))
    m2.metric("Incassato", format_currency(p.totale_incassato))
    m3.metric("Residuo", format_currency(p.credito_residuo))

    st.markdown("---")

    # Elenco incassi esistenti
    incassi = session.query(Incasso).filter(Incasso.prestazione_id == p.id).order_by(Incasso.data.desc()).all()

    if incassi:
        st.markdown("### Incassi registrati")
        for inc in incassi:
            with st.expander(
                f"{'✅' if inc.stato == 'Confermato' else '⏳' if inc.stato == 'Caricato da confermare' else '❌'} "
                f"{inc.data.strftime('%d/%m/%Y')} — {format_currency(inc.importo)} — {inc.modalita} — {inc.stato}",
                expanded=False
            ):
                with st.form(f"edit_inc_{inc.id}"):
                    ei1, ei2, ei3, ei4 = st.columns(4)
                    e_imp = ei1.number_input("Importo €", value=float(inc.importo), step=0.01, key=f"ei_{inc.id}")
                    e_data = ei2.date_input("Data", value=inc.data, key=f"ed_{inc.id}")
                    e_mod = ei3.selectbox("Modalità", MODALITA_INCASSO_OPTIONS,
                        index=MODALITA_INCASSO_OPTIONS.index(inc.modalita) if inc.modalita in MODALITA_INCASSO_OPTIONS else 0,
                        key=f"em_{inc.id}")
                    e_stato = ei4.selectbox("Stato", ["Confermato", "Caricato da confermare", "Insoluto"],
                        index=["Confermato", "Caricato da confermare", "Insoluto"].index(inc.stato) if inc.stato in ["Confermato", "Caricato da confermare", "Insoluto"] else 0,
                        key=f"es_{inc.id}")
                    e_rif = st.text_input("Riferimento", value=inc.riferimento or "", key=f"er_{inc.id}")
                    e_note = st.text_input("Note", value=inc.note or "", key=f"en_{inc.id}")

                    fc1, fc2 = st.columns(2)
                    if fc1.form_submit_button("💾 Aggiorna", type="primary"):
                        inc.importo = Decimal(str(e_imp)); inc.data = e_data
                        inc.modalita = e_mod; inc.stato = e_stato
                        inc.riferimento = e_rif; inc.note = e_note
                        session.commit()
                        st.success("✅ Aggiornato!"); st.rerun()

                # Elimina fuori dal form
                if st.button(f"🗑️ Elimina incasso #{inc.id}", key=f"del_{inc.id}"):
                    session.delete(inc); session.commit()
                    st.success("Eliminato!"); st.rerun()
    else:
        st.info("Nessun incasso registrato per questa prestazione.")

    # Nuovo incasso
    st.markdown("---")
    st.markdown("### ➕ Nuovo incasso")
    with st.form("new_inc"):
        ni1, ni2, ni3 = st.columns(3)
        n_imp = ni1.number_input("Importo €", value=float(p.credito_residuo) if p.credito_residuo > 0 else 0.0,
                                  min_value=0.01, step=0.01)
        n_data = ni2.date_input("Data", value=date.today())
        n_mod = ni3.selectbox("Modalità", MODALITA_INCASSO_OPTIONS)
        n_stato = st.selectbox("Stato", ["Confermato", "Caricato da confermare"])
        n_rif = st.text_input("Riferimento")
        n_note = st.text_input("Note")

        if st.form_submit_button("💾 Registra incasso", type="primary", use_container_width=True):
            session.add(Incasso(
                prestazione_id=p.id, importo=Decimal(str(n_imp)),
                data=n_data, stato=n_stato, modalita=n_mod,
                riferimento=n_rif or "", note=n_note or ""))
            session.commit()
            st.success(f"✅ Incasso di {format_currency(n_imp)} registrato!")
            st.rerun()

finally:
    session.close()
