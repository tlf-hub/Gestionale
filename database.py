"""Connessione al database — con migrazione automatica colonne mancanti."""
import os
import streamlit as st
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()
_engine = None
_SessionLocal = None


def _get_database_url():
    try:
        url = st.secrets["database"]["url"]
        if url:
            return url
    except (KeyError, AttributeError, FileNotFoundError):
        pass
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    return None


def get_engine():
    global _engine
    if _engine is None:
        url = _get_database_url()
        if url is None:
            st.error(
                "⚠️ **Database non configurato!**\n\n"
                "Aggiungi nei Secrets:\n\n```toml\n[database]\n"
                'url = "postgresql://user:pass@host/db?sslmode=require"\n```'
            )
            st.stop()
        kwargs = {"pool_pre_ping": True}
        if "sqlite" in url:
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs["pool_size"] = 5
        _engine = create_engine(url, **kwargs)
    return _engine


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal()


def _migrate_columns():
    """Aggiunge colonne mancanti alle tabelle esistenti."""
    engine = get_engine()
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    import models  # noqa

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue

        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}

        for col in table.columns:
            if col.name not in existing_cols:
                col_type = col.type.compile(dialect=engine.dialect)

                default_clause = ""
                if col.default is not None:
                    dv = col.default.arg
                    if callable(dv):
                        pass
                    elif isinstance(dv, str):
                        default_clause = f" DEFAULT '{dv}'"
                    elif isinstance(dv, bool):
                        default_clause = f" DEFAULT {'true' if dv else 'false'}"
                    elif isinstance(dv, (int, float)):
                        default_clause = f" DEFAULT {dv}"
                elif col.nullable:
                    default_clause = ""
                elif "VARCHAR" in col_type.upper() or col_type.upper() == "TEXT":
                    default_clause = " DEFAULT ''"
                elif "NUMERIC" in col_type.upper() or col_type.upper() == "INTEGER":
                    default_clause = " DEFAULT 0"
                elif col_type.upper() == "BOOLEAN":
                    default_clause = " DEFAULT false"

                # Per colonne NOT NULL senza default, rendiamole nullable per sicurezza
                if not col.nullable and not default_clause:
                    null_clause = ""
                else:
                    null_clause = "" if col.nullable else " NOT NULL"

                sql = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type}{default_clause}{null_clause}'
                try:
                    with engine.begin() as conn:
                        conn.execute(text(sql))
                except Exception:
                    pass  # colonna già esistente o errore non bloccante


def init_db():
    import models  # noqa
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        _migrate_columns()
        # Crea indici per performance
        from utils.db_indexes import create_indexes
        create_indexes(engine)
    except Exception as e:
        st.error(f"⚠️ **Errore database.**\n\nErrore: `{e}`")
        st.stop()
