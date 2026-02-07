"""💰 Incassi — Registrazione e workflow SDD SEPA."""
import streamlit as st
import pandas as pd
from datetime import date
from decimal import Decimal
from database import get_session, init_db
from models import Incasso, Prestazione
from utils.helpers import format_currency
from config import MODALITA_INCASSO_OPTIONS
from utils.styles import COMMON_CSS
from utils.auth import check_auth, logout_button

st.set_page_config(page_title="Incassi", page_icon="💰", layout="wide")
init_db(); st.markdown(COMMON_CSS, unsafe_allow_html=True); check_auth(); logout_button()
st.markdown('<div class="page-header"><h2>💰 Incassi</h2></div>', unsafe_allow_html=True)

session = get_session()
try:
    f1, f2 = st.columns(2)
    fs = f1.selectbox("Stato", ["Tutti","Caricato da confermare","Confermato","Insoluto"])
    fm = f2.selectbox("Modalità", ["Tutte"] + MODALITA_INCASSO_OPTIONS)

    b1, b2 = st.columns(2)
    if b1.button("✅ Conferma tutti SDD in attesa", type="primary", use_container_width=True):
        u = session.query(Incasso).filter(Incasso.stato == "Caricato da confermare").update(
            {"stato": "Confermato"}, synchronize_session=False)
        session.commit(); st.success(f"✅ {u} confermati!"); st.rerun()
    if b2.button("❌ Segna tutti insoluti", use_container_width=True):
        u = session.query(Incasso).filter(Incasso.stato == "Caricato da confermare").update(
            {"stato": "Insoluto"}, synchronize_session=False)
        session.commit(); st.warning(f"⚠️ {u} insoluti."); st.rerun()

    st.markdown("---")
    q = session.query(Incasso).order_by(Incasso.data.desc())
    if fs != "Tutti": q = q.filter(Incasso.stato == fs)
    if fm != "Tutte": q = q.filter(Incasso.modalita == fm)
    il = q.limit(500).all()

    if il:
        tc = sum(float(i.importo) for i in il if i.stato == "Confermato")
        ta = sum(float(i.importo) for i in il if i.stato == "Caricato da confermare")
        ti = sum(float(i.importo) for i in il if i.stato == "Insoluto")
        m1, m2, m3 = st.columns(3)
        m1.metric("✅ Confermati", format_currency(tc))
        m2.metric("⏳ Da confermare", format_currency(ta))
        m3.metric("❌ Insoluti", format_currency(ti))

        df = pd.DataFrame([{
            "Data": i.data.strftime("%d/%m/%Y") if i.data else "",
            "Cliente": i.prestazione.cliente.denominazione if i.prestazione and i.prestazione.cliente else "-",
            "Prestazione": i.prestazione.descrizione if i.prestazione else "-",
            "Importo": float(i.importo), "Modalità": i.modalita, "Stato": i.stato,
        } for i in il])
        st.dataframe(df, use_container_width=True, hide_index=True,
            column_config={"Importo": st.column_config.NumberColumn(format="€ %.2f")})

        da_conf = [i for i in il if i.stato == "Caricato da confermare"]
        if da_conf:
            st.markdown("#### Gestione singoli SDD")
            for inc in da_conf:
                p = inc.prestazione
                cl = p.cliente if p else None
                ic1, ic2, ic3 = st.columns([5, 1, 1])
                ic1.text(f"{cl.denominazione if cl else '-'} — {p.descrizione if p else ''} — {format_currency(inc.importo)}")
                if ic2.button("✅", key=f"c{inc.id}"): inc.stato = "Confermato"; session.commit(); st.rerun()
                if ic3.button("❌", key=f"i{inc.id}"): inc.stato = "Insoluto"; session.commit(); st.rerun()
    else:
        st.info("Nessun incasso registrato.")

    st.markdown("---")
    st.markdown("#### ➕ Incasso Manuale")
    prest = session.query(Prestazione).order_by(Prestazione.data_inizio.desc()).limit(100).all()
    if prest:
        with st.form("new_inc"):
            ni1, ni2, ni3, ni4 = st.columns(4)
            sp = ni1.selectbox("Prestazione", prest,
                format_func=lambda p: f"{p.cliente.denominazione} — {p.descrizione} ({format_currency(p.credito_residuo)})")
            imp = ni2.number_input("€", min_value=0.01, step=0.01)
            dt = ni3.date_input("Data", value=date.today())
            mod = ni4.selectbox("Modalità", MODALITA_INCASSO_OPTIONS)
            if st.form_submit_button("💾 Registra", type="primary"):
                session.add(Incasso(prestazione_id=sp.id, importo=Decimal(str(imp)),
                    data=dt, stato="Confermato", modalita=mod))
                session.commit(); st.success(f"✅ Registrato!"); st.rerun()
finally:
    session.close()
