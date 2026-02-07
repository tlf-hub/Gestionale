"""🔐 Utenti — Gestione utenti e accessi (solo admin)."""
import streamlit as st
import pandas as pd
from database import get_session, init_db
from models import User
from config import RUOLI_UTENTE
from utils.auth import check_auth, logout_button, require_role, hash_password
from utils.styles import COMMON_CSS

st.set_page_config(page_title="Utenti", page_icon="🔐", layout="wide")
init_db(); st.markdown(COMMON_CSS, unsafe_allow_html=True); check_auth(); logout_button()
require_role("admin")

st.markdown('<div class="page-header"><h2>🔐 Gestione Utenti</h2></div>', unsafe_allow_html=True)

session = get_session()
try:
    # Elenco utenti
    users = session.query(User).order_by(User.username).all()
    if users:
        df = pd.DataFrame([{
            "Username": u.username, "Nome": u.nome_completo,
            "Ruolo": u.ruolo, "Attivo": "✓" if u.attivo else "✗",
            "Creato": u.created_at.strftime("%d/%m/%Y") if u.created_at else "",
        } for u in users])
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Nuovo utente
    st.markdown("### ➕ Nuovo utente")
    with st.form("new_user"):
        c1, c2, c3 = st.columns(3)
        username = c1.text_input("Username *")
        password = c2.text_input("Password *", type="password")
        nome = c3.text_input("Nome completo")
        r1, r2 = st.columns(2)
        ruolo = r1.selectbox("Ruolo", RUOLI_UTENTE)
        attivo = r2.checkbox("Attivo", value=True)

        if st.form_submit_button("💾 Crea utente", type="primary"):
            if not username or not password:
                st.error("Username e password obbligatori.")
            elif session.query(User).filter(User.username == username).first():
                st.error(f"Username '{username}' già esistente.")
            else:
                session.add(User(
                    username=username, password_hash=hash_password(password),
                    nome_completo=nome or username, ruolo=ruolo, attivo=attivo))
                session.commit()
                st.success(f"✅ Utente '{username}' creato!"); st.rerun()

    # Modifica utente
    if users:
        st.markdown("---")
        st.markdown("### ✏️ Modifica utente")
        sel_id = st.selectbox("Seleziona", [u.id for u in users],
            format_func=lambda i: next(f"{u.username} ({u.nome_completo})" for u in users if u.id == i))
        u = session.query(User).get(sel_id)
        if u:
            with st.form("edit_user"):
                e1, e2 = st.columns(2)
                e_nome = e1.text_input("Nome completo", value=u.nome_completo or "")
                e_ruolo = e2.selectbox("Ruolo", RUOLI_UTENTE,
                    index=RUOLI_UTENTE.index(u.ruolo) if u.ruolo in RUOLI_UTENTE else 0)
                e_attivo = st.checkbox("Attivo", value=u.attivo)
                new_pass = st.text_input("Nuova password (lascia vuoto per non cambiare)", type="password")

                if st.form_submit_button("💾 Aggiorna", type="primary"):
                    u.nome_completo = e_nome; u.ruolo = e_ruolo; u.attivo = e_attivo
                    if new_pass:
                        u.password_hash = hash_password(new_pass)
                    session.commit()
                    st.success("✅ Aggiornato!"); st.rerun()

            if u.username != "admin":
                if st.button(f"🗑️ Elimina '{u.username}'"):
                    session.delete(u); session.commit(); st.rerun()
            else:
                st.caption("L'utente admin non può essere eliminato.")

    # Cambio password personale
    st.markdown("---")
    st.markdown("### 🔑 Cambia la tua password")
    with st.form("change_pwd"):
        old_pwd = st.text_input("Password attuale", type="password")
        new_pwd = st.text_input("Nuova password", type="password")
        new_pwd2 = st.text_input("Conferma nuova password", type="password")
        if st.form_submit_button("🔑 Cambia password"):
            from utils.auth import verify_password
            me = session.query(User).get(st.session_state.user_id)
            if not verify_password(old_pwd, me.password_hash):
                st.error("Password attuale non corretta.")
            elif new_pwd != new_pwd2:
                st.error("Le nuove password non corrispondono.")
            elif len(new_pwd) < 4:
                st.error("La password deve essere almeno 4 caratteri.")
            else:
                me.password_hash = hash_password(new_pwd)
                session.commit()
                st.success("✅ Password cambiata!")
finally:
    session.close()
