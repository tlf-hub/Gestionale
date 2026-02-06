"""📄 Fatture — Elenco fatture emesse e generazione XML FatturaPA."""
import streamlit as st
import pandas as pd
from datetime import date
from database import get_session, init_db
from models import Fattura, Prestazione, Cliente, SoggettoFatturante
from utils.helpers import format_currency
from utils.fattura_xml import genera_fattura_xml, genera_zip_fatture

st.set_page_config(page_title="Fatture", page_icon="📄", layout="wide")
init_db()
st.markdown("## 📄 Fatture Emesse")

session = get_session()
try:
    clienti = {c.id: c for c in session.query(Cliente).all()}
    fatturanti = {f.id: f for f in session.query(SoggettoFatturante).all()}

    # Filtri
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_anno = st.number_input("Anno", min_value=2020, max_value=2030, value=date.today().year)
    with fc2:
        f_stato = st.selectbox("Stato", ["Tutti","Emessa","XML Generato","Inviata a SDI","Accettata","Rifiutata"])
    with fc3:
        f_fatt = st.selectbox("Fatturante", ["Tutti"] + [f.ragione_sociale for f in fatturanti.values()])

    query = session.query(Fattura).filter(Fattura.anno == f_anno)
    if f_stato != "Tutti":
        query = query.filter(Fattura.stato == f_stato)
    if f_fatt != "Tutti":
        fid = next((f.id for f in fatturanti.values() if f.ragione_sociale == f_fatt), None)
        if fid:
            query = query.filter(Fattura.fatturante_id == fid)

    fatture_list = query.order_by(Fattura.numero.desc()).all()

    if fatture_list:
        st.caption(f"{len(fatture_list)} fatture trovate")
        rows = []
        for f in fatture_list:
            cl = clienti.get(f.cliente_id)
            ft = fatturanti.get(f.fatturante_id)
            rows.append({
                "N.": f.numero, "Anno": f.anno,
                "Data": f.data.strftime("%d/%m/%Y") if f.data else "",
                "Cliente": cl.denominazione if cl else "N/D",
                "Fatturante": ft.ragione_sociale if ft else "N/D",
                "Imponibile": float(f.totale_imponibile),
                "IVA": float(f.totale_iva),
                "Totale": float(f.totale),
                "Stato": f.stato,
                "XML": "✓" if f.xml_generato else "—",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
            column_config={
                "Imponibile": st.column_config.NumberColumn(format="€ %.2f"),
                "IVA": st.column_config.NumberColumn(format="€ %.2f"),
                "Totale": st.column_config.NumberColumn(format="€ %.2f"),
            })

        # Totali
        tot = sum(r["Totale"] for r in rows)
        st.markdown(f"**Totale fatturato {f_anno}: {format_currency(tot)}**")

        # Genera XML per fatture senza XML
        st.markdown("---")
        st.markdown("#### 📋 Genera Tracciato XML FatturaPA")
        fatture_no_xml = [f for f in fatture_list if not f.xml_generato]
        if fatture_no_xml:
            st.info(f"{len(fatture_no_xml)} fattura/e senza XML generato.")
            if st.button("📋 Genera XML per tutte", type="primary"):
                xml_list = []
                for f in fatture_no_xml:
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
                    st.download_button("⬇️ Scarica XML", data=xml_list[0][0],
                        file_name=xml_list[0][1], mime="application/xml")
                elif len(xml_list) > 1:
                    from utils.fattura_xml import genera_zip_fatture
                    zip_data = genera_zip_fatture(xml_list)
                    st.download_button(f"⬇️ Scarica {len(xml_list)} fatture (ZIP)",
                        data=zip_data, file_name=f"fatture_{f_anno}.zip", mime="application/zip")
                st.success(f"✅ XML generato per {len(xml_list)} fattura/e!")
        else:
            st.success("Tutte le fatture hanno già l'XML generato.")
    else:
        st.info(f"Nessuna fattura trovata per {f_anno}. Usa la Dashboard per emettere fatture.")
finally:
    session.close()
