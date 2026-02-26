PERIODS = {
    1: {"label": "P1", "time": "7:00 - 7:50"},
    2: {"label": "P2", "time": "7:50 - 8:40"},
    # Descanso 8:40 - 9:10
    3: {"label": "P3", "time": "9:10 - 10:00"},
    4: {"label": "P4", "time": "10:00 - 10:50"},
    5: {"label": "P5", "time": "10:50 - 11:40"},
    6: {"label": "P6", "time": "11:40 - 12:30"},
    7: {"label": "P7", "time": "12:30 - 13:20"},
    8: {"label": "P8", "time": "13:20 - 14:10"},
    9: {"label": "P9", "time": "14:10 - 15:00"},
    10: {"label": "P10", "time": "15:00 - 15:50"},
    11: {"label": "P11", "time": "15:50 - 16:40"},
    12: {"label": "P12", "time": "16:40 - 17:30"},
    13: {"label": "P13", "time": "17:30 - 18:00"},
}

PERIOD_INDICES = list(PERIODS.keys())  # [1, 2, ..., 13]

DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]


def period_label(period_idx: int) -> str:
    p = PERIODS.get(period_idx)
    if p:
        return f"{p['label']} ({p['time']})"
    return str(period_idx)
