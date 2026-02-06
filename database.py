from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_session():
    """Restituisce una sessione database."""
    return SessionLocal()


def init_db():
    """Crea tutte le tabelle se non esistono."""
    from models import Cliente, ContoRicavo, SoggettoFatturante, Fattura, Prestazione, Incasso
    Base.metadata.create_all(bind=engine)
