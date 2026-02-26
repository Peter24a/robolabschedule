import streamlit as st
import sys
import os
from database import get_db
from crud import get_user_by_username, verify_password

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.login import login_page
from ui.admin_dashboard import admin_dashboard
from ui.student_dashboard import student_dashboard
from ui.calendar_view import calendar_view
from ui.team_leader_dashboard import team_leader_dashboard
from ui.group_chief_dashboard import group_chief_dashboard

def main():
    st.set_page_config(page_title="Sistema de Gestión de Laboratorio de Robótica", layout="wide")

    if "user" not in st.session_state:
        st.session_state["user"] = None

    user = st.session_state["user"]

    if user is None:
        login_page()
    else:
        # Sidebar with user info
        with st.sidebar:
            st.title(f"Bienvenido, {user['full_name']}")
            st.write(f"Rol: {user['role']}")
            if st.button("Cerrar Sesión"):
                st.session_state["user"] = None
                st.rerun()

        # Routing based on role
        role = user['role']
        if role == "SUPERADMIN":
            admin_dashboard()
        elif role == "TEACHER":
            st.title("Calendario Maestro")
            calendar_view()
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
