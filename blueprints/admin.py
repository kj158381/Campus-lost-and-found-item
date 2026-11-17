from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, flash, g, abort, url_for
from sqlalchemy import func
from config import CATEGORIES
from database.models import db, User, Item, Claim, MatchRecord, Message
from utils.helpers import admin_required, delete_image

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("")
@admin_required
def dashboard():
    stats = {
        "users": User.query.count(),
        "lost": Item.query.filter_by(kind="lost").count(),
        "found": Item.query.filter_by(kind="found").count(),
        "returned": Item.query.filter_by(status="returned").count(),
        "pending_claims": Claim.query.filter_by(status="pending").count(),
        "matches": MatchRecord.query.count(),
    }
    # last 14 days of reports
    days = [date.today() - timedelta(days=i) for i in range(13, -1, -1)]
    lost_by_day, found_by_day = [], []
    for d in days:
        lost_by_day.append(Item.query.filter(Item.kind == "lost", func.date(Item.created_at) == d.isoformat()).count())
        found_by_day.append(Item.query.filter(Item.kind == "found", func.date(Item.created_at) == d.isoformat()).count())
    cats = (db.session.query(Item.category, func.count(Item.id)).group_by(Item.category).all())
    locs = (db.session.query(Item.location, func.count(Item.id)).group_by(Item.location)
            .order_by(func.count(Item.id).desc()).limit(6).all())
    chart = {
        "days": [d.strftime("%d %b") for d in days], "lost": lost_by_day, "found": found_by_day,
        "cat_labels": [CATEGORIES.get(k, ("", k.title()))[1] for k, _ in cats], "cat_values": [v for _, v in cats],
        "loc_labels": [l or "Unknown" for l, _ in locs], "loc_values": [v for _, v in locs],
    }
    pending = Claim.query.filter_by(status="pending").order_by(Claim.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats, chart=chart, pending=pending)


@bp.route("/users")
@admin_required
def users():
    q = request.args.get("q", "").strip()
    query = User.query
    if q:
        query = query.filter(User.name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))
    return render_template("admin/users.html", users=query.order_by(User.created_at.desc()).all(), q=q)


@bp.route("/users/<int:uid>/role", methods=["POST"])
@admin_required
def set_role(uid):
    u = User.query.get_or_404(uid)
    role = request.form.get("role")
    if u.id == g.user.id:
        flash("You can't change your own role.", "error")
    elif role in ("student", "staff", "admin"):
        u.role = role; db.session.commit(); flash(f"{u.name} is now {role}.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:uid>/toggle", methods=["POST"])
@admin_required
def toggle_user(uid):
    u = User.query.get_or_404(uid)
    if u.id == g.user.id:
        flash("You can't deactivate yourself.", "error")
    else:
        u.is_active_user = not u.is_active_user; db.session.commit()
        flash(f"{u.name} {'reactivated' if u.is_active_user else 'deactivated'}.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/items")
@admin_required
def items():
    q = request.args.get("q", "").strip()
    query = Item.query
    if q:
        query = query.filter(Item.title.ilike(f"%{q}%"))
    return render_template("admin/items.html", items=query.order_by(Item.created_at.desc()).limit(200).all(), q=q)


@bp.route("/claims")
@admin_required
def claims():
    status = request.args.get("status", "")
    query = Claim.query
    if status in ("pending", "approved", "rejected", "completed"):
        query = query.filter_by(status=status)
    return render_template("admin/claims.html", claims=query.order_by(Claim.created_at.desc()).all(), status=status)
