from core.database import engine, Base, SessionLocal
import core.models as models
from core.models import User, UserRole, GroupName, Team, RoboticsClassSchedule
from core.crud import create_user, create_team, init_system_settings

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

    db = SessionLocal()

    # Initialize System Settings
    init_system_settings(db)

    # Check if admin exists
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        print("Creating superadmin...")
        create_user(db, "admin", "admin123", "Moya (Admin)", UserRole.SUPERADMIN, group_name=GroupName.B)

    # Check if teacher exists
    teacher = db.query(User).filter(User.username == "teacher").first()
    if not teacher:
        print("Creating teacher...")
        create_user(db, "teacher", "teacher123", "Cantero (Teacher)", UserRole.TEACHER, group_name=GroupName.D)

    # Check if group chiefs exist
    chief_b = db.query(User).filter(User.username == "chief_b").first()
    if not chief_b:
        print("Creating Chief Group B...")
        create_user(db, "chief_b", "chief123", "Jefe Grupo B", UserRole.GROUP_CHIEF, group_name=GroupName.B)

    chief_d = db.query(User).filter(User.username == "chief_d").first()
    if not chief_d:
        print("Creating Chief Group D...")
        create_user(db, "chief_d", "chief123", "Jefe Grupo D", UserRole.GROUP_CHIEF, group_name=GroupName.D)

    # Create some dummy teams and leaders for testing
    if not db.query(Team).first():
        print("Creating dummy teams...")
        team1 = create_team(db, "Team Alpha (B)", GroupName.B)
        create_user(db, "leader_alpha", "1234", "Leader Alpha", UserRole.TEAM_LEADER, team_id=team1.id)
        create_user(db, "student1", "1234", "Student 1", UserRole.TEAM_MEMBER, team_id=team1.id)
        create_user(db, "student2", "1234", "Student 2", UserRole.TEAM_MEMBER, team_id=team1.id)

        team2 = create_team(db, "Team Beta (D)", GroupName.D)
        create_user(db, "leader_beta", "1234", "Leader Beta", UserRole.TEAM_LEADER, team_id=team2.id)
        create_user(db, "student3", "1234", "Student 3", UserRole.TEAM_MEMBER, team_id=team2.id)
        create_user(db, "student4", "1234", "Student 4", UserRole.TEAM_MEMBER, team_id=team2.id)

    db.close()
    print("Database initialization complete.")

if __name__ == "__main__":
    init_db()
