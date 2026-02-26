import streamlit as st
from database import get_db
from crud import create_user, get_user_by_username
from models import UserRole

def register_page():
    st.title("Registro de Usuario")

    with st.form("register_form"):
        username = st.text_input("Nombre de Usuario")
        full_name = st.text_input("Nombre Completo")
        password = st.text_input("Contraseña", type="password")
        confirm_password = st.text_input("Confirmar Contraseña", type="password")

        submitted = st.form_submit_button("Registrarse")

        if submitted:
            if not username or not full_name or not password:
                st.error("Por favor, complete todos los campos.")
                return

            if password != confirm_password:
                st.error("Las contraseñas no coinciden.")
                return

            db = next(get_db())
            existing_user = get_user_by_username(db, username)
            if existing_user:
                st.error("El nombre de usuario ya está en uso.")
                return

            # Default role is TEAM_MEMBER
            try:
                create_user(
                    db=db,
                    username=username,
                    password=password,
                    full_name=full_name,
                    role=UserRole.TEAM_MEMBER,
                    team_id=None,
                    group_name=None
                )
                st.success("Registro exitoso. Por favor, inicie sesión.")
                st.session_state["show_register"] = False
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar usuario: {str(e)}")

    if st.button("Volver al Inicio de Sesión"):
        st.session_state["show_register"] = False
        st.rerun()
