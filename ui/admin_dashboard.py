import streamlit as st
from database import get_db
from crud import get_system_setting, set_system_setting, clear_schedule, create_reservation, get_all_teams, get_user_availability, get_all_group_blocks, get_all_reservations, delete_reservation, get_users_by_team
from ga_engine import GeneticAlgorithmEngine
from models import KEY_OPENING_HOUR, KEY_CLOSING_HOUR, KEY_MANUAL_MODE, KEY_SCHEDULE_STATUS, ScheduleState
from ui.components import schedule_grid
import pandas as pd

def admin_dashboard():
    user = st.session_state["user"]
    st.title("Panel de Administración")

    db = next(get_db())

    # 1. System Settings
    st.header("Configuración del Sistema")

    col1, col2 = st.columns(2)

    with col1:
        opening_hour = int(get_system_setting(db, KEY_OPENING_HOUR, "7"))
        closing_hour = int(get_system_setting(db, KEY_CLOSING_HOUR, "18"))

        # Opening Hour Selection (7 or 9)
        new_opening = st.selectbox("Hora de Apertura", [7, 9], index=0 if opening_hour==7 else 1)
        if new_opening != opening_hour:
            set_system_setting(db, KEY_OPENING_HOUR, str(new_opening))
            st.rerun()

    with col2:
        manual_mode = get_system_setting(db, KEY_MANUAL_MODE, "false").lower() == "true"
        new_manual = st.toggle("Modo Manual (Emergencia)", value=manual_mode)
        if new_manual != manual_mode:
            set_system_setting(db, KEY_MANUAL_MODE, str(new_manual).lower())
            st.rerun()

    st.write(f"Hora de Cierre: {closing_hour}:00 (Fijo)")

    st.divider()

    # 2. Schedule Generation (GA)
    st.header("Generación de Horarios (IA)")

    current_status = get_system_setting(db, KEY_SCHEDULE_STATUS, ScheduleState.NONE)
    st.write(f"Estado del Horario: **{current_status}**")

    if manual_mode:
        st.warning("El Modo Manual está activado. La generación automática está deshabilitada.")
    else:
        if st.button("Ejecutar Algoritmo Genético"):
            with st.spinner("Ejecutando GA... Esto puede tardar unos segundos..."):
                # Prepare data for GA
                teams = get_all_teams(db)
                teams_data = []
                for t in teams:
                    members = get_users_by_team(db, t.id)
                    members_data = [{'id': m.id, 'role': m.role} for m in members]
                    teams_data.append({
                        'id': t.id,
                        'name': t.name,
                        'group_name': t.group_name, # Enum to string automatically? Or value.
                        'members': members_data
                    })

                availabilities = {}
                # Fetch availabilities for all users
                # Optimisation: fetch all availabilities in one go? Or loop.
                # Loop is fine for now.
                for t in teams:
                    for m in t.members:
                        avails = get_user_availability(db, m.id)
                        availabilities[m.id] = set((a.day_of_week, a.hour) for a in avails)

                group_blocks = set()
                blocks = get_all_group_blocks(db)
                for b in blocks:
                    group_blocks.add((b.group_name, b.day_of_week, b.hour))

                ga = GeneticAlgorithmEngine(teams_data, availabilities, group_blocks, opening_hour, closing_hour)
                schedule = ga.run()

                # Save as Draft
                clear_schedule(db, keep_manual=False) # Clear previous GA schedule
                for item in schedule:
                    try:
                        create_reservation(db, item['team_id'], item['day_of_week'], item['hour'], is_manual=False)
                    except ValueError:
                        pass # Duplicate? Should not happen if GA is correct.

                set_system_setting(db, KEY_SCHEDULE_STATUS, ScheduleState.DRAFT)
                st.success("Horario generado (Borrador). Revísalo abajo.")
                st.rerun()

        # Review Schedule
        reservations = get_all_reservations(db)
        if reservations:
            st.subheader("Vista Previa del Horario")
            schedule_grid(reservations)

            if current_status == ScheduleState.DRAFT:
                col_app, col_rej = st.columns(2)
                with col_app:
                    if st.button("Aprobar y Publicar"):
                        set_system_setting(db, KEY_SCHEDULE_STATUS, ScheduleState.PUBLISHED)
                        st.success("Horario Publicado.")
                        st.rerun()
                with col_rej:
                    if st.button("Rechazar (Borrar)"):
                        clear_schedule(db, keep_manual=False)
                        set_system_setting(db, KEY_SCHEDULE_STATUS, ScheduleState.NONE)
                        st.warning("Horario borrado.")
                        st.rerun()
        else:
            st.info("No hay horario generado.")
