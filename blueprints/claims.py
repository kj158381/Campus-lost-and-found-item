from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for, flash, g, abort, Response)
from database.models import db, Item, Claim, Message
from services.notifications import notify
from services.qr_service import qr_png_bytes, verify_url
from utils.helpers import login_required

bp = Blueprint("claims", __name__)


def _owner_or_admin(claim):
    return g.user.is_admin or claim.item.user_id == g.user.id


@bp.route("/items/<int:item_id>/claim", methods=["POST"])
@login_required
def create(item_id):
    item = Item.query.get_or_404(item_id)
    proof = request.form.get("proof", "").strip()
    if item.kind != "found" or item.status != "open":
        flash("This item can't be claimed right now.", "error")
    elif item.user_id == g.user.id:
        flash("You can't claim your own found report.", "error")
    elif len(proof) < 8:
        flash("Please describe proof of ownership (at least a sentence).", "error")
    elif item.claims.filter(Claim.claimant_id == g.user.id, Claim.status.in_(["pending", "approved"])).first():
        flash("You already have an active claim on this item.", "error")
    else:
        c = Claim(item_id=item.id, claimant_id=g.user.id, proof=proof[:1000])
        db.session.add(c)
        notify(item.user_id, "New ownership claim",
               f"{g.user.name} says “{item.title}” is theirs. Review their proof.", f"/items/{item.id}", "claim")
        db.session.commit()
        flash("Claim sent! The finder will review your proof and respond.", "success")
    return redirect(url_for("items.detail", item_id=item_id))


@bp.route("/items/<int:item_id>/i-found-it", methods=["POST"])
@login_required
def i_found_it(item_id):
    item = Item.query.get_or_404(item_id)
    if item.kind != "lost" or item.user_id == g.user.id:
        abort(400)
    notify(item.user_id, "Someone may have found your item",
           f"{g.user.name} says they found “{item.title}”. Open the chat to follow up.",
           url_for("chat.thread", item_id=item.id, other_id=g.user.id), "match")
    db.session.add(Message(item_id=item.id, sender_id=g.user.id, recipient_id=item.user_id,
                           body=f"Hi! I think I found your “{item.title}”. Can you describe it so we can confirm?"))
    db.session.commit()
    return redirect(url_for("chat.thread", item_id=item.id, other_id=item.user_id))


@bp.route("/claims")
@login_required
def listing():
    mine = (Claim.query.filter_by(claimant_id=g.user.id).order_by(Claim.created_at.desc()).all())
    incoming = (Claim.query.join(Item).filter(Item.user_id == g.user.id).order_by(Claim.created_at.desc()).all())
    return render_template("claims/list.html", mine=mine, incoming=incoming)


@bp.route("/claims/<int:cid>")
@login_required
def view(cid):
    c = Claim.query.get_or_404(cid)
    if not (c.claimant_id == g.user.id or _owner_or_admin(c)):
        abort(403)
    return render_template("claims/pass.html", c=c, verify_url=verify_url(c.qr_token) if c.qr_token else "")


@bp.route("/claims/<int:cid>/qr.png")
@login_required
def qr(cid):
    c = Claim.query.get_or_404(cid)
    if not (c.claimant_id == g.user.id or _owner_or_admin(c)) or c.status not in ("approved", "completed") or not c.qr_token:
        abort(403)
    return Response(qr_png_bytes(c.qr_token), mimetype="image/png", headers={"Cache-Control": "private, max-age=300"})


@bp.route("/claims/<int:cid>/approve", methods=["POST"])
@login_required
def approve(cid):
    c = Claim.query.get_or_404(cid)
    if not _owner_or_admin(c): abort(403)
    if c.status != "pending" or c.item.status != "open":
        flash("This claim can no longer be approved.", "error")
        return redirect(url_for("items.detail", item_id=c.item_id))
    c.status = "approved"; c.issue_token(); c.item.status = "claimed"
    notify(c.claimant_id, "Claim approved 🎉",
           f"Your claim on “{c.item.title}” was approved. Show your QR pass when collecting it.",
           url_for("claims.view", cid=c.id), "success")
    for other in c.item.claims.filter(Claim.id != c.id, Claim.status == "pending").all():
        other.status = "rejected"; other.resolved_at = datetime.utcnow()
        notify(other.claimant_id, "Claim not approved",
               f"Another claim on “{c.item.title}” was approved first.", f"/items/{c.item_id}", "info")
    db.session.commit()
    flash("Claim approved. A QR pass was issued to the claimant.", "success")
    return redirect(url_for("items.detail", item_id=c.item_id))


@bp.route("/claims/<int:cid>/reject", methods=["POST"])
@login_required
def reject(cid):
    c = Claim.query.get_or_404(cid)
    if not _owner_or_admin(c): abort(403)
    if c.status == "pending":
        c.status = "rejected"; c.resolved_at = datetime.utcnow()
        notify(c.claimant_id, "Claim not approved",
               f"The finder couldn't verify your claim on “{c.item.title}”.", f"/items/{c.item_id}", "info")
        db.session.commit()
        flash("Claim rejected.", "success")
    return redirect(url_for("items.detail", item_id=c.item_id))


# ── Hand-over verification (QR scan target) ─────────────────────
@bp.route("/verify", methods=["GET", "POST"])
@login_required
def verify_home():
    if request.method == "POST":
        token = request.form.get("token", "").strip().rstrip("/").split("/")[-1]
        if token and Claim.query.filter_by(qr_token=token).first():
            return redirect(url_for("claims.verify", token=token))
        flash("No claim found for that code.", "error")
    return render_template("claims/verify.html", c=None)


@bp.route("/verify/<token>")
@login_required
def verify(token):
    c = Claim.query.filter_by(qr_token=token).first_or_404()
    if not _owner_or_admin(c):
        abort(403)
    return render_template("claims/verify.html", c=c)


@bp.route("/verify/<token>/complete", methods=["POST"])
@login_required
def complete(token):
    c = Claim.query.filter_by(qr_token=token).first_or_404()
    if not _owner_or_admin(c): abort(403)
    if c.status == "approved":
        c.status = "completed"; c.resolved_at = datetime.utcnow(); c.item.status = "returned"
        notify(c.claimant_id, "Item handed over", f"“{c.item.title}” was marked as returned to you.", "", "success")
        notify(c.item.user_id, "Hand-over confirmed", f"“{c.item.title}” is marked as returned. Thank you!", "", "success")
        db.session.commit()
        flash("Hand-over confirmed. Item marked as returned.", "success")
    return redirect(url_for("claims.verify", token=token))
