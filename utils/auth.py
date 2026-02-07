"""Autenticazione utenti."""
import streamlit as st
import bcrypt
from database import get_session
from models import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_default_admin():
    """Crea l'utente admin di default se non esiste."""
    session = get_session()
    try:
        if not session.query(User).filter(User.username == "admin").first():
            session.add(User(
                username="admin",
                password_hash=hash_password("admin"),
                nome_completo="Amministratore",
                ruolo="admin",
                attivo=True,
            ))
            session.commit()
    finally:
        session.close()


def check_auth():
    """Verifica se l'utente è autenticato. Mostra login se no."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.ruolo = None

    if not st.session_state.authenticated:
        show_login()
        st.stop()


def show_login():
    """Mostra la pagina di login."""
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center;padding:2rem 0;">
            <h1 style="color:#1e293b;">⬡ Gestionale</h1>
            <p style="color:#64748b;">Accedi per continuare</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Utente", placeholder="nome utente")
            password = st.text_input("Password", type="password", placeholder="password")
            submitted = st.form_submit_button("🔐 Accedi", use_container_width=True, type="primary")

            if submitted:
                if not username or not password:
                    st.error("Inserisci utente e password.")
                    return
                session = get_session()
                try:
                    user = session.query(User).filter(
                        User.username == username, User.attivo == True
                    ).first()
                    if user and verify_password(password, user.password_hash):
                        st.session_state.authenticated = True
                        st.session_state.user_id = user.id
                        st.session_state.username = user.username
                        st.session_state.ruolo = user.ruolo
                        st.session_state.nome_completo = user.nome_completo
                        st.rerun()
                    else:
                        st.error("Credenziali non valide.")
                finally:
                    session.close()

        st.caption("Primo accesso: utente `admin`, password `admin`")


def require_role(roles):
    """Verifica che l'utente abbia il ruolo richiesto."""
    if isinstance(roles, str):
        roles = [roles]
    if st.session_state.get("ruolo") not in roles:
        st.error("⛔ Non hai i permessi per questa sezione.")
        st.stop()


def logout_button():
    """Mostra il pulsante di logout nella sidebar."""
    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.get('nome_completo', '')}**")
        st.caption(f"Ruolo: {st.session_state.get('ruolo', '')}")
        if st.button("🚪 Esci", use_container_width=True):
            for k in ["authenticated", "user_id", "username", "ruolo", "nome_completo"]:
                st.session_state.pop(k, None)
            st.rerun()
