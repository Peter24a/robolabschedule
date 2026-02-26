import streamlit as st
from core.database import get_db
from core.crud import get_all_reservations, get_system_setting
from core.models import KEY_SCHEDULE_STATUS, ScheduleState
from ui.components import schedule_grid

def calendar_view():
    st.subheader("Calendario Semanal del Laboratorio")

    db = next(get_db())
    status = get_system_setting(db, KEY_SCHEDULE_STATUS, ScheduleState.NONE)

    if status != ScheduleState.PUBLISHED:
        st.info("El horario aún no ha sido publicado.")
        return

    reservations = get_all_reservations(db)
    schedule_grid(reservations)
