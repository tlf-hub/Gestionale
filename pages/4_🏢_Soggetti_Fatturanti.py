"""🏢 Soggetti Fatturanti — Gestione soggetti che emettono fatture."""
import streamlit as st
import pandas as pd
from database import get_session, init_db
from models import SoggettoFatturante
from config import REGIME_FISCALE_OPTIONS

st.set_page_config(page_title="Soggetti Fatturanti", page_icon="🏢", layout="wide")
init_db()
st.markdown("## 🏢 Soggetti Fatturanti")

session = get_session()
try:
    with st.form("new_fatturante"):
        st.markdown("#### ➕ Nuovo Soggetto Fatturante")
        c1, c2, c3 = st.columns(3)
        with c1:
            rag_soc = st.text_input("Ragione Sociale *")
            piva = st.text_input("Partita IVA *")
            cf = st.text_input("Codice Fiscale *")
            regime = st.selectbox("Regime Fiscale", REGIME_FISCALE_OPTIONS)
        with c2:
            indirizzo = st.text_input("Indirizzo")
            cap = st.text_input("CAP")
            citta = st.text_input("Città")
            provincia = st.text_input("Provincia")
        with c3:
            pec = st.text_input("PEC")
            sdi = st.text_input("Codice SDI", value="0000000")
            iban = st.text_input("IBAN")
            paese = st.text_input("Paese", value="IT")

        if st.form_submit_button("💾 Salva", type="primary") and rag_soc and piva:
            existing = session.query(SoggettoFatturante).filter(SoggettoFatturante.partita_iva == piva).first()
            if existing:
                st.error(f"P.IVA '{piva}' già presente.")
            else:
                session.add(SoggettoFatturante(
                    ragione_sociale=rag_soc, partita_iva=piva, codice_fiscale=cf or "",
                    indirizzo=indirizzo or "", cap=cap or "", citta=citta or "",
                    provincia=provincia or "", paese=paese or "IT",
                    regime_fiscale=regime, pec=pec or "", codice_sdi=sdi or "0000000",
                    iban=iban or ""
                ))
                session.commit()
                st.success(f"✅ '{rag_soc}' creato!")
                st.rerun()

    st.markdown("---")
    fatt_list = session.query(SoggettoFatturante).order_by(SoggettoFatturante.ragione_sociale).all()
    if fatt_list:
        df = pd.DataFrame([{
            "ID": f.id, "Ragione Sociale": f.ragione_sociale, "P.IVA": f.partita_iva,
            "C.F.": f.codice_fiscale, "Città": f"{f.citta} ({f.provincia})",
            "PEC": f.pec, "SDI": f.codice_sdi, "Regime": f.regime_fiscale, "IBAN": f.iban,
        } for f in fatt_list])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun soggetto fatturante presente.")
finally:
    session.close()
