"""💰 Incassi — Registrazione e gestione incassi con workflow SDD SEPA."""
import streamlit as st
import pandas as pd
from datetime import date
from decimal import Decimal
from database import get_session, init_db
from models import Incasso, Prestazione, Cliente
from utils.helpers import format_currency
from config import MODALITA_INCASSO_OPTIONS

st.set_page_config(page_title="Incassi", page_icon="💰", layout="wide")
init_db()
st.markdown("## 💰 Incassi")

session = get_session()
try:
    # Filtri
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_stato = st.selectbox("Stato", ["Tutti", "Caricato da confermare", "Confermato", "Insoluto"])
    with fc2:
        f_mod = st.selectbox("Modalità", ["Tutte"] + MODALITA_INCASSO_OPTIONS)
    with fc3:
        f_mese = st.selectbox("Mese", ["Tutti"] + [str(i) for i in range(1, 13)],
            format_func=lambda x: x if x == "Tutti" else
            ["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"][int(x)-1])

    # Azioni massive SDD
    st.markdown("#### Azioni SDD SEPA")
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        if st.button("✅ Conferma Tutti SDD in Attesa", type="primary"):
            updated = session.query(Incasso).filter(
                Incasso.stato == "Caricato da confermare"
            ).update({"stato": "Confermato"}, synchronize_session=False)
            session.commit()
            st.success(f"✅ {updated} incasso/i confermati!")
            st.rerun()
    with bc2:
        if st.button("❌ Segna Tutti Insoluti"):
            updated = session.query(Incasso).filter(
                Incasso.stato == "Caricato da confermare"
            ).update({"stato": "Insoluto"}, synchronize_session=False)
            session.commit()
            st.warning(f"⚠️ {updated} incasso/i segnati come insoluti.")
            st.rerun()

    st.markdown("---")

    # Query
    query = session.query(Incasso).order_by(Incasso.data.desc())
    if f_stato != "Tutti":
        query = query.filter(Incasso.stato == f_stato)
    if f_mod != "Tutte":
        query = query.filter(Incasso.modalita == f_mod)

    incassi_list = query.all()

    if incassi_list:
        # Totali per stato
        tot_conf = sum(float(i.importo) for i in incassi_list if i.stato == "Confermato")
        tot_att = sum(float(i.importo) for i in incassi_list if i.stato == "Caricato da confermare")
        tot_ins = sum(float(i.importo) for i in incassi_list if i.stato == "Insoluto")

        m1, m2, m3 = st.columns(3)
        m1.metric("✅ Confermati", format_currency(tot_conf))
        m2.metric("⏳ Da Confermare", format_currency(tot_att))
        m3.metric("❌ Insoluti", format_currency(tot_ins))

        rows = []
        for i in incassi_list:
            prest = i.prestazione
            cl = prest.cliente if prest else None
            rows.append({
                "ID": i.id,
                "Data": i.data.strftime("%d/%m/%Y") if i.data else "",
                "Cliente": cl.denominazione if cl else "N/D",
                "Prestazione": prest.descrizione if prest else "N/D",
                "Importo": float(i.importo),
                "Modalità": i.modalita,
                "Stato": i.stato,
                "Riferimento": i.riferimento or "",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
            column_config={"Importo": st.column_config.NumberColumn(format="€ %.2f")})

        # Gestione singoli incassi SDD
        da_confermare = [i for i in incassi_list if i.stato == "Caricato da confermare"]
        if da_confermare:
            st.markdown("---")
            st.markdown("#### Gestione Singoli SDD")
            for inc in da_confermare:
                prest = inc.prestazione
                cl = prest.cliente if prest else None
                ic1, ic2, ic3, ic4 = st.columns([3, 1, 1, 1])
                with ic1:
                    st.text(f"{cl.denominazione if cl else 'N/D'} — {prest.descrizione if prest else ''} — {format_currency(inc.importo)}")
                with ic2:
                    if st.button("✅ Conferma", key=f"conf_{inc.id}"):
                        inc.stato = "Confermato"
                        session.commit()
                        st.rerun()
                with ic3:
                    if st.button("❌ Insoluto", key=f"ins_{inc.id}"):
                        inc.stato = "Insoluto"
                        session.commit()
                        st.rerun()
                with ic4:
                    if st.button("🗑️", key=f"del_{inc.id}"):
                        session.delete(inc)
                        session.commit()
                        st.rerun()
    else:
        st.info("Nessun incasso registrato. Usa la Dashboard per caricare SDD SEPA.")

    # Registrazione incasso manuale
    st.markdown("---")
    st.markdown("#### ➕ Registra Incasso Manuale")
    prestazioni = session.query(Prestazione).order_by(Prestazione.data_inizio.desc()).limit(100).all()
    if prestazioni:
        with st.form("new_incasso"):
            ni1, ni2, ni3, ni4 = st.columns(4)
            with ni1:
                sel_prest = st.selectbox("Prestazione", prestazioni,
                    format_func=lambda p: f"{p.cliente.denominazione} — {p.descrizione} ({format_currency(p.credito_residuo)} residuo)")
            with ni2:
                n_importo = st.number_input("Importo €", min_value=0.01, step=0.01)
            with ni3:
                n_data = st.date_input("Data Incasso", value=date.today())
            with ni4:
                n_mod = st.selectbox("Modalità", MODALITA_INCASSO_OPTIONS)
            n_rif = st.text_input("Riferimento (facoltativo)")

            if st.form_submit_button("💾 Registra Incasso", type="primary"):
                new_inc = Incasso(
                    prestazione_id=sel_prest.id,
                    importo=Decimal(str(n_importo)),
                    data=n_data,
                    stato="Confermato",
                    modalita=n_mod,
                    riferimento=n_rif or ""
                )
                session.add(new_inc)
                session.commit()
                st.success(f"✅ Incasso di {format_currency(n_importo)} registrato!")
                st.rerun()
finally:
    session.close()
