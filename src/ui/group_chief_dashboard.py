import streamlit as st
from core.database import get_db
from core.crud import get_group_blocks, set_group_blocks
from ui.components import availability_grid

def group_chief_dashboard():
    user = st.session_state["user"]
    st.title(f"Panel de Jefe de Grupo - {user['full_name']}")

    group_name = user['group_name']
    if not group_name:
        st.error("No tienes un grupo asignado.")
        return

    st.subheader(f"Gestión de Bloques Teóricos para Grupo {group_name}")
    st.write("Selecciona los períodos en los que este grupo tiene clases teóricas. NINGÚN equipo de este grupo podrá reservar el laboratorio en estos períodos.")

    db = next(get_db())
    current_blocks = get_group_blocks(db, group_name)
    current_slots = [(b.day_of_week, b.period) for b in current_blocks]

    new_slots = availability_grid(current_slots, key_prefix=f"group_{group_name}",
                                  title="Períodos de Clase Teórica")

    if st.button("Guardar Bloques"):
        set_group_blocks(db, group_name, new_slots)
        st.success("Bloques guardados correctamente.")
        st.rerun()
