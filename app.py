"""
Gestionale Aziendale — Applicazione Streamlit
Entry point principale.
"""
import streamlit as st
from database import init_db

# Configurazione pagina
st.set_page_config(
    page_title="Gestionale Aziendale",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inizializza database
init_db()

# CSS personalizzato
st.markdown("""
<style>
    /* Sidebar styling */
    [data-testid="stSidebar"] { background-color: #1e293b; }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown span { color: #e2e8f0 !important; }

    /* Tabella righe alternate */
    .row-even { background-color: #ffffff; }
    .row-odd { background-color: #f8fafc; }

    /* Metriche */
    [data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
    }

    /* Nascondi il menu hamburger e footer */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Header */
    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## ⬡ Gestionale")
    st.markdown("---")
    st.markdown("### Navigazione")
    st.markdown("""
    - 📊 **Dashboard** — Vista prestazioni
    - 👥 **Clienti** — Anagrafica clienti
    - 📁 **Conti Ricavo**
    - 🏢 **Soggetti Fatturanti**
    - 📄 **Fatture** — Emesse
    - 💰 **Incassi** — Registrazione
    - 📤 **Import/Export** — Dati massivi
    """)
    st.markdown("---")
    st.caption("v1.0 — Gestionale Aziendale")

# Home page
st.markdown('<div class="main-header"><h1 style="margin:0;color:white;">⬡ Gestionale Aziendale</h1><p style="margin:0;opacity:0.8;">Seleziona una sezione dal menu laterale</p></div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("### 📊")
    st.markdown("**Dashboard**")
    st.caption("Gestione prestazioni, fatturazione e incassi")
with col2:
    st.markdown("### 👥")
    st.markdown("**Clienti**")
    st.caption("Anagrafica clienti completa")
with col3:
    st.markdown("### 📄")
    st.markdown("**Fatture**")
    st.caption("Emissione e tracciato XML FatturaPA")
with col4:
    st.markdown("### 💰")
    st.markdown("**Incassi**")
    st.caption("SDD SEPA, bonifici, contanti")

st.info("👈 Usa il menu laterale per navigare tra le sezioni, oppure le pagine in alto.")
