from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort
from sqlalchemy import or_
from config import Config, CATEGORIES, LOCATIONS
from database.models import db, Item, Claim
from services.matching import find_matches, match_label
from utils.helpers import login_required, save_image, delete_image, safe_next

bp = Blueprint("items", __name__)


def _can_edit(item):
    return g.user.is_admin or item.user_id == g.user.id


@bp.route("/items")
@login_required
def browse():
    q = request.args.get("q", "").strip()
    kind = request.args.get("kind", "")
    cat = request.args.get("category", "")
    status = request.args.get("status", "open")
    loc = request.args.get("location", "")
    page = request.args.get("page", 1, type=int)
    query = Item.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Item.title.ilike(like), Item.description.ilike(like), Item.location.ilike(like)))
    if kind in ("lost", "found"): query = query.filter_by(kind=kind)
    if cat in CATEGORIES: query = query.filter_by(category=cat)
    if loc in LOCATIONS: query = query.filter_by(location=loc)
    if status in ("open", "claimed", "returned", "closed"): query = query.filter_by(status=status)
    pagination = query.order_by(Item.created_at.desc()).paginate(page=page, per_page=Config.PAGE_SIZE, error_out=False)
    return render_template("items/browse.html", pagination=pagination, q=q, kind=kind, cat=cat,
                           status=status, loc=loc)


@bp.route("/my-items")
@login_required
def mine():
    items = Item.query.filter_by(user_id=g.user.id).order_by(Item.created_at.desc()).all()
    return render_template("items/mine.html", items=items)


@bp.route("/items/new", methods=["GET", "POST"])
@login_required
def new():
    kind = request.values.get("kind", "lost")
    if kind not in ("lost", "found"): kind = "lost"
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        desc = request.form.get("description", "").strip()
        category = request.form.get("category", "other")
        location = request.form.get("location", "")
        d = request.form.get("date_event", "")
        errors = []
        if len(title) < 3: errors.append("Give the item a short title (3+ characters).")
        if category not in CATEGORIES: category = "other"
        try:
            date_event = datetime.strptime(d, "%Y-%m-%d").date()
            if date_event > date.today(): errors.append("The date can't be in the future.")
        except ValueError:
            errors.append("Please pick a valid date."); date_event = date.today()
        image = ""
        if not errors:
            try:
                image = save_image(request.files.get("image"))
            except ValueError as e:
                errors.append(str(e))
        if errors:
            for e in errors: flash(e, "error")
        else:
            item = Item(kind=kind, title=title[:120], description=desc[:2000], category=category,
                        location=location[:80], date_event=date_event, image=image,
                        security_question=request.form.get("security_question", "").strip()[:200] if kind == "found" else "",
                        user_id=g.user.id)
            db.session.add(item); db.session.commit()
            matches = find_matches(item)
            if matches:
                flash(f"Report submitted — we found {len(matches)} possible match{'es' if len(matches) != 1 else ''}!", "success")
            else:
                flash("Report submitted. We'll notify you as soon as a match appears.", "success")
            return redirect(url_for("items.detail", item_id=item.id))
    return render_template("items/form.html", kind=kind, item=None, today=date.today().isoformat())


@bp.route("/items/<int:item_id>")
@login_required
def detail(item_id):
    item = Item.query.get_or_404(item_id)
    is_owner = item.user_id == g.user.id
    matches = []
    if is_owner or g.user.is_admin:
        matches = [{"item": o, "score": s, "label": match_label(s)} for o, s in find_matches(item, create_records=False)[:4]]
    claims, my_claim = [], None
    if item.kind == "found":
        if is_owner or g.user.is_admin:
            claims = item.claims.order_by(Claim.created_at.desc()).all()
        else:
            my_claim = item.claims.filter_by(claimant_id=g.user.id).order_by(Claim.created_at.desc()).first()
    return render_template("items/detail.html", item=item, is_owner=is_owner, matches=matches,
                           claims=claims, my_claim=my_claim)


@bp.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit(item_id):
    item = Item.query.get_or_404(item_id)
    if not _can_edit(item): abort(403)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if len(title) < 3:
            flash("Title is too short.", "error")
        else:
            try:
                new_img = save_image(request.files.get("image"))
            except ValueError as e:
                flash(str(e), "error")
                return redirect(request.url)
            if new_img:
                delete_image(item.image); item.image = new_img
            item.title = title[:120]
            item.description = request.form.get("description", "").strip()[:2000]
            c = request.form.get("category", "other"); item.category = c if c in CATEGORIES else "other"
            item.location = request.form.get("location", "")[:80]
            try:
                dt = datetime.strptime(request.form.get("date_event", ""), "%Y-%m-%d").date()
                if dt <= date.today(): item.date_event = dt
            except ValueError:
                pass
            if item.kind == "found":
                item.security_question = request.form.get("security_question", "").strip()[:200]
            db.session.commit()
            find_matches(item)
            flash("Report updated.", "success")
            return redirect(url_for("items.detail", item_id=item.id))
    return render_template("items/form.html", kind=item.kind, item=item, today=date.today().isoformat())


@bp.route("/items/<int:item_id>/status", methods=["POST"])
@login_required
def set_status(item_id):
    item = Item.query.get_or_404(item_id)
    if not _can_edit(item): abort(403)
    new = request.form.get("status")
    if new in ("open", "closed"):
        item.status = new
        db.session.commit()
        flash("Report reopened." if new == "open" else "Report closed.", "success")
    return redirect(url_for("items.detail", item_id=item.id))


@bp.route("/items/<int:item_id>/delete", methods=["POST"])
@login_required
def delete(item_id):
    item = Item.query.get_or_404(item_id)
    if not _can_edit(item): abort(403)
    from database.models import MatchRecord, Message
    MatchRecord.query.filter((MatchRecord.lost_id == item.id) | (MatchRecord.found_id == item.id)).delete()
    Message.query.filter_by(item_id=item.id).delete()
    delete_image(item.image)
    db.session.delete(item); db.session.commit()
    flash("Report deleted.", "success")
    return redirect(safe_next(request.form.get("next"), url_for("items.mine")))
