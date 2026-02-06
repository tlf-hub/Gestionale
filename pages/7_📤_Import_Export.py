"""📤 Import/Export — Caricamento massivo da Excel/CSV e download template."""
import streamlit as st
import pandas as pd
import io
from datetime import date
from database import get_session, init_db
from models import Cliente, ContoRicavo, SoggettoFatturante, Prestazione, Fattura, Incasso
from config import TIPO_CLIENTE_OPTIONS, REGIME_FISCALE_OPTIONS, MODALITA_INCASSO_OPTIONS

st.set_page_config(page_title="Import/Export", page_icon="📤", layout="wide")
init_db()
st.markdown("## 📤 Import / Export Dati")

session = get_session()
try:
    tab_imp, tab_exp = st.tabs(["📥 Importa", "📤 Esporta"])

    # =========================================================================
    # TEMPLATES
    # =========================================================================
    TEMPLATES = {
        "Clienti": {
            "columns": ["cognome_ragione_sociale","nome","titolo","indirizzo","cap","citta",
                "provincia","paese","tipo_cliente","regime_fiscale","liquidazione_iva",
                "sostituto_imposta","split_payment","codice_fiscale","partita_iva",
                "cassa_previdenza","rappresentante_legale","carica_rl","cf_rl",
                "telefono","cellulare","mail","pec","codice_sdi",
                "sdd_attivo","iban_sdd","data_mandato_sdd","rif_mandato_sdd",
                "modalita_incasso","cliente_attivo"],
            "sample": ["Rossi SRL","","","Via Roma 1","20121","Milano","MI","IT",
                "srl","Ordinario","Mensile","False","False","01234567890","01234567890",
                "","Mario Rossi","Amministratore","RSSMRA80A01H501Z",
                "02-1234567","333-1234567","info@rossi.it","rossi@pec.it","XXXXXXX",
                "True","IT60X0542811101000000123456","2024-01-15","MAND-001",
                "SDD SEPA","True"],
        },
        "Conti Ricavo": {
            "columns": ["codice", "descrizione"],
            "sample": ["CR001", "Consulenza fiscale"],
        },
        "Soggetti Fatturanti": {
            "columns": ["ragione_sociale","partita_iva","codice_fiscale","indirizzo",
                "cap","citta","provincia","paese","regime_fiscale","pec","codice_sdi","iban"],
            "sample": ["Studio Rossi","01234567890","RSSMRA80A01H501Z","Via Roma 10",
                "20121","Milano","MI","IT","Ordinario","studio@pec.it","XXXXXXX",
                "IT60X0542811101000000123456"],
        },
        "Prestazioni": {
            "columns": ["cliente_partita_iva","conto_ricavo_codice","fatturante_partita_iva",
                "periodicita","descrizione","importo_unitario","aliquota_iva",
                "data_inizio","data_fine","modalita_incasso","note"],
            "sample": ["01234567890","CR001","01234567890","Mensile",
                "Contabilità","350.00","22","2025-01-01","2025-01-31","SDD SEPA",""],
        },
    }

    # =========================================================================
    # IMPORT TAB
    # =========================================================================
    with tab_imp:
        st.markdown("### 📥 Importa Dati da Excel o CSV")
        st.info("⚠️ I doppioni vengono rilevati automaticamente in base a Partita IVA o Codice Fiscale.")

        for table_name, template in TEMPLATES.items():
            st.markdown(f"---")
            st.markdown(f"#### {table_name}")

            # Download template
            template_df = pd.DataFrame([template["sample"]], columns=template["columns"])
            buffer = io.BytesIO()
            template_df.to_excel(buffer, index=False, engine="openpyxl")
            buffer.seek(0)
            st.download_button(
                f"📋 Scarica Template {table_name}",
                data=buffer.getvalue(),
                file_name=f"template_{table_name.lower().replace(' ','_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"tmpl_{table_name}"
            )

            # Upload
            uploaded = st.file_uploader(
                f"📤 Carica file {table_name}",
                type=["xlsx", "csv"],
                key=f"upload_{table_name}"
            )

            if uploaded:
                try:
                    if uploaded.name.endswith(".csv"):
                        df = pd.read_csv(uploaded, dtype=str).fillna("")
                    else:
                        df = pd.read_excel(uploaded, dtype=str, engine="openpyxl").fillna("")

                    st.dataframe(df.head(10), use_container_width=True)
                    st.caption(f"{len(df)} righe trovate nel file.")

                    if st.button(f"⬆️ Importa {len(df)} record in {table_name}", key=f"imp_btn_{table_name}", type="primary"):
                        imported = 0
                        skipped = 0

                        if table_name == "Clienti":
                            for _, row in df.iterrows():
                                piva = str(row.get("partita_iva", "")).strip()
                                cf = str(row.get("codice_fiscale", "")).strip()
                                dup = False
                                if piva:
                                    dup = session.query(Cliente).filter(Cliente.partita_iva == piva).first() is not None
                                if not dup and cf:
                                    dup = session.query(Cliente).filter(Cliente.codice_fiscale == cf).first() is not None
                                if dup:
                                    skipped += 1
                                    continue
                                session.add(Cliente(
                                    cognome_ragione_sociale=str(row.get("cognome_ragione_sociale", "")),
                                    nome=str(row.get("nome", "")),
                                    titolo=str(row.get("titolo", "")),
                                    indirizzo=str(row.get("indirizzo", "")),
                                    cap=str(row.get("cap", "")),
                                    citta=str(row.get("citta", "")),
                                    provincia=str(row.get("provincia", "")),
                                    paese=str(row.get("paese", "IT")) or "IT",
                                    tipo_cliente=str(row.get("tipo_cliente", "srl")),
                                    regime_fiscale=str(row.get("regime_fiscale", "Ordinario")),
                                    liquidazione_iva=str(row.get("liquidazione_iva", "")),
                                    sostituto_imposta=str(row.get("sostituto_imposta", "")).lower() == "true",
                                    split_payment=str(row.get("split_payment", "")).lower() == "true",
                                    codice_fiscale=cf,
                                    partita_iva=piva,
                                    cassa_previdenza=str(row.get("cassa_previdenza", "")),
                                    rappresentante_legale=str(row.get("rappresentante_legale", "")),
                                    carica_rl=str(row.get("carica_rl", "")),
                                    cf_rl=str(row.get("cf_rl", "")),
                                    telefono=str(row.get("telefono", "")),
                                    cellulare=str(row.get("cellulare", "")),
                                    mail=str(row.get("mail", "")),
                                    pec=str(row.get("pec", "")),
                                    codice_sdi=str(row.get("codice_sdi", "0000000")),
                                    sdd_attivo=str(row.get("sdd_attivo", "")).lower() == "true",
                                    iban_sdd=str(row.get("iban_sdd", "")),
                                    rif_mandato_sdd=str(row.get("rif_mandato_sdd", "")),
                                    modalita_incasso=str(row.get("modalita_incasso", "Bonifico")),
                                    cliente_attivo=str(row.get("cliente_attivo", "True")).lower() != "false",
                                ))
                                imported += 1

                        elif table_name == "Conti Ricavo":
                            for _, row in df.iterrows():
                                codice = str(row.get("codice", "")).strip()
                                if session.query(ContoRicavo).filter(ContoRicavo.codice == codice).first():
                                    skipped += 1
                                    continue
                                session.add(ContoRicavo(
                                    codice=codice,
                                    descrizione=str(row.get("descrizione", ""))
                                ))
                                imported += 1

                        elif table_name == "Soggetti Fatturanti":
                            for _, row in df.iterrows():
                                piva = str(row.get("partita_iva", "")).strip()
                                if session.query(SoggettoFatturante).filter(SoggettoFatturante.partita_iva == piva).first():
                                    skipped += 1
                                    continue
                                session.add(SoggettoFatturante(
                                    ragione_sociale=str(row.get("ragione_sociale", "")),
                                    partita_iva=piva,
                                    codice_fiscale=str(row.get("codice_fiscale", "")),
                                    indirizzo=str(row.get("indirizzo", "")),
                                    cap=str(row.get("cap", "")),
                                    citta=str(row.get("citta", "")),
                                    provincia=str(row.get("provincia", "")),
                                    paese=str(row.get("paese", "IT")) or "IT",
                                    regime_fiscale=str(row.get("regime_fiscale", "Ordinario")),
                                    pec=str(row.get("pec", "")),
                                    codice_sdi=str(row.get("codice_sdi", "0000000")),
                                    iban=str(row.get("iban", "")),
                                ))
                                imported += 1

                        elif table_name == "Prestazioni":
                            for _, row in df.iterrows():
                                cl_piva = str(row.get("cliente_partita_iva", "")).strip()
                                cr_cod = str(row.get("conto_ricavo_codice", "")).strip()
                                ft_piva = str(row.get("fatturante_partita_iva", "")).strip()
                                cl = session.query(Cliente).filter(Cliente.partita_iva == cl_piva).first()
                                cr = session.query(ContoRicavo).filter(ContoRicavo.codice == cr_cod).first()
                                ft = session.query(SoggettoFatturante).filter(SoggettoFatturante.partita_iva == ft_piva).first()
                                if not cl or not cr or not ft:
                                    skipped += 1
                                    continue
                                from decimal import Decimal
                                session.add(Prestazione(
                                    cliente_id=cl.id,
                                    conto_ricavo_id=cr.id,
                                    fatturante_id=ft.id,
                                    periodicita=str(row.get("periodicita", "Mensile")),
                                    descrizione=str(row.get("descrizione", "")),
                                    importo_unitario=Decimal(str(row.get("importo_unitario", "0"))),
                                    aliquota_iva=int(float(row.get("aliquota_iva", "22"))),
                                    data_inizio=pd.to_datetime(row.get("data_inizio")).date(),
                                    data_fine=pd.to_datetime(row.get("data_fine")).date(),
                                    modalita_incasso=str(row.get("modalita_incasso", "Bonifico")),
                                    note=str(row.get("note", "")),
                                ))
                                imported += 1

                        session.commit()
                        st.success(f"✅ Importati: {imported} | Doppioni saltati: {skipped}")
                        st.rerun()

                except Exception as e:
                    st.error(f"Errore nel file: {e}")

    # =========================================================================
    # EXPORT TAB
    # =========================================================================
    with tab_exp:
        st.markdown("### 📤 Esporta Dati")

        export_tables = {
            "Clienti": lambda: pd.DataFrame([{
                "cognome_ragione_sociale": c.cognome_ragione_sociale, "nome": c.nome,
                "titolo": c.titolo, "tipo_cliente": c.tipo_cliente,
                "partita_iva": c.partita_iva, "codice_fiscale": c.codice_fiscale,
                "citta": c.citta, "provincia": c.provincia, "pec": c.pec,
                "codice_sdi": c.codice_sdi, "sdd_attivo": c.sdd_attivo,
                "iban_sdd": c.iban_sdd, "modalita_incasso": c.modalita_incasso,
                "cliente_attivo": c.cliente_attivo,
            } for c in session.query(Cliente).all()]),
            "Conti Ricavo": lambda: pd.DataFrame([{
                "codice": c.codice, "descrizione": c.descrizione,
            } for c in session.query(ContoRicavo).all()]),
            "Soggetti Fatturanti": lambda: pd.DataFrame([{
                "ragione_sociale": f.ragione_sociale, "partita_iva": f.partita_iva,
                "codice_fiscale": f.codice_fiscale, "citta": f.citta,
                "pec": f.pec, "iban": f.iban,
            } for f in session.query(SoggettoFatturante).all()]),
            "Fatture": lambda: pd.DataFrame([{
                "numero": f.numero, "anno": f.anno, "data": f.data,
                "totale": float(f.totale), "stato": f.stato,
            } for f in session.query(Fattura).all()]),
        }

        for name, get_df_fn in export_tables.items():
            st.markdown(f"---")
            ec1, ec2, ec3 = st.columns([3, 1, 1])
            with ec1:
                st.markdown(f"**{name}**")
            df_exp = get_df_fn()
            with ec2:
                buf = io.BytesIO()
                df_exp.to_excel(buf, index=False, engine="openpyxl")
                buf.seek(0)
                st.download_button(f"📥 Excel", data=buf.getvalue(),
                    file_name=f"{name.lower().replace(' ','_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"exp_xl_{name}")
            with ec3:
                csv_data = df_exp.to_csv(index=False).encode("utf-8")
                st.download_button(f"📥 CSV", data=csv_data,
                    file_name=f"{name.lower().replace(' ','_')}.csv",
                    mime="text/csv", key=f"exp_csv_{name}")

finally:
    session.close()
