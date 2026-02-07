"""Generazione XML SDD SEPA — Standard ISO 20022 pain.008.001.02"""
from lxml import etree
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import uuid

NS = "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02"

def _r2(val):
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _el(parent, tag, text=None):
    e = etree.SubElement(parent, tag)
    if text is not None: e.text = str(text)
    return e


def genera_sdd_xml(fatturante, incassi_list, data_esecuzione=None):
    if data_esecuzione is None:
        data_esecuzione = date.today()

    msg_id = f"MSG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
    pmt_id = f"PMT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"

    root = etree.Element("Document", nsmap={None: NS})
    cstmr = _el(root, "CstmrDrctDbtInitn")

    gh = _el(cstmr, "GrpHdr")
    _el(gh, "MsgId", msg_id)
    _el(gh, "CreDtTm", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))
    _el(gh, "NbOfTxs", str(len(incassi_list)))
    ctrl = sum(_r2(i["importo"]) for i in incassi_list)
    _el(gh, "CtrlSum", str(ctrl))
    ip = _el(gh, "InitgPty"); _el(ip, "Nm", fatturante.ragione_sociale[:70])

    pi = _el(cstmr, "PmtInf")
    _el(pi, "PmtInfId", pmt_id); _el(pi, "PmtMtd", "DD"); _el(pi, "BtchBookg", "true")
    _el(pi, "NbOfTxs", str(len(incassi_list))); _el(pi, "CtrlSum", str(ctrl))

    pti = _el(pi, "PmtTpInf")
    sl = _el(pti, "SvcLvl"); _el(sl, "Cd", "SEPA")
    li = _el(pti, "LclInstrm"); _el(li, "Cd", "CORE")
    _el(pti, "SeqTp", "RCUR")
    _el(pi, "ReqdColltnDt", data_esecuzione.isoformat())

    cdtr = _el(pi, "Cdtr"); _el(cdtr, "Nm", fatturante.ragione_sociale[:70])
    ca = _el(pi, "CdtrAcct"); caid = _el(ca, "Id")
    _el(caid, "IBAN", fatturante.iban.replace(" ", ""))
    cag = _el(pi, "CdtrAgt"); fi = _el(cag, "FinInstnId"); _el(fi, "BIC", "NOTPROVIDED")

    csi = _el(pi, "CdtrSchmeId"); csid = _el(csi, "Id")
    pv = _el(csid, "PrvtId"); ot = _el(pv, "Othr")
    _el(ot, "Id", f"IT{fatturante.codice_fiscale}ZZZ")
    sn = _el(ot, "SchmeNm"); _el(sn, "Prtry", "SEPA")

    for inc in incassi_list:
        cl = inc["cliente"]
        importo = _r2(inc["importo"])
        e2e = inc.get("end_to_end_id", f"E2E-{uuid.uuid4().hex[:12].upper()}")

        dd = _el(pi, "DrctDbtTxInf")
        pid = _el(dd, "PmtId"); _el(pid, "EndToEndId", e2e[:35])
        amt = _el(dd, "InstdAmt", str(importo)); amt.set("Ccy", "EUR")

        ddt = _el(dd, "DrctDbtTx"); mri = _el(ddt, "MndtRltdInf")
        _el(mri, "MndtId", cl.rif_mandato_sdd or f"MAND-{cl.id}")
        _el(mri, "DtOfSgntr",
            cl.data_mandato_sdd.isoformat() if cl.data_mandato_sdd else date.today().isoformat())

        dbtr = _el(dd, "Dbtr"); _el(dbtr, "Nm", cl.denominazione[:70])
        da = _el(dd, "DbtrAcct"); dai = _el(da, "Id"); _el(dai, "IBAN", cl.iban_sdd.replace(" ", ""))
        dag = _el(dd, "DbtrAgt"); dfi = _el(dag, "FinInstnId"); _el(dfi, "BIC", "NOTPROVIDED")
        ri = _el(dd, "RmtInf"); _el(ri, "Ustrd", inc.get("prestazione_descrizione", "Pagamento")[:140])

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True).decode()
