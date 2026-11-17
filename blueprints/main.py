from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, flash, g, abort
from sqlalchemy import func, or_
from config import Config, CATEGORIES
from database.models import db, Item, MatchRecord, Claim, Notification, User
from utils.helpers import login_required

bp = Blueprint("main", __name__)


@bp.route("/dashboard")
@login_required
def dashboard():
    uid = g.user.id
    total_lost = Item.query.filter_by(kind="lost", status="open").count()
    total_found = Item.query.filter_by(kind="found", status="open").count()
    returned = Item.query.filter_by(status="returned").count()
    total_all = Item.query.count()
    recovery_rate = round(returned / total_all * 100) if total_all else 0
    my_open = Item.query.filter_by(user_id=uid).filter(Item.status.in_(["open", "claimed"])).count()

    # Top matches that involve MY items
    my_ids = [i.id for i in Item.query.filter_by(user_id=uid).all()]
    matches = []
    if my_ids:
        recs = (MatchRecord.query.filter(or_(MatchRecord.lost_id.in_(my_ids), MatchRecord.found_id.in_(my_ids)))
                .order_by(MatchRecord.score.desc()).limit(4).all())
        for r in recs:
            mine, other = (r.lost, r.found) if r.lost.user_id == uid else (r.found, r.lost)
            if mine.status == "open" and other.status == "open":
                matches.append({"mine": mine, "other": other, "score": r.score})

    recent = Item.query.filter_by(status="open").order_by(Item.created_at.desc()).limit(6).all()
    cat_rows = (db.session.query(Item.category, func.count(Item.id)).filter(Item.status == "open")
                .group_by(Item.category).order_by(func.count(Item.id).desc()).limit(6).all())
    cat_max = max([c for _, c in cat_rows], default=1)
    incoming = (Claim.query.join(Item).filter(Item.user_id == uid, Claim.status == "pending").count())
    return render_template("dashboard.html", total_lost=total_lost, total_found=total_found,
                           returned=returned, recovery_rate=recovery_rate, my_open=my_open,
                           matches=matches, recent=recent, cat_rows=cat_rows, cat_max=cat_max,
                           incoming=incoming, hour=__import__("datetime").datetime.now().hour)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    u = g.user
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if len(name) < 2:
            flash("Name is too short.", "error")
        else:
            u.name = name
            u.department = request.form.get("department", "").strip()[:80]
            u.phone = request.form.get("phone", "").strip()[:30]
            new_pw = request.form.get("new_password", "")
            if new_pw:
                if not u.check_password(request.form.get("current_password", "")):
                    flash("Current password is incorrect.", "error")
                    return redirect("/profile")
                if len(new_pw) < 6:
                    flash("New password must be at least 6 characters.", "error")
                    return redirect("/profile")
                u.set_password(new_pw)
            db.session.commit()
            flash("Profile updated.", "success")
        return redirect("/profile")
    mine = Item.query.filter_by(user_id=u.id)
    stats = {"reports": mine.count(), "returned": mine.filter_by(status="returned").count(),
             "claims": Claim.query.filter_by(claimant_id=u.id).count()}
    return render_template("profile.html", stats=stats)


@bp.route("/notifications")
@login_required
def notifications():
    notes = (Notification.query.filter_by(user_id=g.user.id)
             .order_by(Notification.created_at.desc()).limit(80).all())
    return render_template("notifications.html", notes=notes)


@bp.route("/notifications/read-all", methods=["POST"])
@login_required
def read_all():
    Notification.query.filter_by(user_id=g.user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return redirect("/notifications")


@bp.route("/notifications/<int:nid>/go")
@login_required
def go(nid):
    n = Notification.query.get_or_404(nid)
    if n.user_id != g.user.id:
        abort(403)
    n.is_read = True
    db.session.commit()
    return redirect(n.link or "/notifications")
