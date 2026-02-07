"""🏢 Soggetti Fatturanti — con Logo e configurazione SMTP."""
import streamlit as st
import pandas as pd
from database import get_session, init_db
from models import SoggettoFatturante
from config import REGIME_FISCALE_OPTIONS
from utils.styles import COMMON_CSS
from utils.auth import check_auth, logout_button

st.set_page_config(page_title="Soggetti Fatturanti", page_icon="🏢", layout="wide")
init_db(); st.markdown(COMMON_CSS, unsafe_allow_html=True); check_auth(); logout_button()
st.markdown('<div class="page-header"><h2>🏢 Soggetti Fatturanti</h2></div>', unsafe_allow_html=True)

session = get_session()
try:
    mode = st.radio("", ["📋 Elenco", "➕ Nuovo"], horizontal=True)

    if mode == "➕ Nuovo":
        with st.form("new_sf"):
            st.markdown("#### Dati Anagrafici")
            c1, c2, c3 = st.columns(3)
            with c1:
                rs = st.text_input("Ragione Sociale *"); pi = st.text_input("Partita IVA *")
                cf = st.text_input("Codice Fiscale *"); reg = st.selectbox("Regime", REGIME_FISCALE_OPTIONS)
            with c2:
                ind = st.text_input("Indirizzo"); cap = st.text_input("CAP")
                cit = st.text_input("Città"); pro = st.text_input("Provincia")
            with c3:
                pec = st.text_input("PEC"); sdi = st.text_input("Codice SDI", value="0000000")
                iban = st.text_input("IBAN")

            st.markdown("#### Logo")
            logo_file = st.file_uploader("Carica logo (PNG/JPG)", type=["png", "jpg", "jpeg"])

            st.markdown("#### Configurazione Email (SMTP)")
            sm1, sm2 = st.columns(2)
            smtp_host = sm1.text_input("SMTP Host", placeholder="smtp.gmail.com")
            smtp_port = sm2.number_input("SMTP Port", value=587, min_value=1, max_value=65535)
            sm3, sm4 = st.columns(2)
            smtp_user = sm3.text_input("SMTP User", placeholder="email@example.com")
            smtp_pass = sm4.text_input("SMTP Password", type="password")
            smtp_from = st.text_input("Email mittente", placeholder="noreply@studio.it")

            if st.form_submit_button("💾 Salva", type="primary") and rs and pi:
                if session.query(SoggettoFatturante).filter(SoggettoFatturante.partita_iva == pi).first():
                    st.error(f"P.IVA '{pi}' già presente.")
                else:
                    logo_bytes = logo_file.read() if logo_file else None
                    logo_name = logo_file.name if logo_file else ""
                    session.add(SoggettoFatturante(
                        ragione_sociale=rs, partita_iva=pi, codice_fiscale=cf or "",
                        indirizzo=ind or "", cap=cap or "", citta=cit or "", provincia=pro or "",
                        paese="IT", regime_fiscale=reg, pec=pec or "", codice_sdi=sdi or "0000000",
                        iban=iban or "", logo=logo_bytes, logo_filename=logo_name,
                        smtp_host=smtp_host or "", smtp_port=smtp_port,
                        smtp_user=smtp_user or "", smtp_password=smtp_pass or "",
                        smtp_from=smtp_from or ""))
                    session.commit()
                    st.success(f"✅ '{rs}' creato!"); st.rerun()
    else:
        fl = session.query(SoggettoFatturante).order_by(SoggettoFatturante.ragione_sociale).all()
        if fl:
            df = pd.DataFrame([{
                "Ragione Sociale": f.ragione_sociale, "P.IVA": f.partita_iva,
                "C.F.": f.codice_fiscale, "Città": f"{f.citta} ({f.provincia})" if f.citta else "",
                "PEC": f.pec, "IBAN": f.iban, "Regime": f.regime_fiscale,
                "Logo": "✓" if f.logo else "—", "SMTP": "✓" if f.smtp_host else "—",
            } for f in fl])
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("---")
            sel_id = st.selectbox("✏️ Modifica fatturante", [f.id for f in fl],
                format_func=lambda i: next(f.ragione_sociale for f in fl if f.id == i))
            sf = session.query(SoggettoFatturante).get(sel_id)
            if sf:
                with st.form("edit_sf"):
                    e1, e2 = st.columns(2)
                    with e1:
                        ers = st.text_input("Ragione Sociale", value=sf.ragione_sociale)
                        epi = st.text_input("P.IVA", value=sf.partita_iva)
                        ecf = st.text_input("C.F.", value=sf.codice_fiscale)
                        eiban = st.text_input("IBAN", value=sf.iban or "")
                        epec = st.text_input("PEC", value=sf.pec or "")
                    with e2:
                        eind = st.text_input("Indirizzo", value=sf.indirizzo or "")
                        ecit = st.text_input("Città", value=sf.citta or "")
                        epro = st.text_input("Provincia", value=sf.provincia or "")
                        ereg = st.selectbox("Regime", REGIME_FISCALE_OPTIONS,
                            index=REGIME_FISCALE_OPTIONS.index(sf.regime_fiscale) if sf.regime_fiscale in REGIME_FISCALE_OPTIONS else 0)
                    
                    st.markdown("#### Logo")
                    if sf.logo:
                        st.image(sf.logo, width=150, caption=sf.logo_filename)
                    new_logo = st.file_uploader("Nuovo logo", type=["png","jpg","jpeg"], key="edit_logo")

                    st.markdown("#### SMTP")
                    es1, es2 = st.columns(2)
                    ehost = es1.text_input("Host", value=sf.smtp_host or "")
                    eport = es2.number_input("Port", value=sf.smtp_port or 587)
                    es3, es4 = st.columns(2)
                    euser = es3.text_input("User", value=sf.smtp_user or "")
                    epass = es4.text_input("Password", value=sf.smtp_password or "", type="password")
                    efrom = st.text_input("From", value=sf.smtp_from or "")

                    if st.form_submit_button("💾 Aggiorna", type="primary"):
                        sf.ragione_sociale = ers; sf.partita_iva = epi; sf.codice_fiscale = ecf
                        sf.iban = eiban; sf.pec = epec; sf.indirizzo = eind
                        sf.citta = ecit; sf.provincia = epro; sf.regime_fiscale = ereg
                        sf.smtp_host = ehost; sf.smtp_port = eport
                        sf.smtp_user = euser; sf.smtp_password = epass; sf.smtp_from = efrom
                        if new_logo:
                            sf.logo = new_logo.read(); sf.logo_filename = new_logo.name
                        session.commit(); st.success("✅ Aggiornato!"); st.rerun()
        else:
            st.info("Nessun soggetto fatturante.")
finally:
    session.close()
