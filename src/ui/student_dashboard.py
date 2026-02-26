import streamlit as st
from core.database import get_db
from core.crud import get_user_availability, set_user_availability, get_team_by_id
from core.periods import DAYS, period_label
from ui.components import availability_grid

def student_dashboard():
    user = st.session_state["user"]
    st.title(f"Panel de Estudiante - {user['full_name']}")

    db = next(get_db())

    team = get_team_by_id(db, user['team_id'])
    if team and team.is_locked:
        st.warning("La disponibilidad de tu equipo ha sido bloqueada por el líder.")
        current_slots = [(a.day_of_week, a.period) for a in get_user_availability(db, user['id'])]
        st.write("Tu disponibilidad actual:")
        for day, period in current_slots:
            st.write(f"{DAYS[day]} - {period_label(period)}")
        return

    st.write("Por favor, marca los períodos en los que estás disponible para ir al laboratorio.")

    current_avail = get_user_availability(db, user['id'])
    current_slots = [(a.day_of_week, a.period) for a in current_avail]

    new_slots = availability_grid(current_slots, key_prefix=f"user_{user['id']}")

    if st.button("Guardar Disponibilidad"):
        set_user_availability(db, user['id'], new_slots)
        st.success("Disponibilidad guardada correctamente.")
        st.rerun()
