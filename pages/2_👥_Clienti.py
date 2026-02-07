"""👥 Clienti — Anagrafica completa."""
import streamlit as st
import pandas as pd
from database import get_session, init_db
from models import Cliente
from config import TIPO_CLIENTE_OPTIONS, REGIME_FISCALE_OPTIONS, MODALITA_INCASSO_OPTIONS, TITOLO_OPTIONS
from utils.styles import COMMON_CSS
from utils.auth import check_auth, logout_button

st.set_page_config(page_title="Clienti", page_icon="👥", layout="wide")
init_db(); st.markdown(COMMON_CSS, unsafe_allow_html=True)
check_auth(); logout_button()
st.markdown('<div class="page-header"><h2>👥 Anagrafica Clienti</h2></div>', unsafe_allow_html=True)

session = get_session()
try:
    mode = st.radio("", ["📋 Elenco", "➕ Nuovo Cliente"], horizontal=True)

    if mode == "➕ Nuovo Cliente":
        with st.form("new_cl"):
            st.markdown("#### Dati Anagrafici")
            c1, c2, c3 = st.columns(3)
            with c1:
                titolo = st.selectbox("Titolo", TITOLO_OPTIONS)
                cognome = st.text_input("Cognome / Ragione Sociale *")
                nome = st.text_input("Nome")
            with c2:
                tipo = st.selectbox("Tipo Cliente *", TIPO_CLIENTE_OPTIONS)
                regime = st.selectbox("Regime Fiscale", REGIME_FISCALE_OPTIONS)
                liq = st.text_input("Liquidazione IVA")
            with c3:
                cf = st.text_input("Codice Fiscale")
                piva = st.text_input("Partita IVA")
                cassa = st.text_input("Cassa Previdenza")

            st.markdown("#### Indirizzo")
            a1, a2, a3, a4 = st.columns(4)
            ind = a1.text_input("Indirizzo"); cap = a2.text_input("CAP")
            citta = a3.text_input("Città"); prov = a4.text_input("Provincia")

            st.markdown("#### Contatti")
            co1, co2, co3, co4 = st.columns(4)
            tel = co1.text_input("Telefono"); cell = co2.text_input("Cellulare")
            mail = co3.text_input("Email"); pec = co4.text_input("PEC")
            sdi = st.text_input("Codice SDI", value="0000000")

            st.markdown("#### Rappresentante Legale")
            r1, r2, r3 = st.columns(3)
            rl = r1.text_input("Nome e Cognome RL"); car = r2.text_input("Carica RL"); cfrl = r3.text_input("CF RL")

            st.markdown("#### Opzioni")
            o1, o2, o3, o4 = st.columns(4)
            sost = o1.checkbox("Sostituto d'Imposta"); split = o2.checkbox("Split Payment")
            mod = o3.selectbox("Mod. Incasso", MODALITA_INCASSO_OPTIONS)
            att = o4.checkbox("Attivo", value=True)

            st.markdown("#### SDD SEPA")
            s1, s2, s3, s4 = st.columns(4)
            sdd = s1.checkbox("SDD Attivo"); iban = s2.text_input("IBAN SDD")
            dmand = s3.date_input("Data Mandato", value=None); rmand = s4.text_input("Rif. Mandato")

            if st.form_submit_button("💾 Salva", type="primary") and cognome:
                dup = False
                if piva and session.query(Cliente).filter(Cliente.partita_iva == piva).first():
                    st.error(f"P.IVA {piva} già presente!"); dup = True
                if cf and not dup and session.query(Cliente).filter(Cliente.codice_fiscale == cf).first():
                    st.error(f"C.F. {cf} già presente!"); dup = True
                if not dup:
                    session.add(Cliente(
                        cognome_ragione_sociale=cognome, nome=nome or "", titolo=titolo or "",
                        indirizzo=ind or "", cap=cap or "", citta=citta or "", provincia=prov or "",
                        paese="IT", tipo_cliente=tipo, regime_fiscale=regime,
                        liquidazione_iva=liq or "", sostituto_imposta=sost, split_payment=split,
                        codice_fiscale=cf or "", partita_iva=piva or "", cassa_previdenza=cassa or "",
                        rappresentante_legale=rl or "", carica_rl=car or "", cf_rl=cfrl or "",
                        telefono=tel or "", cellulare=cell or "", mail=mail or "",
                        pec=pec or "", codice_sdi=sdi or "0000000",
                        sdd_attivo=sdd, iban_sdd=iban or "", data_mandato_sdd=dmand,
                        rif_mandato_sdd=rmand or "", modalita_incasso=mod, cliente_attivo=att))
                    session.commit()
                    st.success(f"✅ '{cognome}' creato!"); st.rerun()
    else:
        f1, f2, f3 = st.columns([3, 2, 2])
        search = f1.text_input("🔍 Cerca")
        ft = f2.selectbox("Tipo", ["Tutti"] + TIPO_CLIENTE_OPTIONS)
        fa = f3.selectbox("Stato", ["Tutti", "Attivi", "Non attivi"])

        q = session.query(Cliente).order_by(Cliente.cognome_ragione_sociale)
        if search: q = q.filter(Cliente.cognome_ragione_sociale.ilike(f"%{search}%"))
        if ft != "Tutti": q = q.filter(Cliente.tipo_cliente == ft)
        if fa == "Attivi": q = q.filter(Cliente.cliente_attivo == True)
        elif fa == "Non attivi": q = q.filter(Cliente.cliente_attivo == False)

        cls = q.all()
        if cls:
            st.caption(f"{len(cls)} clienti")
            df = pd.DataFrame([{
                "Cognome/R.S.": c.cognome_ragione_sociale, "Nome": c.nome or "",
                "Tipo": c.tipo_cliente, "P.IVA": c.partita_iva or "",
                "C.F.": c.codice_fiscale or "", "Città": f"{c.citta} ({c.provincia})" if c.citta else "",
                "PEC": c.pec or "", "SDI": c.codice_sdi or "",
                "SDD": "✓" if c.sdd_attivo else "", "Attivo": "✓" if c.cliente_attivo else "✗",
            } for c in cls])
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("---")
            sel_id = st.selectbox("✏️ Modifica cliente", [c.id for c in cls],
                format_func=lambda i: next(c.denominazione for c in cls if c.id == i))
            cl = session.query(Cliente).get(sel_id)
            if cl:
                ec1, ec2 = st.columns([5, 1])
                with ec2:
                    if st.button("🗑️ Elimina"):
                        try:
                            session.delete(cl); session.commit(); st.success("Eliminato!"); st.rerun()
                        except Exception as e:
                            session.rollback(); st.error(f"Ha prestazioni associate: {e}")
                with ec1:
                    with st.form("edit_cl"):
                        e1, e2 = st.columns(2)
                        with e1:
                            ec = st.text_input("Cognome/R.S.", value=cl.cognome_ragione_sociale)
                            en = st.text_input("Nome", value=cl.nome or "")
                            ep = st.text_input("P.IVA", value=cl.partita_iva or "")
                            ecf = st.text_input("C.F.", value=cl.codice_fiscale or "")
                            em = st.text_input("PEC", value=cl.pec or "")
                        with e2:
                            et = st.selectbox("Tipo", TIPO_CLIENTE_OPTIONS,
                                index=TIPO_CLIENTE_OPTIONS.index(cl.tipo_cliente) if cl.tipo_cliente in TIPO_CLIENTE_OPTIONS else 0)
                            eci = st.text_input("Città", value=cl.citta or "")
                            esd = st.text_input("SDI", value=cl.codice_sdi or "")
                            esdd = st.checkbox("SDD", value=cl.sdd_attivo)
                            eib = st.text_input("IBAN SDD", value=cl.iban_sdd or "")
                            eatt = st.checkbox("Attivo", value=cl.cliente_attivo)
                        if st.form_submit_button("💾 Aggiorna", type="primary"):
                            cl.cognome_ragione_sociale = ec; cl.nome = en
                            cl.partita_iva = ep; cl.codice_fiscale = ecf; cl.pec = em
                            cl.tipo_cliente = et; cl.citta = eci; cl.codice_sdi = esd
                            cl.sdd_attivo = esdd; cl.iban_sdd = eib; cl.cliente_attivo = eatt
                            session.commit(); st.success("✅ Aggiornato!"); st.rerun()
        else:
            st.info("Nessun cliente trovato.")
finally:
    session.close()
