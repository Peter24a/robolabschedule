import streamlit as st
import pandas as pd
from core.database import get_db
from core.crud import get_user_availability, set_user_availability, get_team_by_id, get_users_by_team, lock_team_availability, unlock_team_availability, get_system_setting, get_all_reservations, create_reservation, delete_reservation, get_group_blocks
from ui.components import availability_grid, schedule_grid
from core.models import UserRole, KEY_MANUAL_MODE, KEY_OPENING_HOUR, KEY_CLOSING_HOUR
from sqlalchemy.exc import IntegrityError

MAX_HOURS_PER_TEAM = 3 # Hardcoded quota for Manual Mode

def team_leader_dashboard():
    user = st.session_state["user"]
    st.title(f"Panel de Líder de Equipo - {user['full_name']}")

    db = next(get_db())
    team = get_team_by_id(db, user['team_id'])

    if not team:
        st.error("No tienes un equipo asignado.")
        return

    st.subheader(f"Equipo: {team.name} (Grupo {team.group_name})")

    # Check Manual Mode
    manual_mode = get_system_setting(db, KEY_MANUAL_MODE, "false").lower() == "true"

    if manual_mode:
        st.warning("MODO MANUAL ACTIVADO: Reserva directamente los bloques disponibles.")
        manual_reservation_ui(db, team)
    else:
        availability_management_ui(db, team, user)

def availability_management_ui(db, team, user):
    # 1. Availability Management
    if team.is_locked:
        st.info("La disponibilidad del equipo está bloqueada. Espera a que el Superadmin genere el horario.")
        if st.button("Desbloquear Disponibilidad (Solo si es necesario corregir)"):
            unlock_team_availability(db, team.id)
            st.rerun()
    else:
        st.subheader("Tu Disponibilidad")
        current_avail = get_user_availability(db, user['id'])
        current_slots = [(a.day_of_week, a.hour) for a in current_avail]

        new_slots = availability_grid(current_slots, key_prefix=f"leader_{user['id']}")

        if st.button("Guardar Mi Disponibilidad"):
            set_user_availability(db, user['id'], new_slots)
            st.success("Disponibilidad guardada correctamente.")
            st.rerun()

        st.divider()

        st.subheader("Disponibilidad de Miembros")
        members = get_users_by_team(db, team.id)

        for member in members:
            if member.id == user['id']:
                continue
            st.write(f"**{member.full_name}** ({member.role})")
            avail = get_user_availability(db, member.id)
            if not avail:
                st.warning("No ha ingresado disponibilidad.")
            else:
                st.write(f"{len(avail)} horas disponibles.")

        if st.button("Bloquear Disponibilidad del Equipo"):
            lock_team_availability(db, team.id)
            st.success("Disponibilidad del equipo bloqueada. Listo para asignación.")
            st.rerun()

def manual_reservation_ui(db, team):
    st.subheader("Reservar Bloques (Manual)")

    # Show current reservations
    reservations = get_all_reservations(db) # This gets ALL. We want to show ours + others as busy.

    # My reservations
    my_res = [r for r in reservations if r.team_id == team.id]
    st.write(f"Has reservado {len(my_res)} / {MAX_HOURS_PER_TEAM} horas permitidas.")

    if my_res:
        st.write("Tus reservas:")
        days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        for r in my_res:
            day_name = days[r.day_of_week] if r.day_of_week < 5 else "Día Desconocido"
            st.write(f"- {day_name} a las {r.hour}:00")
            if st.button(f"Cancelar {day_name} {r.hour}:00", key=f"cancel_{r.id}"):
                delete_reservation(db, r.day_of_week, r.hour)
                st.success("Reserva cancelada.")
                st.rerun()

    st.divider()

    # Check Quota
    if len(my_res) >= MAX_HOURS_PER_TEAM:
        st.error(f"Has alcanzado el límite de {MAX_HOURS_PER_TEAM} horas por semana. Cancela una reserva para hacer otra.")
        return

    # Available slots
    opening_hour = int(get_system_setting(db, KEY_OPENING_HOUR, "7"))
    closing_hour = int(get_system_setting(db, KEY_CLOSING_HOUR, "18"))

    # Blocked by Group Chiefs
    group_blocks = get_group_blocks(db, team.group_name) # My group blocks
    blocked_slots = set((b.day_of_week, b.hour) for b in group_blocks)

    # Reserved slots (by anyone)
    reserved_slots = set((r.day_of_week, r.hour) for r in reservations)

    st.write("Bloques Disponibles (Click para reservar):")

    # Grid of buttons?
    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    cols = st.columns(5)

    for day_idx, col in enumerate(cols):
        with col:
            st.write(f"**{days[day_idx]}**")
            for hour in range(opening_hour, closing_hour):
                slot = (day_idx, hour)
                is_blocked = slot in blocked_slots
                is_reserved = slot in reserved_slots

                label = f"{hour}:00"
                key = f"btn_{day_idx}_{hour}"

                if is_blocked:
                    st.button(f"{label} (Clase)", key=key, disabled=True)
                elif is_reserved:
                    # Check if it's mine
                    if any(r.day_of_week == day_idx and r.hour == hour and r.team_id == team.id for r in reservations):
                        st.button(f"{label} (Mío)", key=key, disabled=True)
                    else:
                        st.button(f"{label} (Ocupado)", key=key, disabled=True)
                else:
                    if st.button(f"{label} (Libre)", key=key):
                        try:
                            create_reservation(db, team.id, day_idx, hour, is_manual=True)
                            st.success(f"Reservado: {days[day_idx]} {hour}:00")
                            st.rerun()
                        except ValueError:
                            st.error("Ya está reservado.")
                        except IntegrityError:
                            db.rollback()
                            st.error("Error de concurrencia: Alguien más reservó este bloque justo antes que tú.")
