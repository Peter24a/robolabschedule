import streamlit as st
from crud import get_user_by_username, verify_password
from database import get_db

def login_page():
    st.title("Sistema de Gestión de Laboratorio de Robótica")
    st.subheader("Iniciar Sesión")

    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        db = next(get_db())
        user = get_user_by_username(db, username)

        if user and verify_password(password, user.password_hash):
            st.session_state['user'] = {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "full_name": user.full_name,
                "team_id": user.team_id,
                "group_name": user.group_name
            }
            st.success(f"Bienvenido {user.full_name}")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
