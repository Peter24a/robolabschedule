"""
Backup & restore de la base de datos a JSON, con persistencia en GitHub.
"""
import json
import base64
import os
import requests
from core.database import SessionLocal
from core.models import (
    User, Team, Availability, GroupBlock,
    RoboticsClassSchedule, Reservation, SystemSetting
)

try:
    import streamlit as st
    _secrets = getattr(st, "secrets", {})
except Exception:
    _secrets = {}


def _get_github_config():
    """Obtiene la configuración de GitHub desde st.secrets o variables de entorno."""
    gh = _secrets.get("github", {})
    token = gh.get("token") or os.getenv("GITHUB_TOKEN", "")
    repo = gh.get("repo") or os.getenv("GITHUB_REPO", "")
    path = gh.get("backup_path") or os.getenv("GITHUB_BACKUP_PATH", "backup.json")
    branch = gh.get("branch") or os.getenv("GITHUB_BACKUP_BRANCH", "main")
    return token, repo, path, branch


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_db_to_json(db) -> dict:
    """Serializa todas las tablas de la BD a un diccionario."""
    data = {}

    data["teams"] = [
        {"id": t.id, "name": t.name, "group_name": t.group_name.value, "is_locked": t.is_locked}
        for t in db.query(Team).all()
    ]

    data["users"] = [
        {
            "id": u.id,
            "username": u.username,
            "password_hash": u.password_hash,
            "full_name": u.full_name,
            "role": u.role.value,
            "team_id": u.team_id,
            "group_name": u.group_name.value if u.group_name else None,
        }
        for u in db.query(User).all()
    ]

    data["availabilities"] = [
        {"id": a.id, "user_id": a.user_id, "day_of_week": a.day_of_week, "period": a.period}
        for a in db.query(Availability).all()
    ]

    data["group_blocks"] = [
        {"id": b.id, "group_name": b.group_name.value, "day_of_week": b.day_of_week, "period": b.period}
        for b in db.query(GroupBlock).all()
    ]

    data["robotics_class_schedule"] = [
        {
            "id": r.id,
            "teacher_id": r.teacher_id,
            "group_name": r.group_name.value,
            "day_of_week": r.day_of_week,
            "period": r.period,
        }
        for r in db.query(RoboticsClassSchedule).all()
    ]

    data["reservations"] = [
        {
            "id": r.id,
            "team_id": r.team_id,
            "day_of_week": r.day_of_week,
            "period": r.period,
            "is_manual": r.is_manual,
            "is_robotics_class": r.is_robotics_class,
            "group_name": r.group_name.value if r.group_name else None,
        }
        for r in db.query(Reservation).all()
    ]

    data["system_settings"] = [
        {"key": s.key, "value": s.value}
        for s in db.query(SystemSetting).all()
    ]

    return data


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def import_db_from_json(db, data: dict):
    """Restaura la BD desde un diccionario JSON. Borra datos existentes primero."""
    # Orden de borrado: tablas dependientes primero
    db.query(Availability).delete()
    db.query(RoboticsClassSchedule).delete()
    db.query(Reservation).delete()
    db.query(GroupBlock).delete()
    db.query(SystemSetting).delete()
    db.query(User).delete()
    db.query(Team).delete()
    db.commit()

    # Restaurar teams
    for t in data.get("teams", []):
        db.execute(
            Team.__table__.insert().values(
                id=t["id"], name=t["name"], group_name=t["group_name"], is_locked=t.get("is_locked", False)
            )
        )

    # Restaurar users
    for u in data.get("users", []):
        db.execute(
            User.__table__.insert().values(
                id=u["id"],
                username=u["username"],
                password_hash=u["password_hash"],
                full_name=u["full_name"],
                role=u["role"],
                team_id=u.get("team_id"),
                group_name=u.get("group_name"),
            )
        )

    # Restaurar availabilities
    for a in data.get("availabilities", []):
        db.execute(
            Availability.__table__.insert().values(
                id=a["id"], user_id=a["user_id"], day_of_week=a["day_of_week"], period=a["period"]
            )
        )

    # Restaurar group_blocks
    for b in data.get("group_blocks", []):
        db.execute(
            GroupBlock.__table__.insert().values(
                id=b["id"], group_name=b["group_name"], day_of_week=b["day_of_week"], period=b["period"]
            )
        )

    # Restaurar robotics_class_schedule
    for r in data.get("robotics_class_schedule", []):
        db.execute(
            RoboticsClassSchedule.__table__.insert().values(
                id=r["id"],
                teacher_id=r["teacher_id"],
                group_name=r["group_name"],
                day_of_week=r["day_of_week"],
                period=r["period"],
            )
        )

    # Restaurar reservations
    for r in data.get("reservations", []):
        db.execute(
            Reservation.__table__.insert().values(
                id=r["id"],
                team_id=r.get("team_id"),
                day_of_week=r["day_of_week"],
                period=r["period"],
                is_manual=r.get("is_manual", False),
                is_robotics_class=r.get("is_robotics_class", False),
                group_name=r.get("group_name"),
            )
        )

    # Restaurar system_settings
    for s in data.get("system_settings", []):
        db.execute(
            SystemSetting.__table__.insert().values(key=s["key"], value=s["value"])
        )

    db.commit()


# ---------------------------------------------------------------------------
# GitHub persistence
# ---------------------------------------------------------------------------

def save_backup_to_github(data: dict) -> str:
    """Guarda el JSON de backup en el repositorio de GitHub. Retorna mensaje de estado."""
    token, repo, path, branch = _get_github_config()
    if not token or not repo:
        return "Error: Configura GITHUB_TOKEN y GITHUB_REPO en st.secrets o variables de entorno."

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    # Obtener SHA del archivo si ya existe (necesario para actualizar)
    sha = None
    resp = requests.get(url, headers=headers, params={"ref": branch})
    if resp.status_code == 200:
        sha = resp.json().get("sha")

    content = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode()
    payload = {
        "message": "Auto-backup base de datos",
        "content": content,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=headers, json=payload)
    if resp.status_code in (200, 201):
        return "Backup guardado en GitHub exitosamente."
    return f"Error al guardar backup: {resp.status_code} - {resp.text}"


def load_backup_from_github() -> dict | None:
    """Descarga el JSON de backup desde GitHub. Retorna dict o None."""
    token, repo, path, branch = _get_github_config()
    if not token or not repo:
        return None

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    resp = requests.get(url, headers=headers, params={"ref": branch})
    if resp.status_code != 200:
        return None

    content = resp.json().get("content", "")
    raw = base64.b64decode(content).decode()
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Helper de alto nivel
# ---------------------------------------------------------------------------

def trigger_backup(db):
    """Exporta la BD y la guarda en GitHub. Retorna mensaje de estado."""
    data = export_db_to_json(db)
    return save_backup_to_github(data)


def auto_restore_if_empty(db):
    """Si la BD está vacía (sin usuarios), intenta restaurar desde GitHub."""
    user_count = db.query(User).count()
    if user_count > 0:
        return None  # BD tiene datos, no restaurar

    data = load_backup_from_github()
    if data and data.get("users"):
        import_db_from_json(db, data)
        return "Base de datos restaurada desde backup de GitHub."
    return None
