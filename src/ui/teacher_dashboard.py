import streamlit as st
from core.database import get_db
from core.crud import (
    get_robotics_class_schedule_by_teacher, set_robotics_class_schedule,
    get_all_reservations, get_system_setting
)
from core.models import GroupName, KEY_SCHEDULE_STATUS, ScheduleState
from ui.components import availability_grid, schedule_grid

def teacher_dashboard():
    user = st.session_state["user"]
    st.title(f"Panel del Maestro - {user['full_name']}")

    db = next(get_db())
    teacher_id = user['id']

    teacher_group = user.get('group_name')
    if not teacher_group:
        st.warning("No tienes un grupo asignado. Contacta al administrador.")
        st.info("El administrador debe asignarte el Grupo (B o D) en la gestión de usuarios.")
        return

    st.subheader(f"Horario de Clases de Robótica - Grupo {teacher_group}")
    st.write(
        "Selecciona los períodos en los que impartes tu clase de robótica. "
        "Estos períodos quedarán reservados obligatoriamente para tu grupo en el laboratorio."
    )

    existing = get_robotics_class_schedule_by_teacher(db, teacher_id)
    current_slots = [(r.day_of_week, r.period) for r in existing]

    new_slots = availability_grid(
        current_slots,
        key_prefix=f"rcs_teacher_{teacher_id}",
        title="Selecciona tus períodos de clase robótica"
    )

    if st.button("Guardar Horario"):
        set_robotics_class_schedule(db, teacher_id, GroupName(teacher_group), new_slots)
        st.success("Horario guardado correctamente.")
        st.rerun()

    st.divider()

    # Show published schedule (view-only)
    st.subheader("Calendario Semanal del Laboratorio")
    status = get_system_setting(db, KEY_SCHEDULE_STATUS, ScheduleState.NONE)
    if status != ScheduleState.PUBLISHED:
        st.info("El horario aún no ha sido publicado.")
    else:
        reservations = get_all_reservations(db)
        schedule_grid(reservations)
