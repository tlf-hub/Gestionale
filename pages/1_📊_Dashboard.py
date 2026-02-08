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
from sqlalchemy.orm import joinedload

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
init_db()
st.markdown(COMMON_CSS, unsafe_allow_html=True)
check_auth()
logout_button()

# === SESSION STATE DEFAULTS ===
if "sel_month" not in st.session_state:
    st.session_state.sel_month = date.today().month - 1
if "sel_year" not in st.session_state:
    st.session_state.sel_year = date.today().year
if "selected_ids" not in st.session_state:
    st.session_state.selected_ids = set()
if "filter_mode" not in st.session_state:
    st.session_state.filter_mode = "quick"  # "quick" = mesi/anno, "advanced" = filtri avanzati

st.markdown('<div class="page-header"><h2>📊 Dashboard Prestazioni</h2></div>',
            unsafe_allow_html=True)

session = get_session()
try:
    # === LOAD LOOKUPS (una sola query ciascuno, cached) ===
    clienti = {c.id: c for c in session.query(Cliente).order_by(Cliente.cognome_ragione_sociale).all()}
    conti = {c.id: c for c in session.query(ContoRicavo).order_by(ContoRicavo.codice).all()}
    fatturanti = {f.id: f for f in session.query(SoggettoFatturante).order_by(SoggettoFatturante.ragione_sociale).all()}

    if not fatturanti:
        st.warning("⚠️ Aggiungi almeno un Soggetto Fatturante, un Conto Ricavo e un Cliente.")
        st.stop()

    # =============================================
    # RIGA 1: MESI + ANNO (applicazione immediata)
    # =============================================
    cols = st.columns(14)
    for i in range(12):
        with cols[i]:
            is_sel = (st.session_state.sel_month == i
                      and st.session_state.filter_mode == "quick")
            if st.button(MESI_SHORT[i], key=f"m_{i}", use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                st.session_state.sel_month = i
                st.session_state.filter_mode = "quick"
                st.rerun()
    with cols[12]:
        if st.button("◀", use_container_width=True):
            st.session_state.sel_year -= 1
            st.session_state.filter_mode = "quick"
            st.rerun()
    with cols[13]:
        if st.button("▶", use_container_width=True):
            st.session_state.sel_year += 1
            st.session_state.filter_mode = "quick"
            st.rerun()

    sel_m = st.session_state.sel_month + 1
    sel_y = st.session_state.sel_year

    # Banner: mostra solo se filtro rapido attivo
    if st.session_state.filter_mode == "quick":
        st.markdown(f'<div class="month-banner">{MESI[sel_m-1]} {sel_y}</div>',
                    unsafe_allow_html=True)

    # =============================================
    # FILTRI AVANZATI (alternativi ai pulsanti mese)
    # =============================================
    with st.expander("🔍 Filtri avanzati", expanded=(st.session_state.filter_mode == "advanced")):
        fc1, fc2, fc3 = st.columns(3)
        flt_cl = fc1.selectbox("Cliente", ["Tutti"] + [c.denominazione for c in clienti.values()],
                               key="flt_cl")
        flt_cr = fc2.selectbox("Conto Ricavo",
                               ["Tutti"] + [f"{c.codice} - {c.descrizione}" for c in conti.values()],
                               key="flt_cr")
        flt_ft = fc3.selectbox("Fatturante",
                               ["Tutti"] + [f.ragione_sociale for f in fatturanti.values()],
                               key="flt_ft")

        fd1, fd2, fd3 = st.columns(3)
        flt_stato = fd1.selectbox("Stato fatturazione",
                                  ["Tutti", "Fatturato", "Non fatturato"], key="flt_stato")
        flt_per = fd2.selectbox("Periodicità", ["Tutte"] + PERIODICITA_OPTIONS, key="flt_per")
        flt_date = fd3.text_input("📅 Filtro data",
            placeholder="2026, 02/2026, febbraio 2026, >01/01/2026, 01/01-31/03/2026",
            help="Formati: 2026 | 02/2026 | febbraio 2026 | 15/02/2026 | >dd/mm/yyyy | <dd/mm/yyyy | dd/mm/yyyy-dd/mm/yyyy | */2/2026",
            key="flt_date")

        # Salva / Carica filtri
        sf1, sf2, sf3 = st.columns([2, 3, 2])
        if sf1.button("🔍 Applica filtri", type="primary", use_container_width=True):
            st.session_state.filter_mode = "advanced"
            st.rerun()

        saved_name = sf2.text_input("Nome filtro", placeholder="es: Prestazioni bilanci",
                                    key="sf_name", label_visibility="collapsed")
        if sf3.button("💾 Salva filtro", use_container_width=True) and saved_name:
            filtri = {"cliente": flt_cl, "conto": flt_cr, "fatturante": flt_ft,
                      "stato": flt_stato, "periodicita": flt_per, "data": flt_date}
            session.add(SavedFilter(user_id=st.session_state.user_id, nome=saved_name, filtri=filtri))
            session.commit()
            st.success(f"✅ Filtro '{saved_name}' salvato!")
            st.rerun()

        saved = session.query(SavedFilter).filter(
            SavedFilter.user_id == st.session_state.user_id
        ).order_by(SavedFilter.nome).all()
        if saved:
            sl1, sl2, sl3 = st.columns([3, 1, 1])
            sel_filter = sl1.selectbox("📂 Filtri salvati",
                                       [""] + [f.nome for f in saved], key="load_filter")
            if sel_filter:
                sf_obj = next((f for f in saved if f.nome == sel_filter), None)
                if sf_obj:
                    if sl2.button("📂 Carica"):
                        f = sf_obj.filtri
                        st.session_state.flt_cl = f.get("cliente", "Tutti")
                        st.session_state.flt_cr = f.get("conto", "Tutti")
                        st.session_state.flt_ft = f.get("fatturante", "Tutti")
                        st.session_state.flt_stato = f.get("stato", "Tutti")
                        st.session_state.flt_per = f.get("periodicita", "Tutte")
                        st.session_state.flt_date = f.get("data", "")
                        st.session_state.filter_mode = "advanced"
                        st.rerun()
                    if sl3.button("🗑️ Elimina filtro"):
                        session.delete(sf_obj)
                        session.commit()
                        st.rerun()

        if st.button("↩️ Torna a filtro mese/anno"):
            st.session_state.filter_mode = "quick"
            st.rerun()

    # =============================================
    # QUERY PRESTAZIONI (ottimizzata con joinedload)
    # =============================================
    q = session.query(Prestazione).options(
        joinedload(Prestazione.cliente),
        joinedload(Prestazione.conto_ricavo),
        joinedload(Prestazione.fatturante),
        joinedload(Prestazione.fattura),
        joinedload(Prestazione.incassi),
    )

    if st.session_state.filter_mode == "advanced":
        # Filtri avanzati: NO filtro mese/anno rapido
        st.markdown('<div class="month-banner">🔍 Filtro avanzato attivo</div>',
                    unsafe_allow_html=True)

        # Filtro data testuale
        date_filter_parsed = parse_date_filter(flt_date)
        if date_filter_parsed:
            q = apply_date_filter(q, Prestazione.data_inizio, date_filter_parsed)

        # Filtri aggiuntivi
        if flt_cl != "Tutti":
            cid = next((c.id for c in clienti.values() if c.denominazione == flt_cl), None)
            if cid:
                q = q.filter(Prestazione.cliente_id == cid)
        if flt_cr != "Tutti":
            cod = flt_cr.split(" - ")[0]
            crid = next((c.id for c in conti.values() if c.codice == cod), None)
            if crid:
                q = q.filter(Prestazione.conto_ricavo_id == crid)
        if flt_ft != "Tutti":
            fid = next((f.id for f in fatturanti.values() if f.ragione_sociale == flt_ft), None)
            if fid:
                q = q.filter(Prestazione.fatturante_id == fid)
        if flt_per != "Tutte":
            q = q.filter(Prestazione.periodicita == flt_per)
        if flt_stato == "Fatturato":
            q = q.filter(Prestazione.fattura_id.isnot(None))
        elif flt_stato == "Non fatturato":
            q = q.filter(Prestazione.fattura_id.is_(None))
    else:
        # Filtro rapido mese/anno
        q = q.filter(
            extract("month", Prestazione.data_inizio) == sel_m,
            extract("year", Prestazione.data_inizio) == sel_y
        )

    prestazioni = q.order_by(Prestazione.data_inizio, Prestazione.cliente_id).all()

    # Pulisci selezione: rimuovi ID non più nell'elenco corrente
    valid_ids = {p.id for p in prestazioni}
    st.session_state.selected_ids = st.session_state.selected_ids & valid_ids

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
    # PULSANTI AZIONE (riga 1 e 2)
    # =============================================
    st.markdown("---")
    a1, a2, a3, a4, a5, a6 = st.columns(6)
    btn_del = a1.button("🗑️ Elimina", use_container_width=True)
    btn_dup = a2.button("📋 Duplica", use_container_width=True)
    btn_m = a3.button("+1 Mese", use_container_width=True)
    btn_t = a4.button("+1 Trim.", use_container_width=True)
    btn_s = a5.button("+1 Sem.", use_container_width=True)
    btn_a = a6.button("+1 Anno", use_container_width=True)

    b1, b2, b3, b4 = st.columns(4)
    btn_emetti = b1.button("📄 Emetti Fattura", use_container_width=True, type="primary")
    btn_incassa = b2.button("💰 Incassa selez.", use_container_width=True)
    btn_sdd = b3.button("🏦 Crea SDD SEPA", use_container_width=True)
    btn_xml = b4.button("📋 Genera XML", use_container_width=True)

    st.markdown("---")

    # =============================================
    # SELEZIONA TUTTO / DESELEZIONA + RAGGRUPPAMENTO
    # =============================================
    sa1, sa2, sa3, sa4 = st.columns([1, 1, 2, 4])
    if sa1.button("☑️ Selez. tutto", use_container_width=True):
        st.session_state.selected_ids = {p.id for p in prestazioni}
        st.rerun()
    if sa2.button("⬜ Deselez. tutto", use_container_width=True):
        st.session_state.selected_ids = set()
        st.rerun()

    RAGGRUPPAMENTI = [
        "Conto Ricavo", "Nessuno", "Fatturante", "Periodicità",
        "Fatturate/Non fatturate", "Incassate/Non incassate"
    ]
    raggruppamento = sa3.selectbox("Raggruppa per", RAGGRUPPAMENTI, key="raggr",
                                   label_visibility="collapsed")
    sa4.markdown(f"**{len(st.session_state.selected_ids)}** selezionate su **{len(prestazioni)}**")

    # Link nuova prestazione
    st.markdown(
        f'<a href="/Nuova_Prestazione?month={sel_m}&year={sel_y}" target="_blank" '
        f'style="display:inline-block;background:#3b82f6;color:white;padding:6px 16px;'
        f'border-radius:6px;text-decoration:none;font-weight:600;font-size:0.9rem;">'
        f'➕ Nuova Prestazione (nuova scheda)</a>', unsafe_allow_html=True)

    # =============================================
    # TABELLA PRESTAZIONI
    # =============================================
    if not prestazioni:
        st.info("Nessuna prestazione trovata con i filtri correnti.")
    else:
        # Funzione raggruppamento
        def get_group_key(p):
            if raggruppamento == "Conto Ricavo":
                cr = conti.get(p.conto_ricavo_id)
                return f"{cr.codice} - {cr.descrizione}" if cr else "—"
            elif raggruppamento == "Fatturante":
                ft = fatturanti.get(p.fatturante_id)
                return ft.ragione_sociale if ft else "—"
            elif raggruppamento == "Periodicità":
                return p.periodicita
            elif raggruppamento == "Fatturate/Non fatturate":
                return "✅ Fatturate" if p.is_fatturata else "⏳ Non fatturate"
            elif raggruppamento == "Incassate/Non incassate":
                return "✅ Incassate" if p.credito_residuo <= 0 else "⏳ Non incassate"
            else:
                return None

        # Raggruppa
        if raggruppamento != "Nessuno":
            groups = {}
            for p in prestazioni:
                k = get_group_key(p)
                groups.setdefault(k, []).append(p)
        else:
            groups = {"": prestazioni}

        # CSS righe alternate
        st.markdown("""<style>
        .alt-table { width:100%; border-collapse:collapse; font-size:0.82rem; }
        .alt-table th { background:#1e293b; color:white; padding:6px 5px; text-align:left;
            font-size:0.78rem; font-weight:600; position:sticky; top:0; z-index:5; }
        .alt-table td { padding:5px 5px; border-bottom:1px solid #e2e8f0; }
        .alt-table tr.r0 { background:#ffffff; }
        .alt-table tr.r1 { background:#f0f9ff; }
        .alt-table tr:hover { background:#dbeafe !important; }
        .alt-table .money { text-align:right; font-family:monospace; white-space:nowrap; }
        .alt-table .center { text-align:center; }
        .grp-header { background:#e2e8f0; padding:6px 10px; border-radius:6px;
            font-weight:bold; margin:8px 0 4px; font-size:0.9rem; }
        .badge-si { background:#dcfce7; color:#166534; padding:1px 5px; border-radius:3px; font-size:0.75rem; }
        .badge-no { background:#fef3c7; color:#92400e; padding:1px 5px; border-radius:3px; font-size:0.75rem; }
        @media(max-width:768px) {
            .alt-table { font-size:0.72rem; }
            .alt-table th, .alt-table td { padding:3px 2px; }
            .hide-m { display:none !important; }
        }
        </style>""", unsafe_allow_html=True)

        # Render dei gruppi
        for group_name, group_prests in groups.items():
            if group_name:
                tot_g = sum(p.totale for p in group_prests)
                st.markdown(f'<div class="grp-header">{group_name} — '
                            f'{len(group_prests)} record — {format_currency(tot_g)}</div>',
                            unsafe_allow_html=True)

            # Checkbox per selezione — uso st.checkbox individuale
            # Ma per performance con molte righe, uso data_editor
            rows = []
            for p in group_prests:
                cl = p.cliente
                cr = p.conto_ricavo
                ft = p.fatturante
                fa = p.fattura
                pl = calc_periodicity_label(p.periodicita, p.data_inizio)
                rows.append({
                    "_id": p.id,
                    "✓": p.id in st.session_state.selected_ids,
                    "Data": p.data_inizio.strftime("%d/%m/%Y") if p.data_inizio else "",
                    "Cliente": cl.denominazione if cl else "-",
                    "Descrizione": (p.descrizione + pl)[:50],
                    "Importo": float(p.importo_unitario or 0),
                    "IVA%": p.aliquota_iva,
                    "Totale": round(p.totale, 2),
                    "Incassato": round(p.totale_incassato, 2),
                    "Residuo": round(p.credito_residuo, 2),
                    "Mod": (p.modalita_incasso or "")[:4],
                    "Fatt.": f"{fa.numero}/{fa.anno}" if fa else "—",
                    "Per": (p.periodicita or "")[:3],
                })

            df = pd.DataFrame(rows)

            # Chiave unica per data_editor per gruppo
            safe_key = f"tbl_{hash(group_name) % 100000}"

            edited = st.data_editor(
                df.drop(columns=["_id"]),
                column_config={
                    "✓": st.column_config.CheckboxColumn("✓", width=35, default=False),
                    "Data": st.column_config.TextColumn(width=85),
                    "Cliente": st.column_config.TextColumn(width=150),
                    "Descrizione": st.column_config.TextColumn(width=200),
                    "Importo": st.column_config.NumberColumn(format="€ %.2f", width=85),
                    "IVA%": st.column_config.NumberColumn(width=45),
                    "Totale": st.column_config.NumberColumn(format="€ %.2f", width=85),
                    "Incassato": st.column_config.NumberColumn(format="€ %.2f", width=85),
                    "Residuo": st.column_config.NumberColumn(format="€ %.2f", width=85),
                    "Mod": st.column_config.TextColumn(width=42),
                    "Fatt.": st.column_config.TextColumn(width=60),
                    "Per": st.column_config.TextColumn(width=40),
                },
                disabled=["Data", "Cliente", "Descrizione", "Importo", "IVA%",
                           "Totale", "Incassato", "Residuo", "Mod", "Fatt.", "Per"],
                hide_index=True,
                use_container_width=True,
                height=min(500, 38 + len(df) * 35),
                key=safe_key,
            )

            # Sincronizza checkbox → selected_ids
            if edited is not None:
                for i, row in edited.iterrows():
                    pid = df.iloc[i]["_id"]
                    if row.get("✓", False):
                        st.session_state.selected_ids.add(pid)
                    else:
                        st.session_state.selected_ids.discard(pid)

        # =============================================
        # AZIONI PER SINGOLA RIGA (edit / incassi)
        # =============================================
        st.markdown("#### 🔧 Azione rapida su singola prestazione")
        prest_opts = {p.id: f"#{p.id} — {p.cliente.denominazione if p.cliente else '-'} — {p.descrizione}"
                      for p in prestazioni}
        sel_row_id = st.selectbox("Seleziona:", list(prest_opts.keys()),
                                  format_func=lambda x: prest_opts[x], key="sel_row")

        if sel_row_id:
            rc1, rc2 = st.columns(2)
            rc1.markdown(
                f'<a href="/Modifica_Prestazione?id={sel_row_id}" target="_blank" '
                f'style="display:block;text-align:center;background:#dbeafe;color:#1d4ed8;'
                f'padding:8px;border-radius:8px;text-decoration:none;font-weight:bold;">'
                f'✏️ Modifica (nuova scheda)</a>', unsafe_allow_html=True)
            rc2.markdown(
                f'<a href="/Incassi_Prestazione?id={sel_row_id}" target="_blank" '
                f'style="display:block;text-align:center;background:#dcfce7;color:#166534;'
                f'padding:8px;border-radius:8px;text-decoration:none;font-weight:bold;">'
                f'💰 Incassi (nuova scheda)</a>', unsafe_allow_html=True)

    # =============================================
    # AZIONI MASSIVE
    # =============================================
    sids = st.session_state.selected_ids

    def _no_sel():
        if not sids:
            st.warning("⚠️ Nessuna prestazione selezionata.")
            return True
        return False

    def _load_selected():
        """Carica le prestazioni selezionate con gestione sicura."""
        if not sids:
            return []
        id_list = [int(i) for i in sids]
        return session.query(Prestazione).options(
            joinedload(Prestazione.cliente),
            joinedload(Prestazione.incassi),
        ).filter(Prestazione.id.in_(id_list)).all()

    # --- ELIMINA ---
    if btn_del and not _no_sel():
        st.session_state["confirm_action"] = "delete"

    if st.session_state.get("confirm_action") == "delete":
        st.warning(f"⚠️ **Eliminare {len(sids)} prestazioni?** Azione irreversibile.")
        cd1, cd2 = st.columns(2)
        if cd1.button("✅ Sì, elimina", type="primary", key="yes_del"):
            id_list = [int(i) for i in sids]
            session.query(Incasso).filter(Incasso.prestazione_id.in_(id_list)).delete(synchronize_session=False)
            session.query(Prestazione).filter(Prestazione.id.in_(id_list)).delete(synchronize_session=False)
            session.commit()
            st.session_state.selected_ids = set()
            st.session_state.pop("confirm_action", None)
            st.success("✅ Eliminate!")
            st.rerun()
        if cd2.button("❌ Annulla", key="no_del"):
            st.session_state.pop("confirm_action", None)
            st.rerun()

    # --- DUPLICA (stessa data o spostata) ---
    dup_period = None
    if btn_dup and not _no_sel():
        dup_period = "same"
    elif btn_m and not _no_sel():
        dup_period = "Mensile"
    elif btn_t and not _no_sel():
        dup_period = "Trimestrale"
    elif btn_s and not _no_sel():
        dup_period = "Semestrale"
    elif btn_a and not _no_sel():
        dup_period = "Annuale"

    if dup_period:
        st.session_state["confirm_action"] = f"dup_{dup_period}"

    dup_key = st.session_state.get("confirm_action", "")
    if dup_key.startswith("dup_"):
        period = dup_key[4:]
        label = "identiche" if period == "same" else f"spostate +1 {period.lower()}"
        st.info(f"📋 **Duplicare {len(sids)} prestazioni ({label})?**")
        dd1, dd2 = st.columns(2)
        if dd1.button("✅ Sì, duplica", type="primary", key="yes_dup"):
            psel = _load_selected()
            new_ids = set()
            for p in psel:
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
                new_ids.add(new_p.id)
            session.commit()
            st.session_state.selected_ids = new_ids
            st.session_state.pop("confirm_action", None)
            st.success(f"✅ {len(new_ids)} prestazioni duplicate!")
            st.rerun()
        if dd2.button("❌ Annulla", key="no_dup"):
            st.session_state.pop("confirm_action", None)
            st.rerun()

    # --- EMETTI FATTURE ---
    if btn_emetti and not _no_sel():
        psel = _load_selected()
        gia_fatt = [p for p in psel if p.is_fatturata]
        if gia_fatt:
            st.error(f"⚠️ {len(gia_fatt)} prestazioni hanno GIÀ una fattura. Deselezionale.")
        else:
            fatt_ids = set(p.fatturante_id for p in psel)
            if len(fatt_ids) > 1:
                nomi = [fatturanti[fid].ragione_sociale for fid in fatt_ids if fid in fatturanti]
                st.error(f"⚠️ Fatturanti diversi: {', '.join(nomi)}. Filtra prima per fatturante.")
            else:
                st.session_state["confirm_action"] = "emetti"

    if st.session_state.get("confirm_action") == "emetti":
        psel = _load_selected()
        psel = [p for p in psel if not p.is_fatturata]
        if psel:
            st.markdown("### 📄 Anteprima Emissione Fattura")
            data_em = st.date_input("📅 Data emissione", value=date.today(), key="dt_em")

            groups_fatt = {}
            for p in psel:
                groups_fatt.setdefault(p.cliente_id, []).append(p)

            for cid, prests in groups_fatt.items():
                cl = clienti.get(cid)
                tot_g = sum(p.totale for p in prests)
                st.markdown(f"**{cl.denominazione if cl else '-'}** — {len(prests)} righe — "
                            f"{format_currency(tot_g)}")
                for p in prests:
                    st.caption(f"  • {p.descrizione} — {format_currency(p.importo_unitario)} + IVA {p.aliquota_iva}%")

            ef1, ef2 = st.columns(2)
            if ef1.button("✅ Conferma emissione", type="primary", key="yes_em"):
                fatt_id = psel[0].fatturante_id
                for cid, prests in groups_fatt.items():
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
                st.session_state.pop("confirm_action", None)
                st.success(f"✅ {len(groups_fatt)} fattura/e emessa/e!")
                st.rerun()
            if ef2.button("❌ Annulla", key="no_em"):
                st.session_state.pop("confirm_action", None)
                st.rerun()

    # --- INCASSA I SELEZIONATI ---
    if btn_incassa and not _no_sel():
        st.session_state["confirm_action"] = "incassa"

    if st.session_state.get("confirm_action") == "incassa":
        psel = _load_selected()
        psel_cr = [p for p in psel if p.credito_residuo > 0]
        if not psel_cr:
            st.warning("Nessuna prestazione con credito residuo.")
            st.session_state.pop("confirm_action", None)
        else:
            st.markdown("### 💰 Anteprima Incasso")
            ic1, ic2 = st.columns(2)
            data_inc = ic1.date_input("📅 Data incasso", value=date.today(), key="dt_inc")
            mod_inc = ic2.selectbox("Modalità", MODALITA_INCASSO_OPTIONS, key="mod_inc")

            tot_inc = sum(p.credito_residuo for p in psel_cr)
            st.markdown(f"**{len(psel_cr)} prestazioni — Totale: {format_currency(tot_inc)}**")
            for p in psel_cr:
                cl = p.cliente
                st.caption(f"  • {cl.denominazione if cl else '-'} — {p.descrizione} — "
                           f"{format_currency(p.credito_residuo)}")

            ii1, ii2 = st.columns(2)
            if ii1.button("✅ Conferma incasso", type="primary", key="yes_inc"):
                for p in psel_cr:
                    session.add(Incasso(
                        prestazione_id=p.id, importo=Decimal(str(round(p.credito_residuo, 2))),
                        data=data_inc, stato="Confermato", modalita=mod_inc))
                session.commit()
                st.session_state.pop("confirm_action", None)
                st.success(f"✅ {len(psel_cr)} incassi registrati!")
                st.rerun()
            if ii2.button("❌ Annulla", key="no_inc"):
                st.session_state.pop("confirm_action", None)
                st.rerun()

    # --- CREA SDD SEPA ---
    if btn_sdd and not _no_sel():
        psel = _load_selected()
        non_fatt = [p for p in psel if not p.is_fatturata]
        if non_fatt:
            st.error(f"⚠️ {len(non_fatt)} prestazioni senza fattura. Emetti prima le fatture.")
        else:
            fatt_ids = set(p.fatturante_id for p in psel)
            if len(fatt_ids) > 1:
                nomi = [fatturanti[fid].ragione_sociale for fid in fatt_ids if fid in fatturanti]
                st.error(f"⚠️ Fatturanti diversi: {', '.join(nomi)}. Filtra per fatturante.")
            else:
                st.session_state["confirm_action"] = "sdd"

    if st.session_state.get("confirm_action") == "sdd":
        psel = _load_selected()
        psel_sdd = [p for p in psel if p.is_fatturata and p.credito_residuo > 0]
        if not psel_sdd:
            st.warning("Nessuna prestazione con credito residuo.")
            st.session_state.pop("confirm_action", None)
        else:
            st.markdown("### 🏦 Anteprima Tracciato SDD SEPA")
            data_add = st.date_input("📅 Data addebito", value=date.today(), key="dt_sdd")

            anomalie = []
            inc_data = []
            for p in psel_sdd:
                cl = p.cliente
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
                    anomalie.append(f"{cl.denominazione}: rif. mandato SDD mancante")
                inc_data.append({
                    "prestazione": p, "cliente": cl,
                    "importo": round(p.credito_residuo, 2),
                    "prestazione_descrizione": p.descrizione + calc_periodicity_label(p.periodicita, p.data_inizio),
                })

            if anomalie:
                st.warning("⚠️ **Anomalie:**")
                for a in anomalie:
                    st.caption(f"  ⚠️ {a}")

            if inc_data:
                tot_sdd = sum(i["importo"] for i in inc_data)
                st.markdown(f"**{len(inc_data)} addebiti — Totale: {format_currency(tot_sdd)}**")
                for i in inc_data:
                    st.caption(f"  • {i['cliente'].denominazione} — {i['prestazione_descrizione']} — "
                               f"{format_currency(i['importo'])}")

                sd1, sd2 = st.columns(2)
                if sd1.button("✅ Conferma e genera XML", type="primary", key="yes_sdd"):
                    for i in inc_data:
                        session.add(Incasso(
                            prestazione_id=i["prestazione"].id,
                            importo=Decimal(str(i["importo"])),
                            data=data_add, stato="Caricato da confermare", modalita="SDD SEPA"))
                    session.commit()

                    fatt_id = psel_sdd[0].fatturante_id
                    ft = fatturanti[fatt_id]
                    xml = genera_sdd_xml(ft, inc_data, data_add)
                    st.download_button("⬇️ Scarica XML SDD SEPA", xml,
                                       f"SDD_{data_add.isoformat()}.xml", "application/xml")
                    st.session_state.pop("confirm_action", None)
                    st.success(f"✅ Tracciato SDD creato!")
                if sd2.button("❌ Annulla", key="no_sdd"):
                    st.session_state.pop("confirm_action", None)
                    st.rerun()
            else:
                st.error("Nessun addebito valido.")
                if st.button("Chiudi", key="close_sdd"):
                    st.session_state.pop("confirm_action", None)
                    st.rerun()

    # --- GENERA XML FATTURE ---
    if btn_xml:
        fno = session.query(Fattura).filter(Fattura.xml_generato == False).all()
        if not fno:
            st.info("Nessuna fattura da esportare in XML.")
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
                st.download_button(f"⬇️ Scarica ZIP ({len(xml_list)})",
                                   genera_zip_fatture(xml_list), "fatture.zip", "application/zip")
            st.success(f"✅ {len(xml_list)} XML generati!")

finally:
    session.close()
