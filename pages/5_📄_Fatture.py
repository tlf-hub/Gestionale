"""📄 Fatture — Elenco, XML, PDF, invio email."""
import streamlit as st
import pandas as pd
from datetime import date
from database import get_session, init_db
from models import Fattura, Prestazione, Cliente, SoggettoFatturante
from utils.helpers import format_currency
from utils.fattura_xml import genera_fattura_xml, genera_zip_fatture
from utils.pdf_generator import genera_fattura_pdf
from utils.email_sender import invia_fattura_email
from utils.styles import COMMON_CSS
from utils.auth import check_auth, logout_button

st.set_page_config(page_title="Fatture", page_icon="📄", layout="wide")
init_db(); st.markdown(COMMON_CSS, unsafe_allow_html=True); check_auth(); logout_button()
st.markdown('<div class="page-header"><h2>📄 Fatture Emesse</h2></div>', unsafe_allow_html=True)

session = get_session()
try:
    clienti = {c.id: c for c in session.query(Cliente).all()}
    fatturanti = {f.id: f for f in session.query(SoggettoFatturante).all()}

    f1, f2, f3 = st.columns(3)
    anno = f1.number_input("Anno", 2020, 2030, date.today().year)
    stato = f2.selectbox("Stato", ["Tutti","Emessa","XML Generato","Inviata a SDI","Accettata","Rifiutata"])
    sf = f3.selectbox("Fatturante", ["Tutti"] + [f.ragione_sociale for f in fatturanti.values()])

    q = session.query(Fattura).filter(Fattura.anno == anno)
    if stato != "Tutti": q = q.filter(Fattura.stato == stato)
    if sf != "Tutti":
        fid = next((f.id for f in fatturanti.values() if f.ragione_sociale == sf), None)
        if fid: q = q.filter(Fattura.fatturante_id == fid)

    fl = q.order_by(Fattura.numero.desc()).all()
    if fl:
        df = pd.DataFrame([{
            "N.": f.numero, "Data": f.data.strftime("%d/%m/%Y") if f.data else "",
            "Cliente": clienti.get(f.cliente_id, type("",(),{"denominazione":"-"})()).denominazione,
            "Fatturante": fatturanti.get(f.fatturante_id, type("",(),{"ragione_sociale":"-"})()).ragione_sociale,
            "Imponibile": float(f.totale_imponibile), "IVA": float(f.totale_iva),
            "Totale": float(f.totale), "Stato": f.stato, "XML": "✓" if f.xml_generato else "—",
        } for f in fl])
        st.dataframe(df, use_container_width=True, hide_index=True,
            column_config={c: st.column_config.NumberColumn(format="€ %.2f") for c in ["Imponibile","IVA","Totale"]})
        st.markdown(f"**Totale {anno}: {format_currency(df['Totale'].sum())}**")

        # Azioni per singola fattura
        st.markdown("---")
        sel_fatt = st.selectbox("Seleziona fattura per azioni:", [f.id for f in fl],
            format_func=lambda i: next(f"N. {f.numero}/{f.anno} — {clienti.get(f.cliente_id, type('',(),{'denominazione':'-'})()).denominazione}" for f in fl if f.id == i))

        fatt = session.query(Fattura).get(sel_fatt)
        if fatt:
            righe = session.query(Prestazione).filter(Prestazione.fattura_id == fatt.id).all()
            cl = clienti.get(fatt.cliente_id)
            ft = fatturanti.get(fatt.fatturante_id)

            ac1, ac2, ac3, ac4 = st.columns(4)

            # Genera XML
            if ac1.button("📋 Genera XML", disabled=fatt.xml_generato, use_container_width=True):
                if cl and ft and righe:
                    xs, fn = genera_fattura_xml(fatt, righe, ft, cl)
                    fatt.xml_generato = True; fatt.xml_filename = fn; fatt.stato = "XML Generato"
                    session.commit()
                    st.download_button("⬇️ Scarica XML", xs, fn, "application/xml")

            # Genera PDF
            if ac2.button("📄 Genera PDF", use_container_width=True):
                if cl and ft and righe:
                    pdf = genera_fattura_pdf(fatt, righe, ft, cl)
                    st.download_button("⬇️ Scarica PDF", pdf,
                        f"Fattura_{fatt.numero}_{fatt.anno}.pdf", "application/pdf")

            # Invia email
            if ac3.button("📧 Invia per email", use_container_width=True):
                if cl and ft and righe:
                    pdf = genera_fattura_pdf(fatt, righe, ft, cl)
                    xml_str = None
                    if fatt.xml_generato and fatt.xml_filename:
                        xml_str, _ = genera_fattura_xml(fatt, righe, ft, cl)
                    ok, msg = invia_fattura_email(ft, cl, fatt, pdf_bytes=pdf, xml_str=xml_str)
                    if ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")

            # Genera massivo
            st.markdown("---")
            no_xml = [f for f in fl if not f.xml_generato]
            if no_xml:
                if st.button(f"📋 Genera XML per {len(no_xml)} fattura/e senza XML", type="primary"):
                    xl = []
                    for f in no_xml:
                        rr = session.query(Prestazione).filter(Prestazione.fattura_id == f.id).all()
                        c, ft2 = clienti.get(f.cliente_id), fatturanti.get(f.fatturante_id)
                        if c and ft2 and rr:
                            xs, fn = genera_fattura_xml(f, rr, ft2, c)
                            xl.append((xs, fn)); f.xml_generato = True; f.xml_filename = fn; f.stato = "XML Generato"
                    session.commit()
                    if len(xl) == 1:
                        st.download_button("⬇️ Scarica", xl[0][0], xl[0][1], "application/xml")
                    elif xl:
                        st.download_button(f"⬇️ ZIP ({len(xl)})", genera_zip_fatture(xl), f"fatture_{anno}.zip", "application/zip")
                    st.success(f"✅ {len(xl)} XML generati!")
    else:
        st.info(f"Nessuna fattura per {anno}.")
finally:
    session.close()
