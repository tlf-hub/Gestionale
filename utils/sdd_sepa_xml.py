"""
Generazione XML SDD SEPA — Standard ISO 20022 pain.008.001.02
Genera file XML per addebiti diretti da caricare sull'home banking.
"""
from lxml import etree
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import io
import uuid

NS = "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02"
NSMAP = {None: NS}


def _round2(val):
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _el(parent, tag, text=None):
    e = etree.SubElement(parent, tag)
    if text is not None:
        e.text = str(text)
    return e


def genera_sdd_xml(fatturante, incassi_list, data_esecuzione=None):
    """
    Genera il file XML SDD SEPA pain.008.001.02.
    
    Args:
        fatturante: oggetto SoggettoFatturante (creditore)
        incassi_list: lista di dict con:
            - cliente: oggetto Cliente (debitore)
            - importo: Decimal
            - prestazione_descrizione: str
            - end_to_end_id: str
        data_esecuzione: date (default: oggi + 5 giorni lavorativi)
    
    Returns:
        str: contenuto XML come stringa
    """
    if data_esecuzione is None:
        data_esecuzione = date.today()

    msg_id = f"MSG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
    pmt_inf_id = f"PMT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"

    root = etree.Element("Document", nsmap=NSMAP)
    cstmr = _el(root, "CstmrDrctDbtInitn")

    # =========================================================================
    # Group Header
    # =========================================================================
    grp_hdr = _el(cstmr, "GrpHdr")
    _el(grp_hdr, "MsgId", msg_id)
    _el(grp_hdr, "CreDtTm", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))
    _el(grp_hdr, "NbOfTxs", str(len(incassi_list)))
    ctrl_sum = sum(_round2(i["importo"]) for i in incassi_list)
    _el(grp_hdr, "CtrlSum", str(ctrl_sum))
    init_pty = _el(grp_hdr, "InitgPty")
    _el(init_pty, "Nm", fatturante.ragione_sociale[:70])

    # =========================================================================
    # Payment Information
    # =========================================================================
    pmt_inf = _el(cstmr, "PmtInf")
    _el(pmt_inf, "PmtInfId", pmt_inf_id)
    _el(pmt_inf, "PmtMtd", "DD")  # Direct Debit

    # Batch booking
    _el(pmt_inf, "BtchBookg", "true")
    _el(pmt_inf, "NbOfTxs", str(len(incassi_list)))
    _el(pmt_inf, "CtrlSum", str(ctrl_sum))

    # Payment Type Information
    pmt_tp_inf = _el(pmt_inf, "PmtTpInf")
    svc_lvl = _el(pmt_tp_inf, "SvcLvl")
    _el(svc_lvl, "Cd", "SEPA")
    lcl_instrm = _el(pmt_tp_inf, "LclInstrm")
    _el(lcl_instrm, "Cd", "CORE")  # CORE per privati, B2B per aziende
    _el(pmt_tp_inf, "SeqTp", "RCUR")  # Recurring

    # Data esecuzione richiesta
    _el(pmt_inf, "ReqdColltnDt", data_esecuzione.isoformat())

    # Creditore (Fatturante)
    cdtr = _el(pmt_inf, "Cdtr")
    _el(cdtr, "Nm", fatturante.ragione_sociale[:70])
    cdtr_addr = _el(cdtr, "PstlAdr")
    _el(cdtr_addr, "Ctry", fatturante.paese or "IT")

    # IBAN Creditore
    cdtr_acct = _el(pmt_inf, "CdtrAcct")
    cdtr_acct_id = _el(cdtr_acct, "Id")
    _el(cdtr_acct_id, "IBAN", fatturante.iban.replace(" ", ""))

    # BIC Creditore (agent)
    cdtr_agt = _el(pmt_inf, "CdtrAgt")
    fin_instn = _el(cdtr_agt, "FinInstnId")
    _el(fin_instn, "BIC", "NOTPROVIDED")  # BIC opzionale in SEPA

    # Creditor Scheme Identification
    cdtr_schm_id = _el(pmt_inf, "CdtrSchmeId")
    cdtr_schm_id_inner = _el(cdtr_schm_id, "Id")
    prvt_id = _el(cdtr_schm_id_inner, "PrvtId")
    othr = _el(prvt_id, "Othr")
    _el(othr, "Id", f"IT{fatturante.codice_fiscale}ZZZ")
    schm_nm = _el(othr, "SchmeNm")
    _el(schm_nm, "Prtry", "SEPA")

    # =========================================================================
    # Transazioni (una per ogni incasso/debitore)
    # =========================================================================
    for inc in incassi_list:
        cliente = inc["cliente"]
        importo = _round2(inc["importo"])
        e2e_id = inc.get("end_to_end_id", f"E2E-{uuid.uuid4().hex[:12].upper()}")

        drct_dbt = _el(pmt_inf, "DrctDbtTxInf")

        # Payment ID
        pmt_id = _el(drct_dbt, "PmtId")
        _el(pmt_id, "EndToEndId", e2e_id[:35])

        # Importo
        amt = _el(drct_dbt, "InstdAmt", str(importo))
        amt.set("Ccy", "EUR")

        # Mandato
        drct_dbt_tx = _el(drct_dbt, "DrctDbtTx")
        mndt_rltd_inf = _el(drct_dbt_tx, "MndtRltdInf")
        _el(mndt_rltd_inf, "MndtId", cliente.rif_mandato_sdd or f"MAND-{cliente.id}")
        _el(mndt_rltd_inf, "DtOfSgntr",
            cliente.data_mandato_sdd.isoformat() if cliente.data_mandato_sdd else date.today().isoformat())

        # Debitore
        dbtr = _el(drct_dbt, "Dbtr")
        _el(dbtr, "Nm", cliente.denominazione[:70])

        # IBAN Debitore
        dbtr_acct = _el(drct_dbt, "DbtrAcct")
        dbtr_acct_id = _el(dbtr_acct, "Id")
        _el(dbtr_acct_id, "IBAN", cliente.iban_sdd.replace(" ", ""))

        # BIC Debitore
        dbtr_agt = _el(drct_dbt, "DbtrAgt")
        dbtr_fin = _el(dbtr_agt, "FinInstnId")
        _el(dbtr_fin, "BIC", "NOTPROVIDED")

        # Remittance info (causale)
        rmt_inf = _el(drct_dbt, "RmtInf")
        _el(rmt_inf, "Ustrd", inc.get("prestazione_descrizione", "Pagamento")[:140])

    # Serializza
    xml_str = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", pretty_print=True
    ).decode("utf-8")

    return xml_str
