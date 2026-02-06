import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://gestionale_user:SecurePass123!@localhost:5432/gestionale")
CODICE_PAESE = os.getenv("CODICE_PAESE", "IT")
FORMATO_TRASMISSIONE = os.getenv("FORMATO_TRASMISSIONE", "FPR12")

MESI = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
        "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
MESI_SHORT = ["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]
ROMAN_TRIMESTRI = ["I","I","I","II","II","II","III","III","III","IV","IV","IV"]
ROMAN_SEMESTRI  = ["I","I","I","I","I","I","II","II","II","II","II","II"]

PERIODICITA_OPTIONS = ["Una tantum","Mensile","Trimestrale","Semestrale","Annuale"]
TIPO_CLIENTE_OPTIONS = ["srl","srls","spa","coop","coop sociale","ssd","asd","aps",
    "associazione","comitato","fondazione","ditta individuale","sas","snc",
    "professionista","consorzio","condominio","persona fisica","ati"]
REGIME_FISCALE_OPTIONS = ["Ordinario","Semplificato","Forfettario"]
MODALITA_INCASSO_OPTIONS = ["SDD SEPA","Bonifico","Contanti","Altro"]
STATO_SDD_OPTIONS = ["Caricato da confermare","Confermato","Insoluto"]
ALIQUOTA_OPTIONS = [0, 4, 5, 10, 22]
TITOLO_OPTIONS = ["","Dott.","Dott.ssa","Avv.","Ing.","Arch.","Geom.","Rag.","Prof.","Prof.ssa"]
