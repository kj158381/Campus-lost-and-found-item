"""Create demo login accounts on the first run."""
from database.models import db, User, AVATAR_COLORS


def _user(name, email, pw, role="student", dept=""):
    u = User(name=name, email=email, role=role, department=dept,
             avatar_color=AVATAR_COLORS[User.query.count() % len(AVATAR_COLORS)])
    u.set_password(pw)
    db.session.add(u)
    db.session.flush()
    return u


def seed_demo():
    if User.query.first():
        return
    _user("Campus Security Desk", "admin@campus.edu", "admin123", "admin", "Security")
    _user("Aarav Sharma", "student@campus.edu", "student123", "student", "Computer Science")
    _user("Priya Nair", "priya@campus.edu", "student123", "student", "Electronics")
    _user("Rahul Verma", "rahul@campus.edu", "student123", "student", "Mechanical")
    _user("Meera Iyer", "meera@campus.edu", "student123", "student", "Biotechnology")
    db.session.commit()
