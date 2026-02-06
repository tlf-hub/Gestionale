"""
Generazione XML FatturaPA (versione 1.2.2) — Standard Agenzia delle Entrate.
Genera file XML conformi per l'invio tramite SDI.
"""
from lxml import etree
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import os
import zipfile
import io

NAMESPACE = "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
NSMAP = {"p": NAMESPACE}
SCHEMA_LOCATION = (
    "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2 "
    "http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/"
    "v1.2.2/Schema_del_file_FatturaPA_v1.2.2.xsd"
)

# Mappa regime fiscale
REGIME_MAP = {
    "Ordinario": "RF01",
    "Semplificato": "RF01",
    "Forfettario": "RF19",
}

# Mappa tipo documento
def get_tipo_documento(cliente):
    if cliente.split_payment:
        return "TD01"  # fattura con split payment
    return "TD01"  # fattura ordinaria


def _round2(val):
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _el(parent, tag, text=None, attrib=None):
    """Crea un sotto-elemento XML."""
    e = etree.SubElement(parent, tag, attrib or {})
    if text is not None:
        e.text = str(text)
    return e


def genera_fattura_xml(fattura, prestazioni, fatturante, cliente):
    """
    Genera l'XML FatturaPA per una singola fattura.
    
    Args:
        fattura: oggetto Fattura
        prestazioni: lista di oggetti Prestazione associati
        fatturante: oggetto SoggettoFatturante (cedente/prestatore)
        cliente: oggetto Cliente (cessionario/committente)
    
    Returns:
        str: contenuto XML come stringa
    """
    # Progressivo invio: codice fiscale fatturante + underscore + progressivo
    progressivo = f"{fatturante.partita_iva}_{fattura.numero:05d}"
    filename = f"IT{fatturante.partita_iva}_{fattura.numero:05d}.xml"

    root = etree.Element(
        "{%s}FatturaElettronica" % NAMESPACE,
        nsmap={"p": NAMESPACE},
        attrib={
            "versione": "FPR12",
            "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": SCHEMA_LOCATION,
        },
    )

    # =========================================================================
    # HEADER
    # =========================================================================
    header = _el(root, "FatturaElettronicaHeader")

    # --- DatiTrasmissione ---
    dati_trasm = _el(header, "DatiTrasmissione")
    id_trasm = _el(dati_trasm, "IdTrasmittente")
    _el(id_trasm, "IdPaese", "IT")
    _el(id_trasm, "IdCodice", fatturante.partita_iva)
    _el(dati_trasm, "ProgressivoInvio", f"{fattura.numero:05d}")
    _el(dati_trasm, "FormatoTrasmissione", "FPR12")
    _el(dati_trasm, "CodiceDestinatario", cliente.codice_sdi or "0000000")
    if cliente.pec and (not cliente.codice_sdi or cliente.codice_sdi == "0000000"):
        _el(dati_trasm, "PECDestinatario", cliente.pec)

    # --- CedentePrestatore ---
    ced = _el(header, "CedentePrestatore")
    dati_anag_ced = _el(ced, "DatiAnagrafici")
    id_fiscale_ced = _el(dati_anag_ced, "IdFiscaleIVA")
    _el(id_fiscale_ced, "IdPaese", fatturante.paese or "IT")
    _el(id_fiscale_ced, "IdCodice", fatturante.partita_iva)
    if fatturante.codice_fiscale:
        _el(dati_anag_ced, "CodiceFiscale", fatturante.codice_fiscale)
    anag_ced = _el(dati_anag_ced, "Anagrafica")
    _el(anag_ced, "Denominazione", fatturante.ragione_sociale)
    _el(dati_anag_ced, "RegimeFiscale", REGIME_MAP.get(fatturante.regime_fiscale, "RF01"))

    sede_ced = _el(ced, "Sede")
    _el(sede_ced, "Indirizzo", fatturante.indirizzo)
    _el(sede_ced, "CAP", fatturante.cap)
    _el(sede_ced, "Comune", fatturante.citta)
    _el(sede_ced, "Provincia", fatturante.provincia)
    _el(sede_ced, "Nazione", fatturante.paese or "IT")

    # --- CessionarioCommittente ---
    cess = _el(header, "CessionarioCommittente")
    dati_anag_cess = _el(cess, "DatiAnagrafici")
    if cliente.partita_iva:
        id_fiscale_cess = _el(dati_anag_cess, "IdFiscaleIVA")
        _el(id_fiscale_cess, "IdPaese", cliente.paese or "IT")
        _el(id_fiscale_cess, "IdCodice", cliente.partita_iva)
    if cliente.codice_fiscale:
        _el(dati_anag_cess, "CodiceFiscale", cliente.codice_fiscale)
    anag_cess = _el(dati_anag_cess, "Anagrafica")
    if cliente.nome:
        _el(anag_cess, "Nome", cliente.nome)
        _el(anag_cess, "Cognome", cliente.cognome_ragione_sociale)
    else:
        _el(anag_cess, "Denominazione", cliente.cognome_ragione_sociale)

    sede_cess = _el(cess, "Sede")
    _el(sede_cess, "Indirizzo", cliente.indirizzo or "N/D")
    _el(sede_cess, "CAP", cliente.cap or "00000")
    _el(sede_cess, "Comune", cliente.citta or "N/D")
    if cliente.provincia:
        _el(sede_cess, "Provincia", cliente.provincia)
    _el(sede_cess, "Nazione", cliente.paese or "IT")

    # =========================================================================
    # BODY
    # =========================================================================
    body = _el(root, "FatturaElettronicaBody")

    # --- DatiGenerali ---
    dati_gen = _el(body, "DatiGenerali")
    dati_gen_doc = _el(dati_gen, "DatiGeneraliDocumento")
    _el(dati_gen_doc, "TipoDocumento", get_tipo_documento(cliente))
    _el(dati_gen_doc, "Divisa", "EUR")
    _el(dati_gen_doc, "Data", fattura.data.isoformat())
    _el(dati_gen_doc, "Numero", str(fattura.numero))

    # --- DatiBeniServizi ---
    dati_beni = _el(body, "DatiBeniServizi")

    # Raggruppa per aliquota IVA per il riepilogo
    riepilogo_iva = {}
    for i, prest in enumerate(prestazioni, 1):
        det = _el(dati_beni, "DettaglioLinee")
        _el(det, "NumeroLinea", str(i))
        desc = prest.descrizione
        from utils.helpers import calc_periodicity_label
        desc += calc_periodicity_label(prest.periodicita, prest.data_inizio)
        _el(det, "Descrizione", desc)
        _el(det, "PrezzoUnitario", str(_round2(prest.importo_unitario)))
        _el(det, "PrezzoTotale", str(_round2(prest.importo_unitario)))
        _el(det, "AliquotaIVA", f"{prest.aliquota_iva:.2f}")

        aliq = prest.aliquota_iva
        if aliq not in riepilogo_iva:
            riepilogo_iva[aliq] = {"imponibile": Decimal("0"), "imposta": Decimal("0")}
        riepilogo_iva[aliq]["imponibile"] += _round2(prest.importo_unitario)
        riepilogo_iva[aliq]["imposta"] += _round2(float(prest.importo_unitario) * aliq / 100)

    for aliq, valori in sorted(riepilogo_iva.items()):
        riepilogo = _el(dati_beni, "DatiRiepilogo")
        _el(riepilogo, "AliquotaIVA", f"{aliq:.2f}")
        _el(riepilogo, "ImponibileImporto", str(_round2(valori["imponibile"])))
        _el(riepilogo, "Imposta", str(_round2(valori["imposta"])))
        _el(riepilogo, "EsigibilitaIVA", "S" if cliente.split_payment else "I")
        if aliq == 0:
            _el(riepilogo, "Natura", "N2.2")

    # --- DatiPagamento ---
    dati_pag = _el(body, "DatiPagamento")
    _el(dati_pag, "CondizioniPagamento", "TP02")  # pagamento completo
    det_pag = _el(dati_pag, "DettaglioPagamento")
    _el(det_pag, "ModalitaPagamento", "MP05" if cliente.modalita_incasso == "SDD SEPA" else "MP05")
    importo_totale = sum(
        _round2(float(p.importo_unitario) * (1 + p.aliquota_iva / 100))
        for p in prestazioni
    )
    _el(det_pag, "ImportoPagamento", str(_round2(importo_totale)))
    if fatturante.iban:
        _el(det_pag, "IBAN", fatturante.iban.replace(" ", ""))

    # Serializza
    xml_str = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", pretty_print=True
    ).decode("utf-8")

    return xml_str, filename


def genera_zip_fatture(fatture_xml_list):
    """
    Crea un file ZIP contenente più XML di fatture.
    
    Args:
        fatture_xml_list: lista di tuple (xml_string, filename)
    
    Returns:
        bytes: contenuto del file ZIP
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for xml_str, filename in fatture_xml_list:
            zf.writestr(filename, xml_str)
    buffer.seek(0)
    return buffer.getvalue()
