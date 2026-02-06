"""
Gestionale Aziendale — Modelli Database (SQLAlchemy)
Tabella centrale: PRESTAZIONE, relazionata a tutte le altre.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, Numeric, Text,
    ForeignKey, UniqueConstraint, Index, func
)
from sqlalchemy.orm import relationship
from database import Base
from decimal import Decimal
from datetime import datetime


# =============================================================================
# CLIENTE
# =============================================================================
class Cliente(Base):
    __tablename__ = "clienti"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Anagrafica
    cognome_ragione_sociale = Column(String(255), nullable=False, index=True)
    nome = Column(String(100), default="")
    titolo = Column(String(20), default="")

    # Indirizzo
    indirizzo = Column(String(255), default="")
    cap = Column(String(10), default="")
    citta = Column(String(100), default="")
    provincia = Column(String(5), default="")
    paese = Column(String(5), default="IT")

    # Dati fiscali
    tipo_cliente = Column(String(30), nullable=False)
    regime_fiscale = Column(String(20), default="Ordinario")
    liquidazione_iva = Column(String(20), default="")
    sostituto_imposta = Column(Boolean, default=False)
    split_payment = Column(Boolean, default=False)
    codice_fiscale = Column(String(16), default="", index=True)
    partita_iva = Column(String(11), default="", index=True)
    cassa_previdenza = Column(String(50), default="")
    foto = Column(String(500), default="")

    # Rappresentante legale
    rappresentante_legale = Column(String(255), default="")
    carica_rl = Column(String(100), default="")
    cf_rl = Column(String(16), default="")

    # Contatti
    telefono = Column(String(30), default="")
    cellulare = Column(String(30), default="")
    mail = Column(String(255), default="")
    pec = Column(String(255), default="")
    codice_sdi = Column(String(7), default="0000000")

    # SDD SEPA
    sdd_attivo = Column(Boolean, default=False)
    iban_sdd = Column(String(34), default="")
    data_mandato_sdd = Column(Date, nullable=True)
    rif_mandato_sdd = Column(String(50), default="")

    # Stato
    modalita_incasso = Column(String(20), default="Bonifico")
    cliente_attivo = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    prestazioni = relationship("Prestazione", back_populates="cliente")
    fatture = relationship("Fattura", back_populates="cliente")

    @property
    def denominazione(self):
        parts = []
        if self.titolo:
            parts.append(self.titolo)
        parts.append(self.cognome_ragione_sociale)
        if self.nome:
            parts.append(self.nome)
        return " ".join(parts)

    def __repr__(self):
        return f"<Cliente {self.id}: {self.denominazione}>"


# =============================================================================
# CONTO RICAVO
# =============================================================================
class ContoRicavo(Base):
    __tablename__ = "conti_ricavo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codice = Column(String(20), unique=True, nullable=False)
    descrizione = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    prestazioni = relationship("Prestazione", back_populates="conto_ricavo")

    def __repr__(self):
        return f"<ContoRicavo {self.codice}: {self.descrizione}>"


# =============================================================================
# SOGGETTO FATTURANTE
# =============================================================================
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
    created_at = Column(DateTime, default=datetime.utcnow)

    prestazioni = relationship("Prestazione", back_populates="fatturante")
    fatture = relationship("Fattura", back_populates="fatturante")

    def __repr__(self):
        return f"<SoggettoFatturante {self.ragione_sociale}>"


# =============================================================================
# FATTURA
# =============================================================================
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

    def __repr__(self):
        return f"<Fattura {self.numero}/{self.anno}>"


# =============================================================================
# PRESTAZIONE (tabella centrale)
# =============================================================================
class Prestazione(Base):
    __tablename__ = "prestazioni"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # FK relazioni
    cliente_id = Column(Integer, ForeignKey("clienti.id"), nullable=False)
    conto_ricavo_id = Column(Integer, ForeignKey("conti_ricavo.id"), nullable=False)
    fatturante_id = Column(Integer, ForeignKey("soggetti_fatturanti.id"), nullable=False)
    fattura_id = Column(Integer, ForeignKey("fatture.id"), nullable=True)

    # Dati
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

    # Relazioni
    cliente = relationship("Cliente", back_populates="prestazioni")
    conto_ricavo = relationship("ContoRicavo", back_populates="prestazioni")
    fatturante = relationship("SoggettoFatturante", back_populates="prestazioni")
    fattura = relationship("Fattura", back_populates="righe")
    incassi = relationship("Incasso", back_populates="prestazione", cascade="all, delete-orphan")

    @property
    def importo_iva(self):
        return float(self.importo_unitario) * self.aliquota_iva / 100

    @property
    def totale(self):
        return float(self.importo_unitario) + self.importo_iva

    @property
    def totale_incassato(self):
        return sum(float(i.importo) for i in self.incassi if i.stato == "Confermato")

    @property
    def credito_residuo(self):
        return self.totale - self.totale_incassato

    @property
    def is_fatturata(self):
        return self.fattura_id is not None

    def __repr__(self):
        return f"<Prestazione {self.id}: {self.descrizione}>"


# =============================================================================
# INCASSO (allocato a livello riga/prestazione)
# =============================================================================
class Incasso(Base):
    __tablename__ = "incassi"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prestazione_id = Column(Integer, ForeignKey("prestazioni.id"), nullable=False)
    importo = Column(Numeric(10, 2), nullable=False)
    data = Column(Date, nullable=False, index=True)
    stato = Column(String(30), default="Confermato")  # Caricato da confermare / Confermato / Insoluto
    modalita = Column(String(20), default="Bonifico")
    riferimento = Column(String(100), default="")
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    prestazione = relationship("Prestazione", back_populates="incassi")

    def __repr__(self):
        return f"<Incasso {self.id}: €{self.importo} [{self.stato}]>"
