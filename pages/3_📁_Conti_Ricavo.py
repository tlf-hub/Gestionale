"""📁 Conti Ricavo"""
import streamlit as st
import pandas as pd
from database import get_session, init_db
from models import ContoRicavo
from utils.styles import COMMON_CSS
from utils.auth import check_auth, logout_button

st.set_page_config(page_title="Conti Ricavo", page_icon="📁", layout="wide")
init_db(); st.markdown(COMMON_CSS, unsafe_allow_html=True); check_auth(); logout_button()
st.markdown('<div class="page-header"><h2>📁 Conti Ricavo</h2></div>', unsafe_allow_html=True)

session = get_session()
try:
    with st.form("new_cr"):
        c1, c2, c3 = st.columns([2, 4, 2])
        cod = c1.text_input("Codice *"); desc = c2.text_input("Descrizione *")
        sub = c3.form_submit_button("💾 Aggiungi", type="primary")
        if sub and cod and desc:
            if session.query(ContoRicavo).filter(ContoRicavo.codice == cod).first():
                st.error(f"Codice '{cod}' già presente.")
            else:
                session.add(ContoRicavo(codice=cod, descrizione=desc)); session.commit()
                st.success(f"✅ '{cod}' creato!"); st.rerun()

    conti = session.query(ContoRicavo).order_by(ContoRicavo.codice).all()
    if conti:
        df = pd.DataFrame([{"Codice": c.codice, "Descrizione": c.descrizione} for c in conti])
        st.dataframe(df, use_container_width=True, hide_index=True)
        sel = st.selectbox("Seleziona", [c.id for c in conti],
            format_func=lambda i: next(f"{c.codice} - {c.descrizione}" for c in conti if c.id == i))
        co = session.query(ContoRicavo).get(sel)
        e1, e2, e3, e4 = st.columns([2, 4, 1, 1])
        nc = e1.text_input("Codice", value=co.codice, key="ec")
        nd = e2.text_input("Descrizione", value=co.descrizione, key="ed")
        if e3.button("💾"): co.codice = nc; co.descrizione = nd; session.commit(); st.rerun()
        if e4.button("🗑️"):
            try: session.delete(co); session.commit(); st.rerun()
            except: session.rollback(); st.error("Ha prestazioni associate.")
    else:
        st.info("Nessun conto ricavo.")
finally:
    session.close()
