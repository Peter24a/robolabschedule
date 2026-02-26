import streamlit as st
from database import get_db
from crud import (
    get_system_setting, set_system_setting, clear_schedule, create_reservation,
    get_all_teams, get_user_availability, get_all_group_blocks, get_all_reservations,
    delete_reservation, get_users_by_team, get_all_users, update_user_role_and_team,
    create_team
)
from ga_engine import GeneticAlgorithmEngine
from models import (
    KEY_OPENING_HOUR, KEY_CLOSING_HOUR, KEY_MANUAL_MODE, KEY_SCHEDULE_STATUS,
    ScheduleState, UserRole, GroupName
)
from ui.components import schedule_grid
import pandas as pd

def admin_dashboard():
    user = st.session_state["user"]
    st.title("Panel de Administración")

    db = next(get_db())

    tab1, tab2, tab3 = st.tabs(["Gestión de Horarios", "Gestión de Equipos", "Gestión de Usuarios"])

    # --- TAB 1: Gestión de Horarios ---
    with tab1:
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
                    try:
                        # Prepare data for GA
                        teams = get_all_teams(db)
                        teams_data = []
                        for t in teams:
                            members = get_users_by_team(db, t.id)
                            members_data = [{'id': m.id, 'role': m.role} for m in members]
                            teams_data.append({
                                'id': t.id,
                                'name': t.name,
                                'group_name': t.group_name,
                                'members': members_data
                            })

                        availabilities = {}
                        # Fetch availabilities for all users
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
                    except Exception as e:
                        st.error(f"Error al ejecutar el algoritmo genético: {str(e)}")


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

    # --- TAB 2: Gestión de Equipos ---
    with tab2:
        st.header("Equipos Existentes")
        teams = get_all_teams(db)

        # Display teams in a dataframe or simple list
        if teams:
            data = [{"ID": t.id, "Nombre": t.name, "Grupo": t.group_name} for t in teams]
            st.dataframe(pd.DataFrame(data))
        else:
            st.info("No hay equipos registrados.")

        st.divider()
        st.subheader("Crear Nuevo Equipo")
        with st.form("create_team_form"):
            new_team_name = st.text_input("Nombre del Equipo")
            # Using strings for better display
            new_team_group_str = st.selectbox("Grupo", ["B", "D"])

            submitted = st.form_submit_button("Crear Equipo")
            if submitted:
                if not new_team_name:
                    st.error("El nombre del equipo es obligatorio.")
                else:
                    try:
                        create_team(db, new_team_name, GroupName(new_team_group_str))
                        st.success("Equipo creado exitosamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al crear equipo: {str(e)}")

    # --- TAB 3: Gestión de Usuarios ---
    with tab3:
        st.header("Usuarios Registrados")
        users = get_all_users(db)

        # Helper to get team name by ID
        teams = get_all_teams(db) # Refresh teams list
        teams_map = {t.id: t.name for t in teams}

        # Translations
        role_translations = {
            "SUPERADMIN": "Administrador",
            "TEACHER": "Maestro",
            "GROUP_CHIEF": "Jefe de Grupo",
            "TEAM_LEADER": "Líder de Equipo",
            "TEAM_MEMBER": "Miembro de Equipo"
        }

        # Prepare data for display
        user_data = []
        for u in users:
            role_val = u.role.value if hasattr(u.role, 'value') else str(u.role)
            role_disp = role_translations.get(role_val, role_val)

            user_data.append({
                "ID": u.id,
                "Usuario": u.username,
                "Nombre Completo": u.full_name,
                "Rol": role_disp,
                "Equipo": teams_map.get(u.team_id, "Sin Asignar"),
                "Grupo (Jefe)": u.group_name.value if u.group_name else "-"
            })

        st.dataframe(pd.DataFrame(user_data))

        st.divider()
        st.subheader("Editar Usuario")

        if not users:
             st.info("No hay usuarios para editar.")
        else:
            # Select user to edit
            user_options = {}
            for u in users:
                label = f"{u.id}: {u.full_name} ({u.username})"
                user_options[label] = u.id

            selected_user_label = st.selectbox("Seleccionar Usuario", options=list(user_options.keys()))

            if selected_user_label:
                selected_user_id = user_options[selected_user_label]
                # Find the user object again to be sure (or filter from list)
                selected_user = next((u for u in users if u.id == selected_user_id), None)

                if selected_user:
                    with st.form("edit_user_form"):
                        st.write(f"Editando a: **{selected_user.full_name}**")

                        # Role Selection
                        role_options = [r.value for r in UserRole]
                        try:
                            # Handle if role is Enum or string
                            current_role_val = selected_user.role.value if hasattr(selected_user.role, 'value') else str(selected_user.role)
                            current_role_index = role_options.index(current_role_val)
                        except ValueError:
                            current_role_index = 0

                        new_role = st.selectbox(
                            "Rol",
                            role_options,
                            index=current_role_index,
                            format_func=lambda x: role_translations.get(x, x)
                        )

                        # Team Selection
                        # Prepare team options: "Ninguno" + list of teams
                        team_options_display = ["Ninguno"] + [f"{t.id}: {t.name}" for t in teams]

                        current_team_index = 0
                        if selected_user.team_id:
                            # Find index
                            for i, t in enumerate(teams):
                                if t.id == selected_user.team_id:
                                    current_team_index = i + 1 # +1 because of "Ninguno"
                                    break

                        new_team_label = st.selectbox("Equipo", team_options_display, index=current_team_index)

                        # Group Name (Only for Group Chief)
                        group_options = ["Ninguno", "B", "D"]
                        current_group_index = 0
                        if selected_user.group_name:
                             val = selected_user.group_name.value if hasattr(selected_user.group_name, 'value') else selected_user.group_name
                             if val == "B":
                                 current_group_index = 1
                             elif val == "D":
                                 current_group_index = 2

                        new_group_label = st.selectbox("Grupo (Solo para Jefes de Grupo)", group_options, index=current_group_index)

                        submitted_edit = st.form_submit_button("Actualizar Usuario")

                        if submitted_edit:
                            # Parse team ID
                            new_team_id = None
                            if new_team_label != "Ninguno":
                                try:
                                    new_team_id = int(new_team_label.split(":")[0])
                                except:
                                    pass

                            # Parse Group
                            new_group = None
                            if new_group_label != "Ninguno":
                                new_group = GroupName(new_group_label)

                            try:
                                update_user_role_and_team(
                                    db,
                                    selected_user_id,
                                    UserRole(new_role),
                                    new_team_id,
                                    new_group
                                )
                                st.success("Usuario actualizado correctamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al actualizar usuario: {str(e)}")
