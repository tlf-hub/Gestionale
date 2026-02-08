"""Indici aggiuntivi per ottimizzare le query della Dashboard."""
from sqlalchemy import text


INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_prest_data_inizio ON prestazioni (data_inizio)",
    "CREATE INDEX IF NOT EXISTS idx_prest_cliente ON prestazioni (cliente_id)",
    "CREATE INDEX IF NOT EXISTS idx_prest_fatturante ON prestazioni (fatturante_id)",
    "CREATE INDEX IF NOT EXISTS idx_prest_conto ON prestazioni (conto_ricavo_id)",
    "CREATE INDEX IF NOT EXISTS idx_prest_fattura ON prestazioni (fattura_id)",
    "CREATE INDEX IF NOT EXISTS idx_prest_data_mese ON prestazioni (EXTRACT(month FROM data_inizio), EXTRACT(year FROM data_inizio))",
    "CREATE INDEX IF NOT EXISTS idx_incasso_prest ON incassi (prestazione_id)",
    "CREATE INDEX IF NOT EXISTS idx_incasso_stato ON incassi (stato)",
    "CREATE INDEX IF NOT EXISTS idx_fattura_anno ON fatture (anno, fatturante_id)",
    "CREATE INDEX IF NOT EXISTS idx_cliente_attivo ON clienti (cliente_attivo)",
]

def create_indexes(engine):
    """Crea gli indici se non esistono."""
    try:
        with engine.begin() as conn:
            for sql in INDEXES:
                try:
                    conn.execute(text(sql))
                except Exception:
                    pass  # Ignora errori (es. indice già esistente, SQLite non supporta)
    except Exception:
        pass
