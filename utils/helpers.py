"""Funzioni di utilità condivise."""
from config import MESI, ROMAN_TRIMESTRI, ROMAN_SEMESTRI
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import re


def format_currency(value):
    if value is None:
        value = 0
    return f"€ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calc_periodicity_label(periodicita, data_inizio):
    if not data_inizio or not periodicita:
        return ""
    if isinstance(data_inizio, str):
        data_inizio = date.fromisoformat(data_inizio)
    m = data_inizio.month - 1
    y = data_inizio.year
    if periodicita == "Mensile":
        return f" {MESI[m]} {y}"
    elif periodicita == "Trimestrale":
        return f" {ROMAN_TRIMESTRI[m]} trim. {y}"
    elif periodicita == "Semestrale":
        return f" {ROMAN_SEMESTRI[m]} sem. {y}"
    elif periodicita == "Annuale":
        return f" {y}"
    return ""


def add_period(dt, periodicita):
    if isinstance(dt, str):
        dt = date.fromisoformat(dt)
    deltas = {
        "Mensile": relativedelta(months=1),
        "Trimestrale": relativedelta(months=3),
        "Semestrale": relativedelta(months=6),
        "Annuale": relativedelta(years=1),
    }
    return dt + deltas.get(periodicita, relativedelta())


def get_next_fattura_number(session, fatturante_id, anno):
    from models import Fattura
    from sqlalchemy import func
    result = session.query(func.max(Fattura.numero)).filter(
        Fattura.fatturante_id == fatturante_id,
        Fattura.anno == anno
    ).scalar()
    return (result or 0) + 1


def parse_date_filter(text):
    """
    Parsa un filtro data testuale. Ritorna un dict con le info per filtrare.
    Formati supportati:
      - "2026" → anno=2026
      - "02/2026" o "2/2026" → mese=2, anno=2026
      - "febbraio 2026" → mese=2, anno=2026
      - "15/02/2026" → data esatta
      - ">15/02/2026" → dopo data
      - "<15/02/2026" → prima di data
      - "15/02/2026-28/02/2026" → range
      - "*/2/2026" → mese=2, anno=2026
    Ritorna: dict con tipo ("anno","mese_anno","data","dopo","prima","range") e valori.
    """
    if not text or not text.strip():
        return None
    text = text.strip().lower()
    mesi_map = {m.lower(): i + 1 for i, m in enumerate(MESI)}

    # Range: data1-data2
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})\s*[-–]\s*(\d{1,2})/(\d{1,2})/(\d{4})$', text)
    if m:
        try:
            d1 = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            d2 = date(int(m.group(6)), int(m.group(5)), int(m.group(4)))
            return {"tipo": "range", "da": d1, "a": d2}
        except ValueError:
            return None

    # > data
    m = re.match(r'^>\s*(\d{1,2})/(\d{1,2})/(\d{4})$', text)
    if m:
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return {"tipo": "dopo", "data": d}
        except ValueError:
            return None

    # < data
    m = re.match(r'^<\s*(\d{1,2})/(\d{1,2})/(\d{4})$', text)
    if m:
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return {"tipo": "prima", "data": d}
        except ValueError:
            return None

    # Data esatta: dd/mm/yyyy
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', text)
    if m:
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return {"tipo": "data", "data": d}
        except ValueError:
            return None

    # */m/yyyy
    m = re.match(r'^\*/(\d{1,2})/(\d{4})$', text)
    if m:
        return {"tipo": "mese_anno", "mese": int(m.group(1)), "anno": int(m.group(2))}

    # mm/yyyy
    m = re.match(r'^(\d{1,2})/(\d{4})$', text)
    if m:
        return {"tipo": "mese_anno", "mese": int(m.group(1)), "anno": int(m.group(2))}

    # "mese anno" testuale
    for nome, num in mesi_map.items():
        m2 = re.match(rf'^{nome}\s+(\d{{4}})$', text)
        if m2:
            return {"tipo": "mese_anno", "mese": num, "anno": int(m2.group(1))}

    # Solo anno
    m = re.match(r'^(\d{4})$', text)
    if m:
        return {"tipo": "anno", "anno": int(m.group(1))}

    return None


def apply_date_filter(query, model_field, date_filter):
    """Applica il filtro data parsed alla query SQLAlchemy."""
    from sqlalchemy import extract
    if not date_filter:
        return query
    t = date_filter["tipo"]
    if t == "anno":
        return query.filter(extract("year", model_field) == date_filter["anno"])
    elif t == "mese_anno":
        return query.filter(
            extract("year", model_field) == date_filter["anno"],
            extract("month", model_field) == date_filter["mese"]
        )
    elif t == "data":
        return query.filter(model_field == date_filter["data"])
    elif t == "dopo":
        return query.filter(model_field > date_filter["data"])
    elif t == "prima":
        return query.filter(model_field < date_filter["data"])
    elif t == "range":
        return query.filter(model_field >= date_filter["da"], model_field <= date_filter["a"])
    return query
