"""Invio email con allegati (fatture PDF/XML)."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


def invia_fattura_email(fatturante, cliente, fattura, pdf_bytes=None, xml_str=None):
    """
    Invia fattura via email. Richiede che il fatturante abbia SMTP configurato.
    Ritorna (success: bool, message: str).
    """
    if not fatturante.smtp_host or not fatturante.smtp_user:
        return False, "SMTP non configurato per questo fatturante."

    dest = cliente.pec or cliente.mail
    if not dest:
        return False, f"Nessun indirizzo email per {cliente.denominazione}."

    msg = MIMEMultipart()
    msg["From"] = fatturante.smtp_from or fatturante.smtp_user
    msg["To"] = dest
    msg["Subject"] = f"Fattura n. {fattura.numero}/{fattura.anno} — {fatturante.ragione_sociale}"

    body = f"""Gentile {cliente.denominazione},

in allegato la fattura n. {fattura.numero}/{fattura.anno} del {fattura.data.strftime('%d/%m/%Y')}.

Totale: € {float(fattura.totale):,.2f}

Cordiali saluti,
{fatturante.ragione_sociale}
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if pdf_bytes:
        att = MIMEApplication(pdf_bytes, _subtype="pdf")
        att.add_header("Content-Disposition", "attachment",
                       filename=f"Fattura_{fattura.numero}_{fattura.anno}.pdf")
        msg.attach(att)

    if xml_str:
        att = MIMEApplication(xml_str.encode("utf-8"), _subtype="xml")
        att.add_header("Content-Disposition", "attachment",
                       filename=f"IT{fatturante.partita_iva}_{fattura.numero:05d}.xml")
        msg.attach(att)

    try:
        with smtplib.SMTP(fatturante.smtp_host, fatturante.smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(fatturante.smtp_user, fatturante.smtp_password)
            server.send_message(msg)
        return True, f"Email inviata a {dest}"
    except Exception as e:
        return False, f"Errore invio: {e}"
