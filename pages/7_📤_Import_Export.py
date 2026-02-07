"""📤 Import/Export — Upload massivo + Export."""
import streamlit as st
import pandas as pd
import io
from decimal import Decimal
from database import get_session, init_db
from models import Cliente, ContoRicavo, SoggettoFatturante, Prestazione, Fattura
from utils.styles import COMMON_CSS
from utils.auth import check_auth, logout_button

st.set_page_config(page_title="Import/Export", page_icon="📤", layout="wide")
init_db(); st.markdown(COMMON_CSS, unsafe_allow_html=True); check_auth(); logout_button()
st.markdown('<div class="page-header"><h2>📤 Import / Export</h2></div>', unsafe_allow_html=True)

TEMPLATES = {
    "Clienti": {
        "cols": ["cognome_ragione_sociale","nome","titolo","tipo_cliente","regime_fiscale",
            "codice_fiscale","partita_iva","indirizzo","cap","citta","provincia",
            "telefono","mail","pec","codice_sdi","modalita_incasso",
            "sdd_attivo","iban_sdd","rif_mandato_sdd","cliente_attivo"],
        "sample": ["Rossi SRL","","","srl","Ordinario","01234567890","01234567890",
            "Via Roma 1","20121","Milano","MI","02-123456","info@rossi.it",
            "rossi@pec.it","XXXXXXX","SDD SEPA","True","IT60X0542811101000000123456","MAND-001","True"],
    },
    "Conti Ricavo": {"cols": ["codice","descrizione"], "sample": ["CR001","Consulenza fiscale"]},
    "Soggetti Fatturanti": {
        "cols": ["ragione_sociale","partita_iva","codice_fiscale","indirizzo","cap",
            "citta","provincia","regime_fiscale","pec","codice_sdi","iban"],
        "sample": ["Studio Rossi","01234567890","RSSMRA80A01H501Z","Via Roma 10",
            "20121","Milano","MI","Ordinario","studio@pec.it","XXXXXXX","IT60X0542811101000000123456"],
    },
    "Prestazioni": {
        "cols": ["cliente_partita_iva","conto_ricavo_codice","fatturante_partita_iva",
            "periodicita","descrizione","importo_unitario","aliquota_iva",
            "data_inizio","data_fine","modalita_incasso"],
        "sample": ["01234567890","CR001","01234567890","Mensile","Contabilità","350.00","22","2025-01-01","2025-01-31","SDD SEPA"],
    },
}

session = get_session()
try:
    tab_i, tab_e = st.tabs(["📥 Importa", "📤 Esporta"])
    with tab_i:
        for name, tmpl in TEMPLATES.items():
            st.markdown(f"---\n#### {name}")
            tdf = pd.DataFrame([tmpl["sample"]], columns=tmpl["cols"])
            buf = io.BytesIO(); tdf.to_excel(buf, index=False, engine="openpyxl"); buf.seek(0)
            st.download_button(f"📋 Template {name}", buf.getvalue(),
                f"template_{name.lower().replace(' ','_')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"t_{name}")
            up = st.file_uploader(f"Carica {name}", ["xlsx","csv"], key=f"u_{name}")
            if up:
                try:
                    df = pd.read_csv(up, dtype=str).fillna("") if up.name.endswith(".csv") \
                        else pd.read_excel(up, dtype=str, engine="openpyxl").fillna("")
                    st.dataframe(df.head(5), use_container_width=True)
                    if st.button(f"⬆️ Importa {len(df)} {name}", key=f"b_{name}", type="primary"):
                        imp, skip = 0, 0
                        for _, r in df.iterrows():
                            try:
                                if name == "Clienti":
                                    pv = str(r.get("partita_iva","")).strip()
                                    cf2 = str(r.get("codice_fiscale","")).strip()
                                    if (pv and session.query(Cliente).filter(Cliente.partita_iva==pv).first()) or \
                                       (cf2 and session.query(Cliente).filter(Cliente.codice_fiscale==cf2).first()):
                                        skip += 1; continue
                                    session.add(Cliente(
                                        cognome_ragione_sociale=str(r.get("cognome_ragione_sociale","")),
                                        nome=str(r.get("nome","")), titolo=str(r.get("titolo","")),
                                        tipo_cliente=str(r.get("tipo_cliente","srl")),
                                        regime_fiscale=str(r.get("regime_fiscale","Ordinario")),
                                        codice_fiscale=cf2, partita_iva=pv,
                                        indirizzo=str(r.get("indirizzo","")), cap=str(r.get("cap","")),
                                        citta=str(r.get("citta","")), provincia=str(r.get("provincia","")),
                                        paese="IT", telefono=str(r.get("telefono","")),
                                        mail=str(r.get("mail","")), pec=str(r.get("pec","")),
                                        codice_sdi=str(r.get("codice_sdi","0000000")),
                                        modalita_incasso=str(r.get("modalita_incasso","Bonifico")),
                                        sdd_attivo=str(r.get("sdd_attivo","")).lower()=="true",
                                        iban_sdd=str(r.get("iban_sdd","")),
                                        rif_mandato_sdd=str(r.get("rif_mandato_sdd","")),
                                        cliente_attivo=str(r.get("cliente_attivo","True")).lower()!="false"))
                                elif name == "Conti Ricavo":
                                    cod = str(r.get("codice","")).strip()
                                    if session.query(ContoRicavo).filter(ContoRicavo.codice==cod).first():
                                        skip += 1; continue
                                    session.add(ContoRicavo(codice=cod, descrizione=str(r.get("descrizione",""))))
                                elif name == "Soggetti Fatturanti":
                                    pv = str(r.get("partita_iva","")).strip()
                                    if session.query(SoggettoFatturante).filter(SoggettoFatturante.partita_iva==pv).first():
                                        skip += 1; continue
                                    session.add(SoggettoFatturante(
                                        ragione_sociale=str(r.get("ragione_sociale","")), partita_iva=pv,
                                        codice_fiscale=str(r.get("codice_fiscale","")),
                                        indirizzo=str(r.get("indirizzo","")), cap=str(r.get("cap","")),
                                        citta=str(r.get("citta","")), provincia=str(r.get("provincia","")),
                                        paese="IT", regime_fiscale=str(r.get("regime_fiscale","Ordinario")),
                                        pec=str(r.get("pec","")), codice_sdi=str(r.get("codice_sdi","0000000")),
                                        iban=str(r.get("iban",""))))
                                elif name == "Prestazioni":
                                    cl2 = session.query(Cliente).filter(Cliente.partita_iva==str(r.get("cliente_partita_iva",""))).first()
                                    cr2 = session.query(ContoRicavo).filter(ContoRicavo.codice==str(r.get("conto_ricavo_codice",""))).first()
                                    ft2 = session.query(SoggettoFatturante).filter(SoggettoFatturante.partita_iva==str(r.get("fatturante_partita_iva",""))).first()
                                    if not cl2 or not cr2 or not ft2: skip += 1; continue
                                    session.add(Prestazione(
                                        cliente_id=cl2.id, conto_ricavo_id=cr2.id, fatturante_id=ft2.id,
                                        periodicita=str(r.get("periodicita","Mensile")),
                                        descrizione=str(r.get("descrizione","")),
                                        importo_unitario=Decimal(str(r.get("importo_unitario","0"))),
                                        aliquota_iva=int(float(r.get("aliquota_iva","22"))),
                                        data_inizio=pd.to_datetime(r.get("data_inizio")).date(),
                                        data_fine=pd.to_datetime(r.get("data_fine")).date(),
                                        modalita_incasso=str(r.get("modalita_incasso","Bonifico"))))
                                imp += 1
                            except Exception: skip += 1
                        session.commit()
                        st.success(f"✅ Importati: {imp} | Saltati: {skip}"); st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

    with tab_e:
        exports = {
            "Clienti": lambda: pd.DataFrame([{
                "Ragione Sociale": c.cognome_ragione_sociale, "Nome": c.nome,
                "Tipo": c.tipo_cliente, "P.IVA": c.partita_iva, "C.F.": c.codice_fiscale,
                "Città": c.citta, "PEC": c.pec, "SDD": c.sdd_attivo,
            } for c in session.query(Cliente).all()]),
            "Conti Ricavo": lambda: pd.DataFrame([{"Codice": c.codice, "Descrizione": c.descrizione}
                for c in session.query(ContoRicavo).all()]),
            "Fatture": lambda: pd.DataFrame([{
                "N.": f.numero, "Anno": f.anno, "Totale": float(f.totale), "Stato": f.stato,
            } for f in session.query(Fattura).all()]),
        }
        for name, fn in exports.items():
            st.markdown("---")
            df = fn()
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.markdown(f"**{name}** ({len(df)} record)")
            buf = io.BytesIO(); df.to_excel(buf, index=False, engine="openpyxl"); buf.seek(0)
            c2.download_button("📥 Excel", buf.getvalue(), f"{name.lower()}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"ex_{name}")
            c3.download_button("📥 CSV", df.to_csv(index=False).encode(), f"{name.lower()}.csv",
                "text/csv", key=f"ec_{name}")
finally:
    session.close()
