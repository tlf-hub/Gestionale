"""
📊 Dashboard — Gestione Prestazioni
Pagina principale del gestionale con filtri, azioni e tabella prestazioni.
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime
from decimal import Decimal
from database import get_session, init_db
from models import Prestazione, Cliente, ContoRicavo, SoggettoFatturante, Fattura, Incasso
from config import (MESI, MESI_SHORT, PERIODICITA_OPTIONS, MODALITA_INCASSO_OPTIONS,
                    ALIQUOTA_OPTIONS, STATO_SDD_OPTIONS)
from utils.helpers import format_currency, calc_periodicity_label, add_period, get_next_fattura_number
from utils.fattura_xml import genera_fattura_xml, genera_zip_fatture
from utils.sdd_sepa_xml import genera_sdd_xml
from sqlalchemy import func, extract
from itertools import groupby
from operator import attrgetter

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
init_db()

# =============================================================================
# SESSION STATE DEFAULTS
# =============================================================================
if "sel_month" not in st.session_state:
    st.session_state.sel_month = date.today().month - 1  # 0-based
if "sel_year" not in st.session_state:
    st.session_state.sel_year = date.today().year
if "selected_ids" not in st.session_state:
    st.session_state.selected_ids = set()


def load_lookups(session):
    """Carica le tabelle di lookup."""
    clienti = {c.id: c for c in session.query(Cliente).order_by(Cliente.cognome_ragione_sociale).all()}
    conti = {c.id: c for c in session.query(ContoRicavo).order_by(ContoRicavo.codice).all()}
    fatturanti = {f.id: f for f in session.query(SoggettoFatturante).order_by(SoggettoFatturante.ragione_sociale).all()}
    fatture = {f.id: f for f in session.query(Fattura).all()}
    return clienti, conti, fatturanti, fatture


# =============================================================================
# HEADER
# =============================================================================
st.markdown("## 📊 Dashboard Prestazioni")

session = get_session()
try:
    clienti, conti, fatturanti, fatture_map = load_lookups(session)

    if not clienti:
        st.warning("⚠️ Nessun cliente trovato. Vai alla pagina **Clienti** per aggiungerne.")
        st.stop()
    if not conti:
        st.warning("⚠️ Nessun Conto Ricavo trovato. Vai alla pagina **Conti Ricavo** per aggiungerne.")
        st.stop()
    if not fatturanti:
        st.warning("⚠️ Nessun Soggetto Fatturante trovato. Vai alla relativa pagina per aggiungerne.")
        st.stop()

    # =========================================================================
    # RIGA 1: PULSANTI AZIONE
    # =========================================================================
    with st.container():
        st.markdown("#### Azioni")
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
        with c1:
            btn_new = st.button("➕ Nuova Prestazione", use_container_width=True)
        with c2:
            btn_delete = st.button("🗑️ Elimina Sel.", use_container_width=True)
        with c3:
            btn_dup = st.button("📋 Duplica Sel.", use_container_width=True)
        with c4:
            btn_dup_m = st.button("📋 +1 Mese", use_container_width=True)
        with c5:
            btn_dup_t = st.button("📋 +1 Trim.", use_container_width=True)
        with c6:
            btn_dup_s = st.button("📋 +1 Sem.", use_container_width=True)
        with c7:
            btn_dup_a = st.button("📋 +1 Anno", use_container_width=True)
        with c8:
            btn_emetti = st.button("📄 Emetti Fatture", type="primary", use_container_width=True)

        c9, c10, c11, _ = st.columns([1,1,1,5])
        with c9:
            btn_xml = st.button("📋 Genera XML FatturaPA", use_container_width=True)
        with c10:
            btn_sdd = st.button("🏦 Carica SDD SEPA", use_container_width=True)
        with c11:
            btn_conf_sdd = st.button("✅ Conferma SDD", use_container_width=True)

    st.markdown("---")

    # =========================================================================
    # RIGA 2: SELEZIONE MESE/ANNO
    # =========================================================================
    with st.container():
        cols_months = st.columns(14)
        for i in range(12):
            with cols_months[i]:
                is_sel = st.session_state.sel_month == i
                if st.button(
                    MESI_SHORT[i],
                    key=f"month_{i}",
                    use_container_width=True,
                    type="primary" if is_sel else "secondary"
                ):
                    st.session_state.sel_month = i
                    st.rerun()
        with cols_months[12]:
            if st.button("◀", use_container_width=True):
                st.session_state.sel_year -= 1
                st.rerun()
        with cols_months[13]:
            if st.button("▶", use_container_width=True):
                st.session_state.sel_year += 1
                st.rerun()

        st.markdown(
            f"<div style='text-align:center;background:#1e293b;color:#38bdf8;"
            f"padding:8px;border-radius:8px;font-size:1.4em;font-weight:bold;'>"
            f"{MESI[st.session_state.sel_month]} {st.session_state.sel_year}</div>",
            unsafe_allow_html=True
        )

    # =========================================================================
    # RIGA 3: FILTRI
    # =========================================================================
    st.markdown("#### 🔍 Filtri")
    fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
    with fc1:
        f_cliente = st.selectbox("Cliente", ["Tutti"] + [c.denominazione for c in clienti.values()], key="f_cliente")
    with fc2:
        f_conto = st.selectbox("Conto Ricavo", ["Tutti"] + [f"{c.codice} - {c.descrizione}" for c in conti.values()], key="f_conto")
    with fc3:
        f_fatt = st.selectbox("Sogg. Fatturante", ["Tutti"] + [f.ragione_sociale for f in fatturanti.values()], key="f_fatt")
    with fc4:
        f_credito = st.selectbox("Credito / Fatt.", ["Tutti","Con credito residuo","Senza credito","Già fatturato","Non fatturato"], key="f_credito")
    with fc5:
        f_sdd = st.selectbox("Stato SDD", ["Tutti"] + STATO_SDD_OPTIONS, key="f_sdd")
    with fc6:
        f_period = st.selectbox("Periodicità", ["Tutte"] + PERIODICITA_OPTIONS, key="f_period")

    # =========================================================================
    # RIGA 4: RAGGRUPPAMENTO
    # =========================================================================
    fc7, fc8 = st.columns([3, 9])
    with fc7:
        raggruppamento = st.radio(
            "Raggruppa per:",
            ["Nessuno", "Cliente", "Conto Ricavo", "Sogg. Fatturante", "Fattura"],
            horizontal=True,
            index=2
        )

    # =========================================================================
    # QUERY PRESTAZIONI
    # =========================================================================
    sel_m = st.session_state.sel_month + 1  # 1-based for SQL
    sel_y = st.session_state.sel_year

    query = session.query(Prestazione).filter(
        extract("month", Prestazione.data_inizio) == sel_m,
        extract("year", Prestazione.data_inizio) == sel_y
    )

    # Applica filtri
    if f_cliente != "Tutti":
        cid = next((c.id for c in clienti.values() if c.denominazione == f_cliente), None)
        if cid:
            query = query.filter(Prestazione.cliente_id == cid)
    if f_conto != "Tutti":
        codice = f_conto.split(" - ")[0]
        crid = next((c.id for c in conti.values() if c.codice == codice), None)
        if crid:
            query = query.filter(Prestazione.conto_ricavo_id == crid)
    if f_fatt != "Tutti":
        fid = next((f.id for f in fatturanti.values() if f.ragione_sociale == f_fatt), None)
        if fid:
            query = query.filter(Prestazione.fatturante_id == fid)
    if f_period != "Tutte":
        query = query.filter(Prestazione.periodicita == f_period)
    if f_credito == "Già fatturato":
        query = query.filter(Prestazione.fattura_id.isnot(None))
    elif f_credito == "Non fatturato":
        query = query.filter(Prestazione.fattura_id.is_(None))

    prestazioni = query.order_by(Prestazione.data_inizio, Prestazione.cliente_id).all()

    # =========================================================================
    # SUMMARY CARDS
    # =========================================================================
    tot_totale = sum(p.totale for p in prestazioni)
    tot_incassato = sum(p.totale_incassato for p in prestazioni)
    tot_residuo = tot_totale - tot_incassato
    tot_fatturato = sum(p.totale for p in prestazioni if p.is_fatturata)
    tot_non_fatturato = sum(p.totale for p in prestazioni if not p.is_fatturata)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📊 Totale Prestazioni", format_currency(tot_totale), f"{len(prestazioni)} record")
    m2.metric("📄 Fatturato", format_currency(tot_fatturato))
    m3.metric("⏳ Non Fatturato", format_currency(tot_non_fatturato))
    m4.metric("✅ Incassato", format_currency(tot_incassato))
    m5.metric("🔴 Credito Residuo", format_currency(tot_residuo))

    st.markdown("---")

    # =========================================================================
    # TABELLA PRESTAZIONI
    # =========================================================================
    if not prestazioni:
        st.info(f"Nessuna prestazione trovata per {MESI[st.session_state.sel_month]} {sel_y}")
    else:
        # Costruisci DataFrame per visualizzazione
        rows = []
        for p in prestazioni:
            cl = clienti.get(p.cliente_id)
            cr = conti.get(p.conto_ricavo_id)
            ft = fatturanti.get(p.fatturante_id)
            fa = fatture_map.get(p.fattura_id)
            period_label = calc_periodicity_label(p.periodicita, p.data_inizio)
            last_inc = max((i.data for i in p.incassi), default=None)
            rows.append({
                "sel": p.id in st.session_state.selected_ids,
                "id": p.id,
                "Esigibilità": f"{p.data_inizio.strftime('%d/%m/%Y')} → {p.data_fine.strftime('%d/%m/%Y')}",
                "Cliente": cl.denominazione if cl else "N/D",
                "Mod. Incasso": p.modalita_incasso,
                "Conto Ricavo": f"{cr.codice} {cr.descrizione}" if cr else "N/D",
                "Descrizione": p.descrizione + period_label,
                "Importo": float(p.importo_unitario),
                "IVA %": p.aliquota_iva,
                "Totale": p.totale,
                "Ult. Incasso": last_inc.strftime("%d/%m/%Y") if last_inc else "-",
                "Incassato": p.totale_incassato,
                "Residuo": p.credito_residuo,
                "Fatturante": ft.ragione_sociale if ft else "N/D",
                "Fattura": f"{fa.numero}/{fa.anno}" if fa else "-",
                "Period.": p.periodicita,
                "Gruppo_Cliente": cl.denominazione if cl else "N/D",
                "Gruppo_Conto": f"{cr.codice} {cr.descrizione}" if cr else "N/D",
                "Gruppo_Fatturante": ft.ragione_sociale if ft else "N/D",
                "Gruppo_Fattura": f"Fatt. {fa.numero}/{fa.anno}" if fa else "Non fatturate",
            })

        df = pd.DataFrame(rows)

        # Raggruppamento
        group_col_map = {
            "Cliente": "Gruppo_Cliente",
            "Conto Ricavo": "Gruppo_Conto",
            "Sogg. Fatturante": "Gruppo_Fatturante",
            "Fattura": "Gruppo_Fattura",
        }

        display_cols = ["Esigibilità","Cliente","Mod. Incasso","Conto Ricavo","Descrizione",
                        "Importo","IVA %","Totale","Ult. Incasso","Incassato","Residuo",
                        "Fatturante","Fattura","Period."]

        if raggruppamento != "Nessuno" and raggruppamento in group_col_map:
            gcol = group_col_map[raggruppamento]
            for group_name, group_df in df.groupby(gcol, sort=True):
                tot_grp = group_df["Totale"].sum()
                st.markdown(
                    f"**{group_name}** — {len(group_df)} record — "
                    f"Totale: {format_currency(tot_grp)}"
                )
                st.dataframe(
                    group_df[display_cols],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Importo": st.column_config.NumberColumn(format="€ %.2f"),
                        "Totale": st.column_config.NumberColumn(format="€ %.2f"),
                        "Incassato": st.column_config.NumberColumn(format="€ %.2f"),
                        "Residuo": st.column_config.NumberColumn(format="€ %.2f"),
                    }
                )
        else:
            st.dataframe(
                df[display_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Importo": st.column_config.NumberColumn(format="€ %.2f"),
                    "Totale": st.column_config.NumberColumn(format="€ %.2f"),
                    "Incassato": st.column_config.NumberColumn(format="€ %.2f"),
                    "Residuo": st.column_config.NumberColumn(format="€ %.2f"),
                }
            )

        # Selezione record con checkboxes
        st.markdown("#### Seleziona Prestazioni")
        all_ids = [p.id for p in prestazioni]
        select_all = st.checkbox("Seleziona tutte", key="select_all_prest")
        if select_all:
            st.session_state.selected_ids = set(all_ids)
        else:
            selected = st.multiselect(
                "Seleziona le prestazioni per le azioni:",
                options=all_ids,
                default=list(st.session_state.selected_ids & set(all_ids)),
                format_func=lambda pid: next(
                    (f"{r['Cliente']} — {r['Descrizione']} — {format_currency(r['Totale'])}"
                     for r in rows if r['id'] == pid), str(pid)
                )
            )
            st.session_state.selected_ids = set(selected)

        n_sel = len(st.session_state.selected_ids)
        if n_sel > 0:
            st.info(f"✅ {n_sel} prestazione/i selezionate")

    # =========================================================================
    # GESTIONE AZIONI
    # =========================================================================

    # --- NUOVA PRESTAZIONE ---
    if btn_new:
        st.session_state.show_new_form = True

    if st.session_state.get("show_new_form"):
        with st.form("new_prestazione_form"):
            st.markdown("### ➕ Nuova Prestazione")
            nc1, nc2 = st.columns(2)
            with nc1:
                n_cliente = st.selectbox("Cliente *", list(clienti.values()), format_func=lambda c: c.denominazione, key="np_cliente")
                n_conto = st.selectbox("Conto Ricavo *", list(conti.values()), format_func=lambda c: f"{c.codice} - {c.descrizione}", key="np_conto")
                n_desc = st.text_input("Descrizione *", key="np_desc")
                n_importo = st.number_input("Importo Unitario €", min_value=0.0, step=0.01, key="np_importo")
            with nc2:
                n_fatt = st.selectbox("Sogg. Fatturante *", list(fatturanti.values()), format_func=lambda f: f.ragione_sociale, key="np_fatt")
                n_period = st.selectbox("Periodicità", PERIODICITA_OPTIONS, key="np_period")
                n_aliq = st.selectbox("Aliquota IVA %", ALIQUOTA_OPTIONS, index=4, key="np_aliq")
                n_mod = st.selectbox("Mod. Incasso", MODALITA_INCASSO_OPTIONS, key="np_mod")
            nc3, nc4 = st.columns(2)
            with nc3:
                n_data_ini = st.date_input("Data Inizio", value=date(sel_y, sel_m, 1), key="np_di")
            with nc4:
                import calendar
                last_day = calendar.monthrange(sel_y, sel_m)[1]
                n_data_fin = st.date_input("Data Fine", value=date(sel_y, sel_m, last_day), key="np_df")
            n_note = st.text_area("Note", key="np_note")

            submitted = st.form_submit_button("💾 Salva Prestazione", type="primary")
            if submitted and n_desc and n_importo > 0:
                new_p = Prestazione(
                    cliente_id=n_cliente.id,
                    conto_ricavo_id=n_conto.id,
                    fatturante_id=n_fatt.id,
                    periodicita=n_period,
                    descrizione=n_desc,
                    importo_unitario=Decimal(str(n_importo)),
                    aliquota_iva=n_aliq,
                    data_inizio=n_data_ini,
                    data_fine=n_data_fin,
                    modalita_incasso=n_mod,
                    note=n_note or "",
                )
                session.add(new_p)
                session.commit()
                st.session_state.show_new_form = False
                st.success("✅ Prestazione creata!")
                st.rerun()

    # --- ELIMINA SELEZIONATE ---
    if btn_delete and st.session_state.selected_ids:
        st.warning(f"⚠️ Stai per eliminare {n_sel} prestazione/i.")
        if st.button("⚠️ Conferma Eliminazione", type="primary"):
            session.query(Prestazione).filter(Prestazione.id.in_(st.session_state.selected_ids)).delete(synchronize_session=False)
            session.commit()
            st.session_state.selected_ids = set()
            st.success("Prestazioni eliminate!")
            st.rerun()

    # --- DUPLICA ---
    if btn_dup and st.session_state.selected_ids:
        prest_to_dup = session.query(Prestazione).filter(Prestazione.id.in_(st.session_state.selected_ids)).all()
        for p in prest_to_dup:
            new_p = Prestazione(
                cliente_id=p.cliente_id, conto_ricavo_id=p.conto_ricavo_id,
                fatturante_id=p.fatturante_id, periodicita=p.periodicita,
                descrizione=p.descrizione, importo_unitario=p.importo_unitario,
                aliquota_iva=p.aliquota_iva, data_inizio=p.data_inizio,
                data_fine=p.data_fine, modalita_incasso=p.modalita_incasso, note=p.note or "",
            )
            session.add(new_p)
        session.commit()
        st.success(f"✅ {len(prest_to_dup)} prestazione/i duplicate!")
        st.rerun()

    # --- DUPLICA CON PERIODO ---
    for btn, period_name in [(btn_dup_m, "Mensile"), (btn_dup_t, "Trimestrale"),
                              (btn_dup_s, "Semestrale"), (btn_dup_a, "Annuale")]:
        if btn and st.session_state.selected_ids:
            prest_to_dup = session.query(Prestazione).filter(Prestazione.id.in_(st.session_state.selected_ids)).all()
            for p in prest_to_dup:
                new_p = Prestazione(
                    cliente_id=p.cliente_id, conto_ricavo_id=p.conto_ricavo_id,
                    fatturante_id=p.fatturante_id, periodicita=p.periodicita,
                    descrizione=p.descrizione, importo_unitario=p.importo_unitario,
                    aliquota_iva=p.aliquota_iva,
                    data_inizio=add_period(p.data_inizio, period_name),
                    data_fine=add_period(p.data_fine, period_name),
                    modalita_incasso=p.modalita_incasso, note=p.note or "",
                )
                session.add(new_p)
            session.commit()
            st.success(f"✅ {len(prest_to_dup)} prestazione/i duplicate con +1 {period_name.lower()}!")
            st.rerun()

    # --- EMETTI FATTURE ---
    if btn_emetti and st.session_state.selected_ids:
        prest_sel = session.query(Prestazione).filter(
            Prestazione.id.in_(st.session_state.selected_ids),
            Prestazione.fattura_id.is_(None)
        ).all()
        if not prest_sel:
            st.warning("Nessuna prestazione non fatturata tra quelle selezionate.")
        else:
            # Raggruppa per cliente + fatturante
            groups = {}
            for p in prest_sel:
                key = (p.cliente_id, p.fatturante_id)
                groups.setdefault(key, []).append(p)

            fatture_create = 0
            for (cid, fid), prests in groups.items():
                anno = sel_y
                numero = get_next_fattura_number(session, fid, anno)
                totale_imp = sum(float(p.importo_unitario) for p in prests)
                totale_iva = sum(p.importo_iva for p in prests)
                totale = sum(p.totale for p in prests)

                nuova_fattura = Fattura(
                    numero=numero, anno=anno, data=date.today(),
                    cliente_id=cid, fatturante_id=fid,
                    totale_imponibile=Decimal(str(totale_imp)),
                    totale_iva=Decimal(str(totale_iva)),
                    totale=Decimal(str(totale)),
                    stato="Emessa"
                )
                session.add(nuova_fattura)
                session.flush()
                for p in prests:
                    p.fattura_id = nuova_fattura.id
                fatture_create += 1

            session.commit()
            st.session_state.selected_ids = set()
            st.success(f"✅ {fatture_create} fattura/e emessa/e!")
            st.rerun()

    # --- GENERA XML FATTURAPA ---
    if btn_xml:
        fatture_da_gen = session.query(Fattura).filter(Fattura.xml_generato == False).all()
        if not fatture_da_gen:
            st.info("Nessuna fattura da generare. Tutte le fatture hanno già l'XML.")
        else:
            xml_list = []
            for f in fatture_da_gen:
                righe = session.query(Prestazione).filter(Prestazione.fattura_id == f.id).all()
                cl = clienti.get(f.cliente_id)
                ft = fatturanti.get(f.fatturante_id)
                if cl and ft and righe:
                    xml_str, filename = genera_fattura_xml(f, righe, ft, cl)
                    xml_list.append((xml_str, filename))
                    f.xml_generato = True
                    f.xml_filename = filename
                    f.stato = "XML Generato"
            session.commit()

            if len(xml_list) == 1:
                st.download_button(
                    f"⬇️ Scarica {xml_list[0][1]}",
                    data=xml_list[0][0],
                    file_name=xml_list[0][1],
                    mime="application/xml"
                )
            elif len(xml_list) > 1:
                zip_data = genera_zip_fatture(xml_list)
                st.download_button(
                    f"⬇️ Scarica {len(xml_list)} fatture (ZIP)",
                    data=zip_data,
                    file_name=f"fatture_{sel_y}_{sel_m:02d}.zip",
                    mime="application/zip"
                )
            st.success(f"✅ XML generato per {len(xml_list)} fattura/e!")

    # --- CARICA SDD SEPA ---
    if btn_sdd and st.session_state.selected_ids:
        prest_sdd = session.query(Prestazione).filter(
            Prestazione.id.in_(st.session_state.selected_ids),
            Prestazione.modalita_incasso == "SDD SEPA"
        ).all()
        if not prest_sdd:
            st.warning("Nessuna prestazione SDD SEPA tra quelle selezionate.")
        else:
            incassi_data = []
            for p in prest_sdd:
                cl = clienti.get(p.cliente_id)
                if cl and cl.sdd_attivo and cl.iban_sdd:
                    residuo = p.credito_residuo
                    if residuo > 0:
                        new_inc = Incasso(
                            prestazione_id=p.id,
                            importo=Decimal(str(residuo)),
                            data=date.today(),
                            stato="Caricato da confermare",
                            modalita="SDD SEPA",
                        )
                        session.add(new_inc)
                        incassi_data.append({
                            "cliente": cl,
                            "importo": residuo,
                            "prestazione_descrizione": p.descrizione + calc_periodicity_label(p.periodicita, p.data_inizio),
                        })
            session.commit()

            if incassi_data:
                ft = next(iter(fatturanti.values()))
                xml_sdd = genera_sdd_xml(ft, incassi_data)
                st.download_button(
                    "⬇️ Scarica XML SDD SEPA per Home Banking",
                    data=xml_sdd,
                    file_name=f"SDD_SEPA_{date.today().isoformat()}.xml",
                    mime="application/xml"
                )
                st.success(f"✅ SDD caricato per {len(incassi_data)} prestazione/i. "
                           f"Stato: 'Caricato da confermare'.")
                st.session_state.selected_ids = set()

    # --- CONFERMA SDD ---
    if btn_conf_sdd:
        updated = session.query(Incasso).filter(Incasso.stato == "Caricato da confermare").update(
            {"stato": "Confermato"}, synchronize_session=False
        )
        session.commit()
        if updated:
            st.success(f"✅ {updated} incasso/i SDD confermati!")
            st.rerun()
        else:
            st.info("Nessun SDD in attesa di conferma.")

finally:
    session.close()
