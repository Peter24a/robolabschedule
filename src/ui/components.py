import streamlit as st
import pandas as pd
from core.periods import PERIODS, PERIOD_INDICES, DAYS, period_label


def availability_grid(existing_slots, key_prefix="avail", title="Seleccione su disponibilidad"):
    """
    Renders a data editor for availability.
    existing_slots: List of (day_index, period).
    Returns: List of (day_index, period) selected.
    """
    row_labels = [period_label(p) for p in PERIOD_INDICES]
    data = {day: [False] * len(PERIOD_INDICES) for day in DAYS}
    df = pd.DataFrame(data, index=row_labels)

    # Pre-fill
    for day_idx, period in existing_slots:
        if 0 <= day_idx < len(DAYS) and period in PERIOD_INDICES:
            day_name = DAYS[day_idx]
            row = period_label(period)
            df.at[row, day_name] = True

    st.subheader(title)
    edited_df = st.data_editor(df, key=f"{key_prefix}_editor", use_container_width=True)

    # Extract selected slots
    selected_slots = []
    for day_idx, day_name in enumerate(DAYS):
        for period in PERIOD_INDICES:
            row = period_label(period)
            if edited_df.at[row, day_name]:
                selected_slots.append((day_idx, period))

    return selected_slots


def blocked_hours_grid(existing_slots, key_prefix="blocked"):
    st.subheader("Bloquear Períodos de Clase Teórica")
    return availability_grid(existing_slots, key_prefix, title="Seleccione los períodos con clase teórica")


def schedule_grid(reservations):
    """
    Renders a read-only schedule.
    reservations: List of Reservation objects.
    """
    row_labels = [period_label(p) for p in PERIOD_INDICES]
    data = {day: [""] * len(PERIOD_INDICES) for day in DAYS}
    df = pd.DataFrame(data, index=row_labels)

    for res in reservations:
        day_idx = res.day_of_week
        period = res.period
        if 0 <= day_idx < len(DAYS) and period in PERIOD_INDICES:
            day_name = DAYS[day_idx]
            row = period_label(period)

            if getattr(res, 'is_robotics_class', False) and res.is_robotics_class:
                group = res.group_name.value if res.group_name else "?"
                df.at[row, day_name] = f"Clase Robótica - Grupo {group}"
            else:
                team_name = res.team.name if res.team else "Reservado"
                df.at[row, day_name] = team_name

    st.dataframe(df, use_container_width=True)
