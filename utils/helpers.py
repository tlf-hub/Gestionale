"""Funzioni di utilità condivise."""
from config import MESI, ROMAN_TRIMESTRI, ROMAN_SEMESTRI
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import locale

try:
    locale.setlocale(locale.LC_ALL, 'it_IT.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'it_IT')
    except locale.Error:
        pass


def format_currency(value):
    """Formatta un numero come valuta EUR."""
    if value is None:
        value = 0
    return f"€ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calc_periodicity_label(periodicita, data_inizio):
    """Calcola l'etichetta descrittiva in base alla periodicità."""
    if not data_inizio or not periodicita:
        return ""
    if isinstance(data_inizio, str):
        data_inizio = date.fromisoformat(data_inizio)
    m = data_inizio.month - 1  # 0-based index
    y = data_inizio.year
    if periodicita == "Mensile":
        return f" {MESI[m]} {y}"
    elif periodicita == "Trimestrale":
        return f" {ROMAN_TRIMESTRI[m]} trimestre {y}"
    elif periodicita == "Semestrale":
        return f" {ROMAN_SEMESTRI[m]} semestre {y}"
    elif periodicita == "Annuale":
        return f" {y}"
    return ""


def add_period(dt, periodicita):
    """Aggiunge un periodo alla data in base alla periodicità."""
    if isinstance(dt, str):
        dt = date.fromisoformat(dt)
    if periodicita == "Mensile":
        return dt + relativedelta(months=1)
    elif periodicita == "Trimestrale":
        return dt + relativedelta(months=3)
    elif periodicita == "Semestrale":
        return dt + relativedelta(months=6)
    elif periodicita == "Annuale":
        return dt + relativedelta(years=1)
    return dt


def get_next_fattura_number(session, fatturante_id, anno):
    """Restituisce il prossimo numero di fattura per un fatturante in un anno."""
    from models import Fattura
    from sqlalchemy import func
    result = session.query(func.max(Fattura.numero)).filter(
        Fattura.fatturante_id == fatturante_id,
        Fattura.anno == anno
    ).scalar()
    return (result or 0) + 1
