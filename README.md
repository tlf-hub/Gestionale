# ⬡ Gestionale Aziendale

Gestionale completo per la gestione di prestazioni, fatturazione elettronica (FatturaPA XML),
incassi con SDD SEPA, e anagrafiche clienti. Costruito con **Streamlit + PostgreSQL**.

## Architettura

```
┌──────────────────────────────────────────────────┐
│                  BROWSER                         │
│            http://localhost:8501                  │
└───────────────────┬──────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────┐
│              STREAMLIT APP                        │
│  ┌─────────────────────────────────────────────┐ │
│  │  app.py (entry point)                       │ │
│  │  pages/                                     │ │
│  │   ├── 📊 Dashboard (prestazioni)            │ │
│  │   ├── 👥 Clienti (anagrafica)               │ │
│  │   ├── 📁 Conti Ricavo                       │ │
│  │   ├── 🏢 Soggetti Fatturanti               │ │
│  │   ├── 📄 Fatture (emissione + XML)          │ │
│  │   ├── 💰 Incassi (SDD SEPA workflow)        │ │
│  │   └── 📤 Import/Export (Excel/CSV)          │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │  utils/                                     │ │
│  │   ├── fattura_xml.py  (FatturaPA v1.2.2)    │ │
│  │   ├── sdd_sepa_xml.py (pain.008.001.02)     │ │
│  │   └── helpers.py                            │ │
│  └─────────────────────────────────────────────┘ │
└───────────────────┬──────────────────────────────┘
                    │ SQLAlchemy ORM
┌───────────────────▼──────────────────────────────┐
│              PostgreSQL 16                        │
│  clienti | conti_ricavo | soggetti_fatturanti    │
│  prestazioni | fatture | incassi                 │
└──────────────────────────────────────────────────┘
```

## Requisiti

- **macOS Ventura 13.x** (Intel) oppure qualsiasi macOS/Linux/Windows
- **Python 3.12+**
- **PostgreSQL 16**
- **Git**

## Setup Rapido (macOS Ventura Intel)

### 1. Installa prerequisiti

```bash
# Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Software
brew install python@3.12 postgresql@16 git
brew services start postgresql@16
```

### 2. Clona il repository

```bash
cd ~/Projects
git clone https://github.com/TUOUSER/Gestionale.git
cd Gestionale
```

### 3. Crea l'ambiente Python

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configura il database

```bash
# Crea utente e database PostgreSQL
createuser -s gestionale_user
psql postgres -c "ALTER USER gestionale_user WITH PASSWORD 'SecurePass123!';"
createdb -O gestionale_user gestionale

# Copia e configura il file .env
cp .env.example .env
# Modifica .env se necessario
```

### 5. Avvia l'applicazione

```bash
source venv/bin/activate
streamlit run app.py
```

L'applicazione si aprirà su **http://localhost:8501**

## Funzionalità

### Dashboard (tabella centrale: PRESTAZIONI)
- Filtri rapidi per mese/anno (12 pulsanti + navigazione anno)
- Filtri avanzati: Cliente, Conto Ricavo, Fatturante, Credito, Stato SDD, Periodicità
- Raggruppamento: per Cliente, Conto Ricavo, Fatturante, Fattura
- Azioni massive: Crea, Elimina, Duplica, Duplica +1 mese/trim./sem./anno
- Etichetta periodicità calcolata (mese, trimestre romano, semestre romano, anno)
- Emissione fatture (raggruppamento automatico per cliente + fatturante)
- Generazione XML FatturaPA (singolo o ZIP multiplo)
- Caricamento SDD SEPA con generazione XML pain.008

### Clienti
- Anagrafica completa con tutti i campi richiesti (SDD, RL, fiscali)
- Controllo doppioni su Partita IVA e Codice Fiscale
- CRUD completo

### Fatturazione
- Numerazione progressiva per anno e soggetto fatturante
- 2 fasi: Emissione fattura → Generazione XML FatturaPA
- Download singolo XML o ZIP multiplo

### Incassi (SDD SEPA)
- Workflow: Caricato da confermare → Confermato / Insoluto
- Solo gli incassi "Confermato" contano come incassati
- Generazione XML SDD SEPA (pain.008.001.02) per home banking
- Registrazione incassi manuali (bonifico, contanti, altro)

### Import/Export
- Download template Excel per ogni tabella
- Upload massivo con rilevamento doppioni
- Export in Excel e CSV

## Struttura File

```
Gestionale/
├── app.py                    # Entry point Streamlit
├── config.py                 # Configurazione e costanti
├── database.py               # Connessione DB e sessioni
├── models.py                 # 6 tabelle SQLAlchemy
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── pages/
│   ├── 1_📊_Dashboard.py    # Vista prestazioni principale
│   ├── 2_👥_Clienti.py      # Anagrafica clienti
│   ├── 3_📁_Conti_Ricavo.py
│   ├── 4_🏢_Soggetti_Fatturanti.py
│   ├── 5_📄_Fatture.py      # Fatture + XML FatturaPA
│   ├── 6_💰_Incassi.py      # Incassi + SDD SEPA
│   └── 7_📤_Import_Export.py # Import/Export Excel/CSV
└── utils/
    ├── __init__.py
    ├── helpers.py            # Utility condivise
    ├── fattura_xml.py        # Generatore FatturaPA XML v1.2.2
    └── sdd_sepa_xml.py       # Generatore SDD SEPA pain.008
```

## Database Schema

La tabella centrale è **PRESTAZIONI**, relazionata a:
- **CLIENTI** — anagrafica completa
- **CONTI_RICAVO** — classificazione ricavi
- **SOGGETTI_FATTURANTI** — chi emette la fattura
- **FATTURE** — fatture emesse con XML FatturaPA
- **INCASSI** — allocati a livello riga (prestazione), con workflow SDD SEPA
