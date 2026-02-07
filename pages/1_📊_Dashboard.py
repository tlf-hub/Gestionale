"""📊 Dashboard — Gestione prestazioni completa."""
import streamlit as st
import pandas as pd
from datetime import date
from decimal import Decimal
from database import get_session, init_db
from models import (Prestazione, Cliente, ContoRicavo, SoggettoFatturante,
                    Fattura, Incasso, SavedFilter)
from config import (MESI, MESI_SHORT, PERIODICITA_OPTIONS, MODALITA_INCASSO_OPTIONS,
                    ALIQUOTA_OPTIONS)
from utils.helpers import (format_currency, calc_periodicity_label, add_period,
                           get_next_fattura_number, parse_date_filter, apply_date_filter)
from utils.fattura_xml import genera_fattura_xml, genera_zip_fatture
from utils.sdd_sepa_xml import genera_sdd_xml
from utils.styles import COMMON_CSS
from utils.auth import check_auth, logout_button
from sqlalchemy import extract
import calendar

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
init_db()
st.markdown(COMMON_CSS, unsafe_allow_html=True)
check_auth()
logout_button()

# === SESSION STATE DEFAULTS ===
defaults = {
    "sel_month": date.today().month - 1,
    "sel_year": date.today().year,
    "selected_ids": set(),
    "active_row_id": None,
    "use_advanced_filter": False,
    "adv_filter_text": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown("""
<div class="page-header">
<h2>📊 Dashboard Prestazioni</h2>
</div>""", unsafe_allow_html=True)

session = get_session()
try:
    # === LOAD LOOKUPS ===
    clienti = {c.id: c for c in session.query(Cliente).order_by(Cliente.cognome_ragione_sociale).all()}
    conti = {c.id: c for c in session.query(ContoRicavo).order_by(ContoRicavo.codice).all()}
    fatturanti = {f.id: f for f in session.query(SoggettoFatturante).order_by(SoggettoFatturante.ragione_sociale).all()}

    if not clienti or not conti or not fatturanti:
        st.warning("⚠️ Devi prima aggiungere almeno un Cliente, un Conto Ricavo e un Soggetto Fatturante.")
        st.stop()

    # =============================================
    # RIGA 1: MESI + ANNO (applicazione immediata)
    # =============================================
    cols = st.columns(14)
    for i in range(12):
        with cols[i]:
            is_sel = st.session_state.sel_month == i and not st.session_state.use_advanced_filter
            if st.button(MESI_SHORT[i], key=f"m_{i}", use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                st.session_state.sel_month = i
                st.session_state.use_advanced_filter = False
                st.rerun()
    with cols[12]:
        if st.button("◀", use_container_width=True):
            st.session_state.sel_year -= 1
            st.session_state.use_advanced_filter = False
            st.rerun()
    with cols[13]:
        if st.button("▶", use_container_width=True):
            st.session_state.sel_year += 1
            st.session_state.use_advanced_filter = False
            st.rerun()

    sel_m = st.session_state.sel_month + 1
    sel_y = st.session_state.sel_year

    # Banner mese/anno (solo se non c'è filtro avanzato attivo)
    if not st.session_state.use_advanced_filter:
        st.markdown(f'<div class="month-banner">{MESI[sel_m-1]} {sel_y}</div>',
                    unsafe_allow_html=True)

    # =============================================
    # RIGA 2: FILTRI con pulsante APPLICA
    # =============================================
    with st.expander("🔍 Filtri avanzati", expanded=st.session_state.use_advanced_filter):
        fc1, fc2, fc3 = st.columns(3)
        fc = fc1.selectbox("Cliente", ["Tutti"] + [c.denominazione for c in clienti.values()], key="flt_cl")
        fcr = fc2.selectbox("Conto Ricavo", ["Tutti"] + [f"{c.codice} - {c.descrizione}" for c in conti.values()], key="flt_cr")
        ff = fc3.selectbox("Fatturante", ["Tutti"] + [f.ragione_sociale for f in fatturanti.values()], key="flt_ft")

        fd1, fd2, fd3 = st.columns(3)
        fcred = fd1.selectbox("Stato fatturazione", ["Tutti","Con credito","Fatturato","Non fatturato"], key="flt_stato")
        fp = fd2.selectbox("Periodicità", ["Tutte"] + PERIODICITA_OPTIONS, key="flt_per")
        date_text = fd3.text_input("📅 Filtro data",
            placeholder="es: 2026, 02/2026, febbraio 2026, >01/01/2026",
            help="Formati: 2026 | 02/2026 | febbraio 2026 | 15/02/2026 | >01/01/2026 | <31/12/2026 | 01/01/2026-31/03/2026",
            key="flt_date")

        raggr = fd1.selectbox("Raggruppa per", ["Nessuno","Cliente","Conto Ricavo","Fatturante","Fattura"], key="flt_raggr")

        # Salva/Carica filtri
        sf1, sf2, sf3 = st.columns([2, 3, 2])
        if sf1.button("🔍 Applica filtri", type="primary", use_container_width=True):
            st.session_state.use_advanced_filter = True
            st.rerun()

        # Salva filtro
        saved_name = sf2.text_input("Nome filtro", placeholder="es: Prestazioni bilanci", key="sf_name",
                                    label_visibility="collapsed")
        if sf3.button("💾 Salva filtro", use_container_width=True) and saved_name:
            filtri = {"cliente": fc, "conto": fcr, "fatturante": ff, "stato": fcred,
                      "periodicita": fp, "data": date_text, "raggruppamento": raggr}
            session.add(SavedFilter(user_id=st.session_state.user_id, nome=saved_name, filtri=filtri))
            session.commit()
            st.success(f"Filtro '{saved_name}' salvato!")
            st.rerun()

        # Carica filtri salvati
        saved = session.query(SavedFilter).filter(
            SavedFilter.user_id == st.session_state.user_id
        ).order_by(SavedFilter.nome).all()
        if saved:
            sl1, sl2 = st.columns([4, 1])
            sel_filter = sl1.selectbox("📂 Filtri salvati",
                [""] + [f.nome for f in saved], key="load_filter")
            if sel_filter:
                sf_obj = next((f for f in saved if f.nome == sel_filter), None)
                if sf_obj and sl2.button("📂 Carica"):
                    f = sf_obj.filtri
                    st.session_state.flt_cl = f.get("cliente", "Tutti")
                    st.session_state.flt_cr = f.get("conto", "Tutti")
                    st.session_state.flt_ft = f.get("fatturante", "Tutti")
                    st.session_state.flt_stato = f.get("stato", "Tutti")
                    st.session_state.flt_per = f.get("periodicita", "Tutte")
                    st.session_state.flt_date = f.get("data", "")
                    st.session_state.flt_raggr = f.get("raggruppamento", "Nessuno")
                    st.session_state.use_advanced_filter = True
                    st.rerun()

        if st.button("↩️ Reset filtri", use_container_width=False):
            st.session_state.use_advanced_filter = False
            st.rerun()

    # =============================================
    # QUERY con filtri
    # =============================================
    q = session.query(Prestazione)

    # Filtro data: se avanzato attivo, usa il campo data; altrimenti mese/anno rapido
    date_filter_parsed = parse_date_filter(date_text) if st.session_state.use_advanced_filter else None

    if date_filter_parsed and st.session_state.use_advanced_filter:
        q = apply_date_filter(q, Prestazione.data_inizio, date_filter_parsed)
        st.markdown(f'<div class="month-banner">🔍 Filtro avanzato attivo</div>', unsafe_allow_html=True)
    else:
        q = q.filter(
            extract("month", Prestazione.data_inizio) == sel_m,
            extract("year", Prestazione.data_inizio) == sel_y
        )

    # Filtri aggiuntivi (sempre attivi)
    if fc != "Tutti":
        cid = next((c.id for c in clienti.values() if c.denominazione == fc), None)
        if cid: q = q.filter(Prestazione.cliente_id == cid)
    if fcr != "Tutti":
        cod = fcr.split(" - ")[0]
        crid = next((c.id for c in conti.values() if c.codice == cod), None)
        if crid: q = q.filter(Prestazione.conto_ricavo_id == crid)
    if ff != "Tutti":
        fid = next((f.id for f in fatturanti.values() if f.ragione_sociale == ff), None)
        if fid: q = q.filter(Prestazione.fatturante_id == fid)
    if fp != "Tutte":
        q = q.filter(Prestazione.periodicita == fp)
    if fcred == "Fatturato":
        q = q.filter(Prestazione.fattura_id.isnot(None))
    elif fcred == "Non fatturato":
        q = q.filter(Prestazione.fattura_id.is_(None))

    prestazioni = q.order_by(Prestazione.data_inizio, Prestazione.cliente_id).all()

    # =============================================
    # METRICHE
    # =============================================
    tot = sum(p.totale for p in prestazioni)
    inc = sum(p.totale_incassato for p in prestazioni)
    fat = sum(p.totale for p in prestazioni if p.is_fatturata)
    nfat = sum(p.totale for p in prestazioni if not p.is_fatturata)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Totale", format_currency(tot), f"{len(prestazioni)} record")
    m2.metric("Fatturato", format_currency(fat))
    m3.metric("Non fatturato", format_currency(nfat))
    m4.metric("Incassato", format_currency(inc))
    m5.metric("Residuo", format_currency(tot - inc))

    # =============================================
    # PULSANTI AZIONE
    # =============================================
    st.markdown("---")
    # Riga 1: CRUD
    a1, a2, a3, a4, a5, a6, a7, a8 = st.columns(8)
    btn_new = a1.button("➕ Nuova", use_container_width=True, help="Apre nuova scheda")
    btn_del = a2.button("🗑️ Elimina", use_container_width=True)
    btn_dup = a3.button("📋 Duplica", use_container_width=True)
    btn_m = a4.button("+1 Mese", use_container_width=True)
    btn_t = a5.button("+1 Trim.", use_container_width=True)
    btn_s = a6.button("+1 Sem.", use_container_width=True)
    btn_a = a7.button("+1 Anno", use_container_width=True)
    btn_emetti = a8.button("📄 Emetti Fatt.", use_container_width=True, type="primary")

    # Riga 2: Incasso, SDD, XML
    b1, b2, b3, b4 = st.columns(4)
    btn_incassa = b1.button("💰 Incassa i selezionati", use_container_width=True)
    btn_sdd = b2.button("🏦 Crea SDD SEPA", use_container_width=True)
    btn_xml = b3.button("📋 Genera XML", use_container_width=True)
    btn_conf_sdd = b4.button("✅ Conferma SDD", use_container_width=True)

    # Nuova prestazione: apre link in nuova scheda
    if btn_new:
        params = f"?month={sel_m}&year={sel_y}"
        st.markdown(
            f'<script>window.open("/Nuova_Prestazione{params}", "_blank");</script>',
            unsafe_allow_html=True)
        st.info("📌 Si apre una nuova scheda per creare la prestazione.")

    st.markdown("---")

    # =============================================
    # TABELLA PRESTAZIONI con checkbox
    # =============================================
    if not prestazioni:
        st.info("Nessuna prestazione trovata con i filtri correnti.")
    else:
        # Build dataframe
        rows = []
        for p in prestazioni:
            cl = clienti.get(p.cliente_id)
            cr = conti.get(p.conto_ricavo_id)
            ft = fatturanti.get(p.fatturante_id)
            fa = session.query(Fattura).get(p.fattura_id) if p.fattura_id else None
            pl = calc_periodicity_label(p.periodicita, p.data_inizio)
            rows.append({
                "id": p.id,
                "Sel": p.id in st.session_state.selected_ids,
                "Esigibilità": f"{p.data_inizio.strftime('%d/%m/%Y')} → {p.data_fine.strftime('%d/%m/%Y')}",
                "Cliente": cl.denominazione if cl else "-",
                "Descrizione": p.descrizione + pl,
                "Importo": float(p.importo_unitario),
                "IVA%": p.aliquota_iva,
                "Totale": p.totale,
                "Incassato": p.totale_incassato,
                "Residuo": p.credito_residuo,
                "Mod.": p.modalita_incasso[:3],
                "Fatturante": ft.ragione_sociale if ft else "-",
                "Fattura": f"{fa.numero}/{fa.anno}" if fa else "—",
                "Per.": p.periodicita[:3],
            })

        df = pd.DataFrame(rows)

        # CSS per righe alternate e riga attiva
        st.markdown("""
        <style>
        [data-testid="stDataEditor"] [data-testid="data-grid-canvas"]
            div[data-row-index]:nth-child(even) { background-color: #f0f9ff !important; }
        [data-testid="stDataEditor"] [data-testid="data-grid-canvas"]
            div[data-row-index]:nth-child(odd) { background-color: #ffffff !important; }
        </style>
        """, unsafe_allow_html=True)

        # Select All / Deselect All
        sa1, sa2, sa3 = st.columns([1, 1, 6])
        if sa1.button("☑️ Seleziona tutto", use_container_width=True):
            st.session_state.selected_ids = {p.id for p in prestazioni}
            st.rerun()
        if sa2.button("⬜ Deseleziona tutto", use_container_width=True):
            st.session_state.selected_ids = set()
            st.rerun()
        sa3.markdown(f"**{len(st.session_state.selected_ids)}** selezionate su {len(prestazioni)}")

        # Data editor con checkbox
        display_cols = ["Sel", "Esigibilità", "Cliente", "Descrizione", "Importo", "IVA%",
                        "Totale", "Incassato", "Residuo", "Mod.", "Fatturante", "Fattura", "Per."]

        edited_df = st.data_editor(
            df[display_cols],
            column_config={
                "Sel": st.column_config.CheckboxColumn("✓", width=40, default=False),
                "Importo": st.column_config.NumberColumn(format="€ %.2f", width=90),
                "Totale": st.column_config.NumberColumn(format="€ %.2f", width=90),
                "Incassato": st.column_config.NumberColumn(format="€ %.2f", width=90),
                "Residuo": st.column_config.NumberColumn(format="€ %.2f", width=90),
                "IVA%": st.column_config.NumberColumn(width=50),
                "Mod.": st.column_config.TextColumn(width=45),
                "Per.": st.column_config.TextColumn(width=45),
            },
            disabled=["Esigibilità", "Cliente", "Descrizione", "Importo", "IVA%",
                       "Totale", "Incassato", "Residuo", "Mod.", "Fatturante", "Fattura", "Per."],
            hide_index=True,
            use_container_width=True,
            height=min(600, 40 + len(df) * 35),
            key="prest_table"
        )

        # Sincronizza selezione
        if edited_df is not None:
            new_sel = set()
            for i, row in edited_df.iterrows():
                if row.get("Sel", False):
                    new_sel.add(df.iloc[i]["id"])
            st.session_state.selected_ids = new_sel

        n_sel = len(st.session_state.selected_ids)

        # =============================================
        # AZIONI PER SINGOLA RIGA (edit / incassi)
        # =============================================
        st.markdown("#### 🔧 Azioni su singola prestazione")
        row_options = {p.id: f"#{p.id} — {clienti.get(p.cliente_id, type('',(),{'denominazione':'-'})()).denominazione} — {p.descrizione}" for p in prestazioni}
        sel_row_id = st.selectbox("Seleziona prestazione:", list(row_options.keys()),
            format_func=lambda x: row_options[x], key="sel_row_action")

        if sel_row_id:
            rc1, rc2, rc3 = st.columns(3)
            # Edit link (nuova scheda)
            rc1.markdown(
                f'<a href="/Modifica_Prestazione?id={sel_row_id}" target="_blank" '
                f'style="display:block;text-align:center;background:#dbeafe;color:#1d4ed8;'
                f'padding:8px;border-radius:8px;text-decoration:none;font-weight:bold;">'
                f'✏️ Modifica</a>', unsafe_allow_html=True)
            # Incassi link (nuova scheda)
            rc2.markdown(
                f'<a href="/Incassi_Prestazione?id={sel_row_id}" target="_blank" '
                f'style="display:block;text-align:center;background:#dcfce7;color:#166534;'
                f'padding:8px;border-radius:8px;text-decoration:none;font-weight:bold;">'
                f'💰 Incassi</a>', unsafe_allow_html=True)
            rc3.markdown(
                f'<a href="/Nuova_Prestazione?month={sel_m}&year={sel_y}" target="_blank" '
                f'style="display:block;text-align:center;background:#fef3c7;color:#92400e;'
                f'padding:8px;border-radius:8px;text-decoration:none;font-weight:bold;">'
                f'➕ Nuova Prestazione</a>', unsafe_allow_html=True)

    # =============================================
    # AZIONI MASSIVE (richiedono selezione)
    # =============================================
    sids = st.session_state.selected_ids

    def _check_selection():
        if not sids:
            st.warning("⚠️ Nessuna prestazione selezionata.")
            return False
        return True

    # --- ELIMINA ---
    if btn_del:
        if _check_selection():
            st.session_state["confirm_delete"] = True

    if st.session_state.get("confirm_delete"):
        st.warning(f"⚠️ **Confermi l'eliminazione di {len(sids)} prestazioni?** Questa azione è irreversibile.")
        cd1, cd2 = st.columns(2)
        if cd1.button("✅ Sì, elimina", type="primary", key="conf_del_yes"):
            session.query(Incasso).filter(
                Incasso.prestazione_id.in_(sids)).delete(synchronize_session=False)
            session.query(Prestazione).filter(
                Prestazione.id.in_(sids)).delete(synchronize_session=False)
            session.commit()
            st.session_state.selected_ids = set()
            st.session_state.pop("confirm_delete", None)
            st.success("✅ Eliminate!")
            st.rerun()
        if cd2.button("❌ Annulla", key="conf_del_no"):
            st.session_state.pop("confirm_delete", None)
            st.rerun()

    # --- DUPLICA ---
    if btn_dup:
        if _check_selection():
            st.session_state["confirm_dup"] = "same"
    for btn, per_name, per_key in [(btn_m, "Mensile", "dup_m"), (btn_t, "Trimestrale", "dup_t"),
                                    (btn_s, "Semestrale", "dup_s"), (btn_a, "Annuale", "dup_a")]:
        if btn:
            if _check_selection():
                st.session_state["confirm_dup"] = per_name

    if st.session_state.get("confirm_dup"):
        period = st.session_state["confirm_dup"]
        label = "identiche" if period == "same" else f"spostate +1 {period.lower()}"
        st.info(f"📋 **Duplicare {len(sids)} prestazioni ({label})?**")
        dd1, dd2 = st.columns(2)
        if dd1.button("✅ Sì, duplica", type="primary", key="conf_dup_yes"):
            new_ids = []
            for p in session.query(Prestazione).filter(Prestazione.id.in_(sids)).all():
                di = p.data_inizio if period == "same" else add_period(p.data_inizio, period)
                df_new = p.data_fine if period == "same" else add_period(p.data_fine, period)
                new_p = Prestazione(
                    cliente_id=p.cliente_id, conto_ricavo_id=p.conto_ricavo_id,
                    fatturante_id=p.fatturante_id, periodicita=p.periodicita,
                    descrizione=p.descrizione, importo_unitario=p.importo_unitario,
                    aliquota_iva=p.aliquota_iva, data_inizio=di, data_fine=df_new,
                    modalita_incasso=p.modalita_incasso, note=p.note or "")
                session.add(new_p)
                session.flush()
                new_ids.append(new_p.id)
            session.commit()
            st.session_state.selected_ids = set(new_ids)  # Nuove diventano attive
            st.session_state.pop("confirm_dup", None)
            st.success(f"✅ {len(new_ids)} prestazioni duplicate!")
            st.rerun()
        if dd2.button("❌ Annulla", key="conf_dup_no"):
            st.session_state.pop("confirm_dup", None)
            st.rerun()

    # --- EMETTI FATTURE ---
    if btn_emetti:
        if _check_selection():
            psel = session.query(Prestazione).filter(
                Prestazione.id.in_(sids)).all()

            # Controllo: nessuna deve avere già una fattura
            gia_fatt = [p for p in psel if p.is_fatturata]
            if gia_fatt:
                st.error(f"⚠️ {len(gia_fatt)} prestazioni selezionate hanno GIÀ una fattura. "
                         "Deselezionale prima di procedere.")
            else:
                # Controllo: stesso fatturante
                fatt_ids = set(p.fatturante_id for p in psel)
                if len(fatt_ids) > 1:
                    nomi = [fatturanti[fid].ragione_sociale for fid in fatt_ids]
                    st.error(f"⚠️ Le prestazioni selezionate hanno fatturanti diversi: {', '.join(nomi)}. "
                             "Filtra prima per fatturante.")
                else:
                    st.session_state["emetti_preview"] = True

    if st.session_state.get("emetti_preview"):
        psel = session.query(Prestazione).filter(
            Prestazione.id.in_(sids), Prestazione.fattura_id.is_(None)).all()
        if psel:
            st.markdown("### 📄 Anteprima Emissione Fattura")
            data_em = st.date_input("📅 Data emissione", value=date.today(), key="data_emissione")

            # Raggruppamento per cliente
            groups = {}
            for p in psel:
                groups.setdefault(p.cliente_id, []).append(p)

            for cid, prests in groups.items():
                cl = clienti.get(cid)
                tot_g = sum(p.totale for p in prests)
                st.markdown(f"**{cl.denominazione if cl else '-'}** — {len(prests)} righe — "
                            f"Totale: {format_currency(tot_g)}")
                for p in prests:
                    st.caption(f"  • {p.descrizione} — {format_currency(p.importo_unitario)} + IVA {p.aliquota_iva}%")

            ef1, ef2 = st.columns(2)
            if ef1.button("✅ Conferma emissione", type="primary", key="conf_emetti"):
                fatt_id = next(iter(set(p.fatturante_id for p in psel)))
                for cid, prests in groups.items():
                    num = get_next_fattura_number(session, fatt_id, data_em.year)
                    t_imp = sum(float(p.importo_unitario) for p in prests)
                    t_iva = sum(p.importo_iva for p in prests)
                    t_tot = sum(p.totale for p in prests)
                    f = Fattura(numero=num, anno=data_em.year, data=data_em, cliente_id=cid,
                        fatturante_id=fatt_id, totale_imponibile=Decimal(str(t_imp)),
                        totale_iva=Decimal(str(t_iva)), totale=Decimal(str(t_tot)))
                    session.add(f)
                    session.flush()
                    for p in prests:
                        p.fattura_id = f.id
                session.commit()
                st.session_state.selected_ids = set()
                st.session_state.pop("emetti_preview", None)
                st.success(f"✅ {len(groups)} fattura/e emessa/e!")
                st.rerun()
            if ef2.button("❌ Annulla", key="conf_emetti_no"):
                st.session_state.pop("emetti_preview", None)
                st.rerun()

    # --- INCASSA I SELEZIONATI ---
    if btn_incassa:
        if _check_selection():
            st.session_state["incassa_preview"] = True

    if st.session_state.get("incassa_preview"):
        psel = session.query(Prestazione).filter(Prestazione.id.in_(sids)).all()
        psel = [p for p in psel if p.credito_residuo > 0]
        if not psel:
            st.warning("Nessuna prestazione selezionata con credito residuo.")
            st.session_state.pop("incassa_preview", None)
        else:
            st.markdown("### 💰 Anteprima Incasso")
            ic1, ic2 = st.columns(2)
            data_inc = ic1.date_input("📅 Data incasso", value=date.today(), key="data_incasso")
            mod_inc = ic2.selectbox("Modalità", MODALITA_INCASSO_OPTIONS, key="mod_incasso")

            tot_inc = sum(p.credito_residuo for p in psel)
            st.markdown(f"**{len(psel)} prestazioni — Totale da incassare: {format_currency(tot_inc)}**")
            for p in psel:
                cl = clienti.get(p.cliente_id)
                st.caption(f"  • {cl.denominazione if cl else '-'} — {p.descrizione} — "
                           f"{format_currency(p.credito_residuo)}")

            ii1, ii2 = st.columns(2)
            if ii1.button("✅ Conferma incasso", type="primary", key="conf_incassa"):
                for p in psel:
                    session.add(Incasso(
                        prestazione_id=p.id, importo=Decimal(str(p.credito_residuo)),
                        data=data_inc, stato="Confermato", modalita=mod_inc))
                session.commit()
                st.session_state.pop("incassa_preview", None)
                st.success(f"✅ {len(psel)} incassi registrati!")
                st.rerun()
            if ii2.button("❌ Annulla", key="conf_incassa_no"):
                st.session_state.pop("incassa_preview", None)
                st.rerun()

    # --- CREA SDD SEPA ---
    if btn_sdd:
        if _check_selection():
            psel = session.query(Prestazione).filter(Prestazione.id.in_(sids)).all()

            # Controllo: tutte fatturate
            non_fatt = [p for p in psel if not p.is_fatturata]
            if non_fatt:
                st.error(f"⚠️ {len(non_fatt)} prestazioni NON hanno fattura emessa. "
                         "Emetti prima le fatture per tutte le prestazioni selezionate.")
            else:
                # Controllo: stesso fatturante
                fatt_ids = set(p.fatturante_id for p in psel)
                if len(fatt_ids) > 1:
                    nomi = [fatturanti[fid].ragione_sociale for fid in fatt_ids]
                    st.error(f"⚠️ I fatturanti sono diversi: {', '.join(nomi)}. "
                             "Filtra prima per fatturante.")
                else:
                    st.session_state["sdd_preview"] = True

    if st.session_state.get("sdd_preview"):
        psel = session.query(Prestazione).filter(
            Prestazione.id.in_(sids), Prestazione.fattura_id.isnot(None)).all()
        psel_sdd = [p for p in psel if p.credito_residuo > 0]
        if not psel_sdd:
            st.warning("Nessuna prestazione con credito residuo.")
            st.session_state.pop("sdd_preview", None)
        else:
            st.markdown("### 🏦 Anteprima Tracciato SDD SEPA")
            data_add = st.date_input("📅 Data addebito", value=date.today(), key="data_sdd")

            anomalie = []
            inc_data = []
            for p in psel_sdd:
                cl = clienti.get(p.cliente_id)
                if not cl:
                    anomalie.append(f"Prestazione #{p.id}: cliente non trovato")
                    continue
                if not cl.sdd_attivo:
                    anomalie.append(f"{cl.denominazione}: SDD non attivo")
                    continue
                if not cl.iban_sdd:
                    anomalie.append(f"{cl.denominazione}: IBAN SDD mancante")
                    continue
                if not cl.rif_mandato_sdd:
                    anomalie.append(f"{cl.denominazione}: riferimento mandato SDD mancante")

                inc_data.append({
                    "prestazione": p, "cliente": cl,
                    "importo": p.credito_residuo,
                    "prestazione_descrizione": p.descrizione + calc_periodicity_label(p.periodicita, p.data_inizio)
                })

            if anomalie:
                st.warning("⚠️ **Anomalie riscontrate:**")
                for a in anomalie:
                    st.caption(f"  ⚠️ {a}")

            if inc_data:
                tot_sdd = sum(i["importo"] for i in inc_data)
                st.markdown(f"**{len(inc_data)} addebiti — Totale: {format_currency(tot_sdd)}**")
                for i in inc_data:
                    st.caption(f"  • {i['cliente'].denominazione} — {i['prestazione_descrizione']} — "
                               f"{format_currency(i['importo'])} — IBAN: {i['cliente'].iban_sdd}")

                sd1, sd2 = st.columns(2)
                if sd1.button("✅ Conferma e genera XML", type="primary", key="conf_sdd"):
                    # Crea incassi
                    for i in inc_data:
                        session.add(Incasso(
                            prestazione_id=i["prestazione"].id,
                            importo=Decimal(str(i["importo"])),
                            data=data_add, stato="Caricato da confermare", modalita="SDD SEPA"))
                    session.commit()

                    # Genera XML
                    fatt_id = next(iter(set(p.fatturante_id for p in psel_sdd)))
                    ft = fatturanti[fatt_id]
                    xml = genera_sdd_xml(ft, inc_data, data_add)
                    st.download_button("⬇️ Scarica XML SDD SEPA", xml,
                        f"SDD_{data_add.isoformat()}.xml", "application/xml")
                    st.session_state.pop("sdd_preview", None)
                    st.success(f"✅ Tracciato SDD creato per {len(inc_data)} addebiti!")
                if sd2.button("❌ Annulla", key="conf_sdd_no"):
                    st.session_state.pop("sdd_preview", None)
                    st.rerun()
            else:
                st.error("Nessun addebito valido. Risolvi le anomalie sopra.")
                if st.button("Chiudi", key="sdd_close"):
                    st.session_state.pop("sdd_preview", None)
                    st.rerun()

    # --- GENERA XML ---
    if btn_xml:
        fno = session.query(Fattura).filter(Fattura.xml_generato == False).all()
        if not fno:
            st.info("Nessuna fattura da generare.")
        else:
            xml_list = []
            for f in fno:
                righe = session.query(Prestazione).filter(Prestazione.fattura_id == f.id).all()
                cl = clienti.get(f.cliente_id)
                ft = fatturanti.get(f.fatturante_id)
                if cl and ft and righe:
                    xs, fn = genera_fattura_xml(f, righe, ft, cl)
                    xml_list.append((xs, fn))
                    f.xml_generato = True
                    f.xml_filename = fn
                    f.stato = "XML Generato"
            session.commit()
            if len(xml_list) == 1:
                st.download_button("⬇️ Scarica XML", xml_list[0][0], xml_list[0][1], "application/xml")
            elif xml_list:
                st.download_button(f"⬇️ Scarica ZIP ({len(xml_list)})", genera_zip_fatture(xml_list),
                    f"fatture.zip", "application/zip")
            st.success(f"✅ {len(xml_list)} XML generati!")

    # --- CONFERMA SDD ---
    if btn_conf_sdd:
        u = session.query(Incasso).filter(Incasso.stato == "Caricato da confermare").update(
            {"stato": "Confermato"}, synchronize_session=False)
        session.commit()
        if u:
            st.success(f"✅ {u} SDD confermati!")
            st.rerun()
        else:
            st.info("Nessun SDD da confermare.")

finally:
    session.close()
