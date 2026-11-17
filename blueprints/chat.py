from flask import Blueprint, render_template, request, jsonify, g, abort
from sqlalchemy import or_, and_
from database.models import db, Item, User, Message
from services.notifications import notify
from utils.helpers import login_required, time_ago

bp = Blueprint("chat", __name__)


def _validate(item_id, other_id):
    item = Item.query.get_or_404(item_id)
    other = User.query.get_or_404(other_id)
    # Conversations must involve the item's owner, so users can't DM arbitrarily.
    if other.id == g.user.id or item.user_id not in (g.user.id, other.id):
        abort(403)
    return item, other


def _thread_filter(item_id, other_id):
    me = g.user.id
    return and_(Message.item_id == item_id, or_(
        and_(Message.sender_id == me, Message.recipient_id == other_id),
        and_(Message.sender_id == other_id, Message.recipient_id == me)))


def _serialize(m):
    return {"id": m.id, "body": m.body, "mine": m.sender_id == g.user.id,
            "time": m.created_at.strftime("%H:%M"), "day": m.created_at.strftime("%d %b")}


@bp.route("/chat")
@login_required
def inbox():
    me = g.user.id
    msgs = (Message.query.filter(or_(Message.sender_id == me, Message.recipient_id == me))
            .order_by(Message.created_at.desc()).all())
    threads = {}
    for m in msgs:
        other = m.recipient if m.sender_id == me else m.sender
        key = (m.item_id, other.id)
        t = threads.setdefault(key, {"item": m.item, "other": other, "last": m, "unread": 0})
        if m.recipient_id == me and not m.is_read:
            t["unread"] += 1
    return render_template("chat/inbox.html", threads=list(threads.values()), time_ago=time_ago)


@bp.route("/chat/<int:item_id>/<int:other_id>")
@login_required
def thread(item_id, other_id):
    item, other = _validate(item_id, other_id)
    msgs = Message.query.filter(_thread_filter(item_id, other_id)).order_by(Message.id).all()
    Message.query.filter(_thread_filter(item_id, other_id), Message.recipient_id == g.user.id,
                         Message.is_read == False).update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return render_template("chat/thread.html", item=item, other=other, msgs=msgs,
                           last_id=msgs[-1].id if msgs else 0)


@bp.route("/api/chat/<int:item_id>/<int:other_id>/messages", methods=["GET", "POST"])
@login_required
def api_messages(item_id, other_id):
    item, other = _validate(item_id, other_id)
    if request.method == "POST":
        body = ((request.get_json(silent=True) or {}).get("body") or "").strip()
        if not body or len(body) > 1000:
            return jsonify(error="Message must be 1-1000 characters."), 400
        m = Message(item_id=item.id, sender_id=g.user.id, recipient_id=other.id, body=body)
        db.session.add(m)
        # one unread-message notification per burst (avoid spam)
        notify(other.id, f"New message from {g.user.first_name}", body[:120],
               f"/chat/{item.id}/{g.user.id}", "message")
        db.session.commit()
        return jsonify(message=_serialize(m))
    after = request.args.get("after", 0, type=int)
    msgs = (Message.query.filter(_thread_filter(item_id, other_id), Message.id > after)
            .order_by(Message.id).all())
    for m in msgs:
        if m.recipient_id == g.user.id and not m.is_read:
            m.is_read = True
    db.session.commit()
    return jsonify(messages=[_serialize(m) for m in msgs])
