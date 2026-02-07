"""
Gestionale Aziendale — Modelli Database (SQLAlchemy)
Tabelle: User, SavedFilter, Cliente, ContoRicavo, SoggettoFatturante, Fattura, Prestazione, Incasso
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, Numeric, Text, LargeBinary,
    ForeignKey, UniqueConstraint, JSON
)
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nome_completo = Column(String(100), default="")
    ruolo = Column(String(20), default="operatore")  # admin, operatore, lettore
    attivo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    saved_filters = relationship("SavedFilter", back_populates="user")


class SavedFilter(Base):
    __tablename__ = "saved_filters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    nome = Column(String(100), nullable=False)
    filtri = Column(JSON, nullable=False)  # dict with all filter values
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="saved_filters")


class Cliente(Base):
    __tablename__ = "clienti"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cognome_ragione_sociale = Column(String(255), nullable=False, index=True)
    nome = Column(String(100), default="")
    titolo = Column(String(20), default="")
    indirizzo = Column(String(255), default="")
    cap = Column(String(10), default="")
    citta = Column(String(100), default="")
    provincia = Column(String(5), default="")
    paese = Column(String(5), default="IT")
    tipo_cliente = Column(String(30), nullable=False)
    regime_fiscale = Column(String(20), default="Ordinario")
    liquidazione_iva = Column(String(20), default="")
    sostituto_imposta = Column(Boolean, default=False)
    split_payment = Column(Boolean, default=False)
    codice_fiscale = Column(String(16), default="", index=True)
    partita_iva = Column(String(11), default="", index=True)
    cassa_previdenza = Column(String(50), default="")
    foto = Column(String(500), default="")
    rappresentante_legale = Column(String(255), default="")
    carica_rl = Column(String(100), default="")
    cf_rl = Column(String(16), default="")
    telefono = Column(String(30), default="")
    cellulare = Column(String(30), default="")
    mail = Column(String(255), default="")
    pec = Column(String(255), default="")
    codice_sdi = Column(String(7), default="0000000")
    sdd_attivo = Column(Boolean, default=False)
    iban_sdd = Column(String(34), default="")
    data_mandato_sdd = Column(Date, nullable=True)
    rif_mandato_sdd = Column(String(50), default="")
    modalita_incasso = Column(String(20), default="Bonifico")
    cliente_attivo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    prestazioni = relationship("Prestazione", back_populates="cliente")
    fatture = relationship("Fattura", back_populates="cliente")

    @property
    def denominazione(self):
        parts = []
        if self.titolo:
            parts.append(self.titolo)
        parts.append(self.cognome_ragione_sociale or "")
        if self.nome:
            parts.append(self.nome)
        return " ".join(parts)

    def __repr__(self):
        return f"<Cliente {self.id}: {self.denominazione}>"


class ContoRicavo(Base):
    __tablename__ = "conti_ricavo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    codice = Column(String(20), unique=True, nullable=False)
    descrizione = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    prestazioni = relationship("Prestazione", back_populates="conto_ricavo")


class SoggettoFatturante(Base):
    __tablename__ = "soggetti_fatturanti"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ragione_sociale = Column(String(255), nullable=False)
    partita_iva = Column(String(11), unique=True, nullable=False)
    codice_fiscale = Column(String(16), nullable=False)
    indirizzo = Column(String(255), default="")
    cap = Column(String(10), default="")
    citta = Column(String(100), default="")
    provincia = Column(String(5), default="")
    paese = Column(String(5), default="IT")
    regime_fiscale = Column(String(20), default="Ordinario")
    pec = Column(String(255), default="")
    codice_sdi = Column(String(7), default="0000000")
    iban = Column(String(34), default="")
    logo = Column(LargeBinary, nullable=True)
    logo_filename = Column(String(255), default="")
    smtp_host = Column(String(255), default="")
    smtp_port = Column(Integer, default=587)
    smtp_user = Column(String(255), default="")
    smtp_password = Column(String(255), default="")
    smtp_from = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    prestazioni = relationship("Prestazione", back_populates="fatturante")
    fatture = relationship("Fattura", back_populates="fatturante")


class Fattura(Base):
    __tablename__ = "fatture"
    id = Column(Integer, primary_key=True, autoincrement=True)
    numero = Column(Integer, nullable=False)
    anno = Column(Integer, nullable=False)
    data = Column(Date, nullable=False)
    cliente_id = Column(Integer, ForeignKey("clienti.id"), nullable=False)
    fatturante_id = Column(Integer, ForeignKey("soggetti_fatturanti.id"), nullable=False)
    totale_imponibile = Column(Numeric(12, 2), default=0)
    totale_iva = Column(Numeric(12, 2), default=0)
    totale = Column(Numeric(12, 2), default=0)
    stato = Column(String(20), default="Emessa")
    xml_generato = Column(Boolean, default=False)
    xml_filename = Column(String(255), default="")
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("numero", "anno", "fatturante_id", name="uq_fattura_num_anno_fatt"),
    )

    cliente = relationship("Cliente", back_populates="fatture")
    fatturante = relationship("SoggettoFatturante", back_populates="fatture")
    righe = relationship("Prestazione", back_populates="fattura")


class Prestazione(Base):
    __tablename__ = "prestazioni"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey("clienti.id"), nullable=False)
    conto_ricavo_id = Column(Integer, ForeignKey("conti_ricavo.id"), nullable=False)
    fatturante_id = Column(Integer, ForeignKey("soggetti_fatturanti.id"), nullable=False)
    fattura_id = Column(Integer, ForeignKey("fatture.id"), nullable=True)
    periodicita = Column(String(20), nullable=False)
    descrizione = Column(String(500), nullable=False)
    importo_unitario = Column(Numeric(10, 2), nullable=False)
    aliquota_iva = Column(Integer, default=22)
    data_inizio = Column(Date, nullable=False, index=True)
    data_fine = Column(Date, nullable=False)
    modalita_incasso = Column(String(20), default="Bonifico")
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = relationship("Cliente", back_populates="prestazioni")
    conto_ricavo = relationship("ContoRicavo", back_populates="prestazioni")
    fatturante = relationship("SoggettoFatturante", back_populates="prestazioni")
    fattura = relationship("Fattura", back_populates="righe")
    incassi = relationship("Incasso", back_populates="prestazione", cascade="all, delete-orphan")

    @property
    def importo_iva(self):
        return float(self.importo_unitario or 0) * (self.aliquota_iva or 0) / 100

    @property
    def totale(self):
        return float(self.importo_unitario or 0) + self.importo_iva

    @property
    def totale_incassato(self):
        return sum(float(i.importo) for i in self.incassi if i.stato == "Confermato")

    @property
    def credito_residuo(self):
        return self.totale - self.totale_incassato

    @property
    def is_fatturata(self):
        return self.fattura_id is not None


class Incasso(Base):
    __tablename__ = "incassi"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prestazione_id = Column(Integer, ForeignKey("prestazioni.id"), nullable=False)
    importo = Column(Numeric(10, 2), nullable=False)
    data = Column(Date, nullable=False, index=True)
    stato = Column(String(30), default="Confermato")
    modalita = Column(String(20), default="Bonifico")
    riferimento = Column(String(100), default="")
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    prestazione = relationship("Prestazione", back_populates="incassi")
