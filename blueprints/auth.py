import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from config import Config
from database.models import db, User, AVATAR_COLORS
from utils.helpers import safe_next

bp = Blueprint("auth", __name__)

DEMO_ACCOUNTS = {"student": "student@campus.edu", "admin": "admin@campus.edu"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _login(user):
    session.clear()
    session.permanent = True
    session["uid"] = user.id


@bp.route("/")
def index():
    return redirect(url_for("main.dashboard") if g.user else url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(pw):
            if not user.is_active_user:
                flash("This account has been deactivated. Contact the security desk.", "error")
            else:
                _login(user)
                return redirect(safe_next(request.args.get("next")))
        else:
            flash("Incorrect email or password.", "error")
    return render_template("auth/login.html", demo=Config.DEMO_MODE)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        dept = request.form.get("department", "").strip()
        pw = request.form.get("password", "")
        errors = []
        if len(name) < 2: errors.append("Please enter your full name.")
        if not EMAIL_RE.match(email): errors.append("Enter a valid email address.")
        if len(pw) < 6: errors.append("Password must be at least 6 characters.")
        if User.query.filter_by(email=email).first(): errors.append("An account with this email already exists.")
        if errors:
            for e in errors: flash(e, "error")
        else:
            u = User(name=name, email=email, department=dept,
                     avatar_color=AVATAR_COLORS[User.query.count() % len(AVATAR_COLORS)])
            u.set_password(pw)
            db.session.add(u); db.session.commit()
            _login(u)
            flash(f"Welcome to Campus Lost & Found, {u.first_name}!", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html")


@bp.route("/auth/demo/<role>", methods=["POST"])
def demo(role):
    if not Config.DEMO_MODE or role not in DEMO_ACCOUNTS:
        flash("Demo login is disabled.", "error")
        return redirect(url_for("auth.login"))
    user = User.query.filter_by(email=DEMO_ACCOUNTS[role]).first()
    if not user:
        flash("Demo account not found.", "error")
        return redirect(url_for("auth.login"))
    _login(user)
    return redirect(url_for("main.dashboard"))


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))
