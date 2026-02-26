import streamlit as st
from database import get_db
from crud import get_user_availability, set_user_availability, get_team_by_id, get_system_setting
from models import KEY_CLOSING_HOUR, KEY_OPENING_HOUR
from ui.components import availability_grid
import pandas as pd

def student_dashboard():
    user = st.session_state["user"]
    st.title(f"Panel de Estudiante - {user['full_name']}")

    db = next(get_db())

    # Check if team is locked
    team = get_team_by_id(db, user['team_id'])
    if team and team.is_locked:
        st.warning("La disponibilidad de tu equipo ha sido bloqueada por el líder.")
        # Read-only view
        current_slots = [(a.day_of_week, a.hour) for a in get_user_availability(db, user['id'])]
        # We can reuse availability_grid but disable editing?
        # st.data_editor has `disabled=True`.
        # But availability_grid doesn't support it yet.
        # Let's just show a text list or similar for now.
        st.write("Tu disponibilidad actual:")
        days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        for day, hour in current_slots:
            st.write(f"{days[day]} - {hour}:00")
        return

    st.write("Por favor, marca las horas en las que estás disponible para ir al laboratorio.")

    # Load current availability
    current_avail = get_user_availability(db, user['id'])
    current_slots = [(a.day_of_week, a.hour) for a in current_avail]

    # Render grid
    new_slots = availability_grid(current_slots, key_prefix=f"user_{user['id']}")

    if st.button("Guardar Disponibilidad"):
        set_user_availability(db, user['id'], new_slots)
        st.success("Disponibilidad guardada correctamente.")
        st.rerun()
