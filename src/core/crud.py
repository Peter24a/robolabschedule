from sqlalchemy.orm import Session
from sqlalchemy import and_
from core.models import User, Team, Availability, GroupBlock, Reservation, SystemSetting, UserRole, GroupName, ScheduleState
from core.models import KEY_OPENING_HOUR, KEY_CLOSING_HOUR, KEY_MANUAL_MODE, KEY_SCHEDULE_STATUS
import bcrypt
from typing import List, Optional

def verify_password(plain_password, hashed_password):
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

def get_password_hash(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# --- User Management ---
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username, password, full_name, role, team_id=None, group_name=None):
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        password_hash=hashed_password,
        full_name=full_name,
        role=role,
        team_id=team_id,
        group_name=group_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users_by_team(db: Session, team_id: int):
    return db.query(User).filter(User.team_id == team_id).all()

def get_all_users(db: Session):
    return db.query(User).all()

def update_user_role_and_team(db: Session, user_id: int, role: UserRole, team_id: int = None, group_name: GroupName = None):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.role = role
        user.team_id = team_id
        user.group_name = group_name
        db.commit()
        db.refresh(user)
    return user

# --- Team Management ---
def create_team(db: Session, name: str, group_name: GroupName):
    db_team = Team(name=name, group_name=group_name)
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team

def get_all_teams(db: Session):
    return db.query(Team).all()

def get_team_by_id(db: Session, team_id: int):
    return db.query(Team).filter(Team.id == team_id).first()

def lock_team_availability(db: Session, team_id: int):
    team = get_team_by_id(db, team_id)
    if team:
        team.is_locked = True
        db.commit()
        return True
    return False

def unlock_team_availability(db: Session, team_id: int):
    team = get_team_by_id(db, team_id)
    if team:
        team.is_locked = False
        db.commit()
        return True
    return False

def update_team(db: Session, team_id: int, name: str, group_name: GroupName):
    team = db.query(Team).filter(Team.id == team_id).first()
    if team:
        team.name = name
        team.group_name = group_name
        db.commit()
        db.refresh(team)
    return team

# --- Availability Management ---
def set_user_availability(db: Session, user_id: int, slots: List[tuple]):
    """
    slots: List of (day_of_week, hour) tuples
    """
    # Clear existing availability
    db.query(Availability).filter(Availability.user_id == user_id).delete()

    # Add new
    for day, hour in slots:
        avail = Availability(user_id=user_id, day_of_week=day, hour=hour)
        db.add(avail)
    db.commit()

def get_user_availability(db: Session, user_id: int):
    return db.query(Availability).filter(Availability.user_id == user_id).all()

def get_team_availability(db: Session, team_id: int):
    """Returns a dictionary mapping (day, hour) to count of available members."""
    users = get_users_by_team(db, team_id)
    user_ids = [u.id for u in users]

    avails = db.query(Availability).filter(Availability.user_id.in_(user_ids)).all()

    counts = {}
    for a in avails:
        key = (a.day_of_week, a.hour)
        counts[key] = counts.get(key, 0) + 1
    return counts, len(users)

# --- Group Blocks (Theory Classes) ---
def set_group_blocks(db: Session, group_name: GroupName, slots: List[tuple]):
    """
    slots: List of (day_of_week, hour) tuples
    """
    # Clear existing blocks for this group
    db.query(GroupBlock).filter(GroupBlock.group_name == group_name).delete()

    for day, hour in slots:
        block = GroupBlock(group_name=group_name, day_of_week=day, hour=hour)
        db.add(block)
    db.commit()

def get_group_blocks(db: Session, group_name: GroupName):
    return db.query(GroupBlock).filter(GroupBlock.group_name == group_name).all()

def get_all_group_blocks(db: Session):
    return db.query(GroupBlock).all()

# --- Reservations / Schedule ---
def create_reservation(db: Session, team_id: int, day: int, hour: int, is_manual: bool):
    # Check for conflict
    existing = db.query(Reservation).filter_by(day_of_week=day, hour=hour).first()
    if existing:
        raise ValueError("Slot already reserved")

    res = Reservation(team_id=team_id, day_of_week=day, hour=hour, is_manual=is_manual)
    db.add(res)
    db.commit()
    return res

def delete_reservation(db: Session, day: int, hour: int):
    db.query(Reservation).filter_by(day_of_week=day, hour=hour).delete()
    db.commit()

def get_all_reservations(db: Session):
    return db.query(Reservation).all()

def clear_schedule(db: Session, keep_manual=True):
    query = db.query(Reservation)
    if keep_manual:
        query = query.filter(Reservation.is_manual == False)
    query.delete()
    db.commit()

# --- System Settings ---
def get_system_setting(db: Session, key: str, default: str = ""):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if setting:
        return setting.value
    return default

def set_system_setting(db: Session, key: str, value: str):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = SystemSetting(key=key, value=value)
        db.add(setting)
    db.commit()

def init_system_settings(db: Session):
    # Set defaults if not exist
    if not get_system_setting(db, KEY_OPENING_HOUR):
        set_system_setting(db, KEY_OPENING_HOUR, "7")
    if not get_system_setting(db, KEY_CLOSING_HOUR):
        set_system_setting(db, KEY_CLOSING_HOUR, "18")
    if not get_system_setting(db, KEY_MANUAL_MODE):
        set_system_setting(db, KEY_MANUAL_MODE, "false")
    if not get_system_setting(db, KEY_SCHEDULE_STATUS):
        set_system_setting(db, KEY_SCHEDULE_STATUS, ScheduleState.NONE)
