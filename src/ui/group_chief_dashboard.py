import streamlit as st
from database import get_db
from crud import get_group_blocks, set_group_blocks, get_system_setting
from ui.components import availability_grid
from models import GroupName

def group_chief_dashboard():
    user = st.session_state["user"]
    st.title(f"Panel de Jefe de Grupo - {user['full_name']}")

    group_name = user['group_name']
    if not group_name:
        st.error("No tienes un grupo asignado.")
        return

    st.subheader(f"Gestión de Bloques Teóricos para Grupo {group_name}")
    st.write("Selecciona las horas en las que este grupo tiene clases teóricas. NINGÚN equipo de este grupo podrá reservar el laboratorio en estas horas.")

    db = next(get_db())
    current_blocks = get_group_blocks(db, group_name)
    current_slots = [(b.day_of_week, b.hour) for b in current_blocks]

    new_slots = availability_grid(current_slots, key_prefix=f"group_{group_name}")

    if st.button("Guardar Bloques"):
        set_group_blocks(db, group_name, new_slots)
        st.success("Bloques guardados correctamente.")
        st.rerun()
