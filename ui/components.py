import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"] # Mon-Fri
HOURS = list(range(7, 19)) # 7 to 18

def availability_grid(existing_slots, key_prefix="avail"):
    """
    Renders a data editor for availability.
    existing_slots: List of (day_index, hour).
    Returns: List of (day_index, hour) selected.
    """
    # Create DataFrame
    data = {day: [False] * len(HOURS) for day in DAYS}
    df = pd.DataFrame(data, index=[f"{h}:00" for h in HOURS])

    # Pre-fill
    for day_idx, hour in existing_slots:
        if 0 <= day_idx < len(DAYS) and hour in HOURS:
            day_name = DAYS[day_idx]
            row_label = f"{hour}:00"
            df.at[row_label, day_name] = True

    # Render
    st.subheader("Seleccione su disponibilidad")
    edited_df = st.data_editor(df, key=f"{key_prefix}_editor", use_container_width=True)

    # Extract selected slots
    selected_slots = []
    for day_idx, day_name in enumerate(DAYS):
        for hour_idx, hour in enumerate(HOURS):
            row_label = f"{hour}:00"
            if edited_df.at[row_label, day_name]:
                selected_slots.append((day_idx, hour))

    return selected_slots

def blocked_hours_grid(existing_slots, key_prefix="blocked"):
    """
    Renders a data editor for blocking hours (Group Chiefs).
    """
    st.subheader("Bloquear Horas de Clase Teórica")
    return availability_grid(existing_slots, key_prefix)

def schedule_grid(reservations):
    """
    Renders a read-only schedule.
    reservations: List of Reservation objects (or dicts).
    """
    # Create DataFrame
    data = {day: [""] * len(HOURS) for day in DAYS}
    df = pd.DataFrame(data, index=[f"{h}:00" for h in HOURS])

    for res in reservations:
        day_idx = res.day_of_week
        hour = res.hour
        if 0 <= day_idx < len(DAYS) and hour in HOURS:
            day_name = DAYS[day_idx]
            row_label = f"{hour}:00"
            team_name = res.team.name if res.team else "Reservado"
            df.at[row_label, day_name] = team_name

    st.dataframe(df, use_container_width=True)
