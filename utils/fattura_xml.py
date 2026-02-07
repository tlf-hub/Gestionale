"""Generazione XML FatturaPA (versione 1.2.2)."""
from lxml import etree
from decimal import Decimal, ROUND_HALF_UP
import zipfile, io

NAMESPACE = "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
SCHEMA_LOCATION = (
    "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2 "
    "http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/"
    "v1.2.2/Schema_del_file_FatturaPA_v1.2.2.xsd"
)
REGIME_MAP = {"Ordinario": "RF01", "Semplificato": "RF01", "Forfettario": "RF19"}


def _r2(val):
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _el(parent, tag, text=None):
    e = etree.SubElement(parent, tag)
    if text is not None:
        e.text = str(text)
    return e


def genera_fattura_xml(fattura, prestazioni, fatturante, cliente):
    filename = f"IT{fatturante.partita_iva}_{fattura.numero:05d}.xml"
    root = etree.Element(
        "{%s}FatturaElettronica" % NAMESPACE,
        nsmap={"p": NAMESPACE},
        attrib={"versione": "FPR12",
                "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": SCHEMA_LOCATION},
    )
    header = _el(root, "FatturaElettronicaHeader")
    dt = _el(header, "DatiTrasmissione")
    idt = _el(dt, "IdTrasmittente")
    _el(idt, "IdPaese", "IT"); _el(idt, "IdCodice", fatturante.partita_iva)
    _el(dt, "ProgressivoInvio", f"{fattura.numero:05d}")
    _el(dt, "FormatoTrasmissione", "FPR12")
    _el(dt, "CodiceDestinatario", cliente.codice_sdi or "0000000")
    if cliente.pec and (not cliente.codice_sdi or cliente.codice_sdi == "0000000"):
        _el(dt, "PECDestinatario", cliente.pec)

    ced = _el(header, "CedentePrestatore")
    da_c = _el(ced, "DatiAnagrafici")
    idf = _el(da_c, "IdFiscaleIVA")
    _el(idf, "IdPaese", fatturante.paese or "IT"); _el(idf, "IdCodice", fatturante.partita_iva)
    if fatturante.codice_fiscale: _el(da_c, "CodiceFiscale", fatturante.codice_fiscale)
    an = _el(da_c, "Anagrafica"); _el(an, "Denominazione", fatturante.ragione_sociale)
    _el(da_c, "RegimeFiscale", REGIME_MAP.get(fatturante.regime_fiscale, "RF01"))
    sede = _el(ced, "Sede")
    _el(sede, "Indirizzo", fatturante.indirizzo or "N/D")
    _el(sede, "CAP", fatturante.cap or "00000")
    _el(sede, "Comune", fatturante.citta or "N/D")
    if fatturante.provincia: _el(sede, "Provincia", fatturante.provincia)
    _el(sede, "Nazione", fatturante.paese or "IT")

    cess = _el(header, "CessionarioCommittente")
    da_cl = _el(cess, "DatiAnagrafici")
    if cliente.partita_iva:
        idf2 = _el(da_cl, "IdFiscaleIVA")
        _el(idf2, "IdPaese", cliente.paese or "IT"); _el(idf2, "IdCodice", cliente.partita_iva)
    if cliente.codice_fiscale: _el(da_cl, "CodiceFiscale", cliente.codice_fiscale)
    an2 = _el(da_cl, "Anagrafica")
    if cliente.nome:
        _el(an2, "Nome", cliente.nome); _el(an2, "Cognome", cliente.cognome_ragione_sociale)
    else:
        _el(an2, "Denominazione", cliente.cognome_ragione_sociale)
    sede2 = _el(cess, "Sede")
    _el(sede2, "Indirizzo", cliente.indirizzo or "N/D")
    _el(sede2, "CAP", cliente.cap or "00000")
    _el(sede2, "Comune", cliente.citta or "N/D")
    if cliente.provincia: _el(sede2, "Provincia", cliente.provincia)
    _el(sede2, "Nazione", cliente.paese or "IT")

    body = _el(root, "FatturaElettronicaBody")
    dg = _el(body, "DatiGenerali")
    dgd = _el(dg, "DatiGeneraliDocumento")
    _el(dgd, "TipoDocumento", "TD01"); _el(dgd, "Divisa", "EUR")
    _el(dgd, "Data", fattura.data.isoformat()); _el(dgd, "Numero", str(fattura.numero))

    dbs = _el(body, "DatiBeniServizi")
    riepilogo_iva = {}
    from utils.helpers import calc_periodicity_label
    for i, p in enumerate(prestazioni, 1):
        det = _el(dbs, "DettaglioLinee")
        _el(det, "NumeroLinea", str(i))
        desc = p.descrizione + calc_periodicity_label(p.periodicita, p.data_inizio)
        _el(det, "Descrizione", desc)
        _el(det, "PrezzoUnitario", str(_r2(p.importo_unitario)))
        _el(det, "PrezzoTotale", str(_r2(p.importo_unitario)))
        _el(det, "AliquotaIVA", f"{p.aliquota_iva:.2f}")
        aliq = p.aliquota_iva
        riepilogo_iva.setdefault(aliq, {"imp": Decimal("0"), "iva": Decimal("0")})
        riepilogo_iva[aliq]["imp"] += _r2(p.importo_unitario)
        riepilogo_iva[aliq]["iva"] += _r2(float(p.importo_unitario) * aliq / 100)

    for aliq, v in sorted(riepilogo_iva.items()):
        r = _el(dbs, "DatiRiepilogo")
        _el(r, "AliquotaIVA", f"{aliq:.2f}")
        _el(r, "ImponibileImporto", str(_r2(v["imp"])))
        _el(r, "Imposta", str(_r2(v["iva"])))
        _el(r, "EsigibilitaIVA", "S" if cliente.split_payment else "I")
        if aliq == 0: _el(r, "Natura", "N2.2")

    dp = _el(body, "DatiPagamento"); _el(dp, "CondizioniPagamento", "TP02")
    ddp = _el(dp, "DettaglioPagamento"); _el(ddp, "ModalitaPagamento", "MP05")
    tot = sum(_r2(float(p.importo_unitario) * (1 + p.aliquota_iva / 100)) for p in prestazioni)
    _el(ddp, "ImportoPagamento", str(_r2(tot)))
    if fatturante.iban: _el(ddp, "IBAN", fatturante.iban.replace(" ", ""))

    xml_str = etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True).decode()
    return xml_str, filename


def genera_zip_fatture(fatture_xml_list):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for xml_str, fname in fatture_xml_list:
            zf.writestr(fname, xml_str)
    buf.seek(0)
    return buf.getvalue()
