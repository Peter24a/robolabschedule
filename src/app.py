import streamlit as st
import sys
import os
from core.database import get_db
from core.crud import get_user_by_username, verify_password

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.login import login_page
from ui.register import register_page
from ui.admin_dashboard import admin_dashboard
from ui.student_dashboard import student_dashboard
from ui.calendar_view import calendar_view
from ui.team_leader_dashboard import team_leader_dashboard
from ui.group_chief_dashboard import group_chief_dashboard
from ui.teacher_dashboard import teacher_dashboard

def main():
    st.set_page_config(page_title="Sistema de Gestión de Laboratorio de Robótica", layout="wide")

    if "user" not in st.session_state:
        st.session_state["user"] = None

    if "show_register" not in st.session_state:
        st.session_state["show_register"] = False

    user = st.session_state["user"]

    if user is None:
        if st.session_state["show_register"]:
            register_page()
        else:
            login_page()
            if st.button("¿No tienes cuenta? Regístrate aquí"):
                st.session_state["show_register"] = True
                st.rerun()
    else:
        # Sidebar with user info
        with st.sidebar:
            st.title(f"Bienvenido, {user['full_name']}")

            # Translate role for display
            role_translations = {
                "SUPERADMIN": "Administrador",
                "TEACHER": "Maestro",
                "GROUP_CHIEF": "Jefe de Grupo",
                "TEAM_LEADER": "Líder de Equipo",
                "TEAM_MEMBER": "Miembro de Equipo"
            }
            role_value = user['role'].value if hasattr(user['role'], 'value') else str(user['role'])
            role_display = role_translations.get(role_value, role_value)

            st.write(f"Rol: {role_display}")
            if st.button("Cerrar Sesión"):
                st.session_state["user"] = None
                st.rerun()

        # Routing based on role
        role = user['role']
        if role == "SUPERADMIN":
            admin_dashboard()
        elif role == "TEACHER":
            teacher_dashboard()
        elif role == "GROUP_CHIEF":
            group_chief_dashboard()
        elif role == "TEAM_LEADER":
            team_leader_dashboard()
        elif role == "TEAM_MEMBER":
            student_dashboard()
        else:
            st.error("Rol desconocido")

if __name__ == "__main__":
    main()
