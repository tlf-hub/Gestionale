"""
👥 Clienti — Anagrafica Clienti completa con tutti i campi richiesti.
"""
import streamlit as st
import pandas as pd
from datetime import date
from database import get_session, init_db
from models import Cliente
from config import TIPO_CLIENTE_OPTIONS, REGIME_FISCALE_OPTIONS, MODALITA_INCASSO_OPTIONS, TITOLO_OPTIONS

st.set_page_config(page_title="Clienti", page_icon="👥", layout="wide")
init_db()

st.markdown("## 👥 Anagrafica Clienti")

session = get_session()
try:
    # =========================================================================
    # FORM NUOVO / MODIFICA CLIENTE
    # =========================================================================
    mode = st.radio("", ["📋 Elenco Clienti", "➕ Nuovo Cliente"], horizontal=True, key="clienti_mode")

    if mode == "➕ Nuovo Cliente":
        with st.form("new_cliente_form"):
            st.markdown("### Dati Anagrafici")
            c1, c2, c3 = st.columns(3)
            with c1:
                titolo = st.selectbox("Titolo", TITOLO_OPTIONS)
                cognome = st.text_input("Cognome / Ragione Sociale *")
                nome = st.text_input("Nome")
            with c2:
                tipo = st.selectbox("Tipo Cliente *", TIPO_CLIENTE_OPTIONS)
                regime = st.selectbox("Regime Fiscale", REGIME_FISCALE_OPTIONS)
                liq_iva = st.text_input("Liquidazione IVA")
            with c3:
                codice_fiscale = st.text_input("Codice Fiscale")
                partita_iva = st.text_input("Partita IVA")
                cassa_prev = st.text_input("Cassa di Previdenza")

            st.markdown("### Indirizzo")
            a1, a2, a3, a4 = st.columns(4)
            with a1:
                indirizzo = st.text_input("Indirizzo")
            with a2:
                cap = st.text_input("CAP")
            with a3:
                citta = st.text_input("Città")
            with a4:
                provincia = st.text_input("Provincia (sigla)")
                paese = st.text_input("Paese", value="IT")

            st.markdown("### Contatti")
            co1, co2, co3, co4 = st.columns(4)
            with co1:
                telefono = st.text_input("Telefono")
            with co2:
                cellulare = st.text_input("Cellulare")
            with co3:
                mail = st.text_input("Email")
            with co4:
                pec = st.text_input("PEC")
                codice_sdi = st.text_input("Codice SDI", value="0000000")

            st.markdown("### Rappresentante Legale")
            r1, r2, r3 = st.columns(3)
            with r1:
                rapp_legale = st.text_input("Nome e Cognome RL")
            with r2:
                carica_rl = st.text_input("Carica RL")
            with r3:
                cf_rl = st.text_input("Codice Fiscale RL")

            st.markdown("### Opzioni Fiscali e Incasso")
            o1, o2, o3, o4 = st.columns(4)
            with o1:
                sostituto = st.checkbox("Sostituto d'Imposta")
            with o2:
                split = st.checkbox("Split Payment")
            with o3:
                mod_incasso = st.selectbox("Modalità Incasso", MODALITA_INCASSO_OPTIONS)
            with o4:
                attivo = st.checkbox("Cliente Attivo", value=True)

            st.markdown("### SDD SEPA")
            s1, s2, s3, s4 = st.columns(4)
            with s1:
                sdd_attivo = st.checkbox("Addebito SDD Attivo")
            with s2:
                iban_sdd = st.text_input("IBAN per SDD")
            with s3:
                data_mandato = st.date_input("Data Mandato SDD", value=None)
            with s4:
                rif_mandato = st.text_input("Rif. Unico Mandato SDD")

            submitted = st.form_submit_button("💾 Salva Cliente", type="primary")
            if submitted and cognome:
                # Controllo doppioni
                dup = False
                if partita_iva:
                    existing = session.query(Cliente).filter(Cliente.partita_iva == partita_iva).first()
                    if existing:
                        st.error(f"⚠️ Partita IVA {partita_iva} già presente: {existing.denominazione}")
                        dup = True
                if codice_fiscale and not dup:
                    existing = session.query(Cliente).filter(Cliente.codice_fiscale == codice_fiscale).first()
                    if existing:
                        st.error(f"⚠️ Codice Fiscale {codice_fiscale} già presente: {existing.denominazione}")
                        dup = True

                if not dup:
                    nuovo = Cliente(
                        cognome_ragione_sociale=cognome, nome=nome or "", titolo=titolo or "",
                        indirizzo=indirizzo or "", cap=cap or "", citta=citta or "",
                        provincia=provincia or "", paese=paese or "IT",
                        tipo_cliente=tipo, regime_fiscale=regime,
                        liquidazione_iva=liq_iva or "",
                        sostituto_imposta=sostituto, split_payment=split,
                        codice_fiscale=codice_fiscale or "", partita_iva=partita_iva or "",
                        cassa_previdenza=cassa_prev or "",
                        rappresentante_legale=rapp_legale or "", carica_rl=carica_rl or "",
                        cf_rl=cf_rl or "",
                        telefono=telefono or "", cellulare=cellulare or "",
                        mail=mail or "", pec=pec or "", codice_sdi=codice_sdi or "0000000",
                        sdd_attivo=sdd_attivo, iban_sdd=iban_sdd or "",
                        data_mandato_sdd=data_mandato, rif_mandato_sdd=rif_mandato or "",
                        modalita_incasso=mod_incasso, cliente_attivo=attivo,
                    )
                    session.add(nuovo)
                    session.commit()
                    st.success(f"✅ Cliente '{cognome}' creato con successo!")
                    st.rerun()

    # =========================================================================
    # ELENCO CLIENTI
    # =========================================================================
    else:
        # Filtro rapido
        f1, f2, f3 = st.columns([3, 2, 2])
        with f1:
            search = st.text_input("🔍 Cerca per nome/ragione sociale", key="search_clienti")
        with f2:
            filter_tipo = st.selectbox("Tipo Cliente", ["Tutti"] + TIPO_CLIENTE_OPTIONS, key="ft_clienti")
        with f3:
            filter_attivo = st.selectbox("Stato", ["Tutti", "Attivi", "Non attivi"], key="fa_clienti")

        query = session.query(Cliente).order_by(Cliente.cognome_ragione_sociale)
        if search:
            query = query.filter(Cliente.cognome_ragione_sociale.ilike(f"%{search}%"))
        if filter_tipo != "Tutti":
            query = query.filter(Cliente.tipo_cliente == filter_tipo)
        if filter_attivo == "Attivi":
            query = query.filter(Cliente.cliente_attivo == True)
        elif filter_attivo == "Non attivi":
            query = query.filter(Cliente.cliente_attivo == False)

        clienti_list = query.all()

        if not clienti_list:
            st.info("Nessun cliente trovato. Usa '➕ Nuovo Cliente' per aggiungerne uno.")
        else:
            st.caption(f"{len(clienti_list)} clienti trovati")

            rows = []
            for c in clienti_list:
                rows.append({
                    "ID": c.id,
                    "Titolo": c.titolo or "",
                    "Cognome/Rag.Sociale": c.cognome_ragione_sociale,
                    "Nome": c.nome or "",
                    "Tipo": c.tipo_cliente,
                    "P.IVA": c.partita_iva or "",
                    "C.F.": c.codice_fiscale or "",
                    "Città": f"{c.citta} ({c.provincia})" if c.citta else "",
                    "PEC": c.pec or "",
                    "SDI": c.codice_sdi or "",
                    "SDD": "✓" if c.sdd_attivo else "",
                    "Incasso": c.modalita_incasso or "",
                    "Attivo": "✓" if c.cliente_attivo else "✗",
                })

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Modifica/Elimina cliente
            st.markdown("---")
            st.markdown("#### ✏️ Modifica / 🗑️ Elimina Cliente")
            sel_id = st.selectbox(
                "Seleziona cliente",
                [c.id for c in clienti_list],
                format_func=lambda cid: next(
                    (c.denominazione for c in clienti_list if c.id == cid), str(cid)
                )
            )

            if sel_id:
                cl = session.query(Cliente).get(sel_id)
                if cl:
                    col_edit, col_del = st.columns([4, 1])
                    with col_del:
                        if st.button("🗑️ Elimina Cliente", type="secondary"):
                            try:
                                session.delete(cl)
                                session.commit()
                                st.success(f"Cliente '{cl.denominazione}' eliminato.")
                                st.rerun()
                            except Exception as e:
                                session.rollback()
                                st.error(f"Impossibile eliminare: il cliente ha prestazioni associate. {e}")

                    with col_edit:
                        with st.form("edit_cliente_form"):
                            ec1, ec2 = st.columns(2)
                            with ec1:
                                e_cognome = st.text_input("Cognome/Rag.Sociale", value=cl.cognome_ragione_sociale)
                                e_nome = st.text_input("Nome", value=cl.nome or "")
                                e_piva = st.text_input("Partita IVA", value=cl.partita_iva or "")
                                e_cf = st.text_input("Codice Fiscale", value=cl.codice_fiscale or "")
                                e_mail = st.text_input("Email", value=cl.mail or "")
                                e_pec = st.text_input("PEC", value=cl.pec or "")
                            with ec2:
                                e_tipo = st.selectbox("Tipo", TIPO_CLIENTE_OPTIONS,
                                    index=TIPO_CLIENTE_OPTIONS.index(cl.tipo_cliente) if cl.tipo_cliente in TIPO_CLIENTE_OPTIONS else 0)
                                e_citta = st.text_input("Città", value=cl.citta or "")
                                e_prov = st.text_input("Provincia", value=cl.provincia or "")
                                e_sdi = st.text_input("Codice SDI", value=cl.codice_sdi or "")
                                e_sdd = st.checkbox("SDD Attivo", value=cl.sdd_attivo)
                                e_iban = st.text_input("IBAN SDD", value=cl.iban_sdd or "")
                                e_attivo = st.checkbox("Cliente Attivo", value=cl.cliente_attivo)

                            if st.form_submit_button("💾 Aggiorna", type="primary"):
                                cl.cognome_ragione_sociale = e_cognome
                                cl.nome = e_nome
                                cl.partita_iva = e_piva
                                cl.codice_fiscale = e_cf
                                cl.mail = e_mail
                                cl.pec = e_pec
                                cl.tipo_cliente = e_tipo
                                cl.citta = e_citta
                                cl.provincia = e_prov
                                cl.codice_sdi = e_sdi
                                cl.sdd_attivo = e_sdd
                                cl.iban_sdd = e_iban
                                cl.cliente_attivo = e_attivo
                                session.commit()
                                st.success("✅ Cliente aggiornato!")
                                st.rerun()
finally:
    session.close()
