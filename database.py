"""
Connessione al database — compatibile con Streamlit Cloud.
"""
import os
import streamlit as st
from sqlalchemy import create_engine
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
                "Vai su **Manage app → Settings → Secrets** e aggiungi:\n\n"
                "```toml\n[database]\n"
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


def init_db():
    import models  # noqa
    try:
        Base.metadata.create_all(bind=get_engine())
    except Exception as e:
        st.error(f"⚠️ **Connessione al database fallita.**\n\nErrore: `{e}`")
        st.stop()
