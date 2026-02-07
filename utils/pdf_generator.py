"""Generazione PDF fattura di cortesia con logo."""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from decimal import Decimal, ROUND_HALF_UP
from utils.helpers import calc_periodicity_label


def _r2(val):
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def genera_fattura_pdf(fattura, prestazioni, fatturante, cliente):
    """Genera un PDF di cortesia per la fattura. Ritorna bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm,
                            leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    elements = []

    # Stili custom
    sn = ParagraphStyle("sn", parent=styles["Normal"], fontSize=9, leading=12)
    sb = ParagraphStyle("sb", parent=styles["Normal"], fontSize=9, leading=12, fontName="Helvetica-Bold")
    sc = ParagraphStyle("sc", parent=styles["Normal"], fontSize=9, leading=12, alignment=TA_CENTER)
    sr = ParagraphStyle("sr", parent=styles["Normal"], fontSize=9, leading=12, alignment=TA_RIGHT)
    stitle = ParagraphStyle("stitle", parent=styles["Normal"], fontSize=14, leading=18,
                            fontName="Helvetica-Bold", textColor=colors.HexColor("#1e293b"))

    # === HEADER con logo ===
    header_data = []
    logo_cell = ""
    if fatturante.logo:
        try:
            logo_buf = io.BytesIO(fatturante.logo)
            logo_img = Image(logo_buf, width=40*mm, height=20*mm)
            logo_img.hAlign = "LEFT"
            logo_cell = logo_img
        except Exception:
            logo_cell = ""

    fatt_info = f"""<b>{fatturante.ragione_sociale}</b><br/>
    {fatturante.indirizzo} — {fatturante.cap} {fatturante.citta} ({fatturante.provincia})<br/>
    P.IVA: {fatturante.partita_iva} — C.F.: {fatturante.codice_fiscale}<br/>
    PEC: {fatturante.pec}"""

    header_data = [[logo_cell, Paragraph(fatt_info, sn)]]
    ht = Table(header_data, colWidths=[45*mm, 135*mm])
    ht.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(ht)
    elements.append(Spacer(1, 8*mm))

    # === TITOLO ===
    elements.append(Paragraph(f"FATTURA N. {fattura.numero}/{fattura.anno}", stitle))
    elements.append(Paragraph(f"Data: {fattura.data.strftime('%d/%m/%Y')}", sn))
    elements.append(Spacer(1, 5*mm))

    # === DESTINATARIO ===
    cl_info = f"""<b>Spett.le</b><br/>
    <b>{cliente.denominazione}</b><br/>
    {cliente.indirizzo}<br/>
    {cliente.cap} {cliente.citta} ({cliente.provincia})<br/>
    P.IVA: {cliente.partita_iva} — C.F.: {cliente.codice_fiscale}"""
    dest_t = Table([[Paragraph(cl_info, sn)]], colWidths=[90*mm])
    dest_t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(dest_t)
    elements.append(Spacer(1, 8*mm))

    # === RIGHE PRESTAZIONI ===
    data = [["N.", "Descrizione", "Importo", "IVA %", "Totale"]]
    tot_imp = Decimal("0")
    riepilogo_iva = {}

    for i, p in enumerate(prestazioni, 1):
        desc = p.descrizione + calc_periodicity_label(p.periodicita, p.data_inizio)
        imp = _r2(p.importo_unitario)
        iva_amt = _r2(float(p.importo_unitario) * p.aliquota_iva / 100)
        tot_riga = imp + iva_amt
        tot_imp += imp
        riepilogo_iva.setdefault(p.aliquota_iva, {"imp": Decimal("0"), "iva": Decimal("0")})
        riepilogo_iva[p.aliquota_iva]["imp"] += imp
        riepilogo_iva[p.aliquota_iva]["iva"] += iva_amt

        data.append([
            Paragraph(str(i), sc),
            Paragraph(desc, sn),
            Paragraph(f"€ {imp:,.2f}".replace(",", "."), sr),
            Paragraph(f"{p.aliquota_iva}%", sc),
            Paragraph(f"€ {tot_riga:,.2f}".replace(",", "."), sr),
        ])

    t = Table(data, colWidths=[12*mm, 90*mm, 28*mm, 18*mm, 32*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f9ff")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 5*mm))

    # === RIEPILOGO IVA ===
    riep_data = [["Aliquota", "Imponibile", "Imposta"]]
    tot_iva_tot = Decimal("0")
    for aliq in sorted(riepilogo_iva.keys()):
        v = riepilogo_iva[aliq]
        tot_iva_tot += v["iva"]
        riep_data.append([f"{aliq}%", f"€ {v['imp']:,.2f}".replace(",", "."),
                          f"€ {v['iva']:,.2f}".replace(",", ".")])

    gran_totale = tot_imp + tot_iva_tot
    riep_data.append(["", Paragraph("<b>TOTALE FATTURA</b>", sr),
                       Paragraph(f"<b>€ {gran_totale:,.2f}</b>".replace(",", "."), sr)])

    rt = Table(riep_data, colWidths=[30*mm, 50*mm, 50*mm])
    rt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(rt)
    elements.append(Spacer(1, 8*mm))

    # === PAGAMENTO ===
    if fatturante.iban:
        elements.append(Paragraph(f"<b>Modalità di pagamento:</b> Bonifico bancario", sn))
        elements.append(Paragraph(f"IBAN: {fatturante.iban}", sn))

    elements.append(Spacer(1, 5*mm))
    elements.append(Paragraph("<i>Documento di cortesia — la fattura originale è in formato elettronico (XML).</i>",
                              ParagraphStyle("foot", parent=sn, fontSize=7, textColor=colors.grey)))

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()
