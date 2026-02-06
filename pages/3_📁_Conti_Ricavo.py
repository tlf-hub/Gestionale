"""📁 Conti Ricavo — Gestione conti ricavo."""
import streamlit as st
import pandas as pd
from database import get_session, init_db
from models import ContoRicavo

st.set_page_config(page_title="Conti Ricavo", page_icon="📁", layout="wide")
init_db()
st.markdown("## 📁 Conti Ricavo")

session = get_session()
try:
    with st.form("new_conto"):
        st.markdown("#### ➕ Nuovo Conto Ricavo")
        c1, c2 = st.columns(2)
        with c1:
            codice = st.text_input("Codice *")
        with c2:
            descrizione = st.text_input("Descrizione *")
        if st.form_submit_button("💾 Salva", type="primary") and codice and descrizione:
            existing = session.query(ContoRicavo).filter(ContoRicavo.codice == codice).first()
            if existing:
                st.error(f"Codice '{codice}' già presente.")
            else:
                session.add(ContoRicavo(codice=codice, descrizione=descrizione))
                session.commit()
                st.success(f"✅ Conto Ricavo '{codice}' creato!")
                st.rerun()

    st.markdown("---")
    conti = session.query(ContoRicavo).order_by(ContoRicavo.codice).all()
    if conti:
        df = pd.DataFrame([{"ID": c.id, "Codice": c.codice, "Descrizione": c.descrizione} for c in conti])
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("#### ✏️ Modifica / 🗑️ Elimina")
        sel = st.selectbox("Seleziona conto", [c.id for c in conti],
            format_func=lambda cid: next(f"{c.codice} - {c.descrizione}" for c in conti if c.id == cid))
        if sel:
            conto = session.query(ContoRicavo).get(sel)
            ec1, ec2, ec3 = st.columns([2, 2, 1])
            with ec1:
                new_cod = st.text_input("Codice", value=conto.codice, key="ec_cod")
            with ec2:
                new_desc = st.text_input("Descrizione", value=conto.descrizione, key="ec_desc")
            with ec3:
                if st.button("💾 Aggiorna"):
                    conto.codice = new_cod
                    conto.descrizione = new_desc
                    session.commit()
                    st.success("Aggiornato!")
                    st.rerun()
                if st.button("🗑️ Elimina"):
                    try:
                        session.delete(conto)
                        session.commit()
                        st.success("Eliminato!")
                        st.rerun()
                    except Exception:
                        session.rollback()
                        st.error("Impossibile eliminare: ha prestazioni associate.")
    else:
        st.info("Nessun conto ricavo presente.")
finally:
    session.close()
