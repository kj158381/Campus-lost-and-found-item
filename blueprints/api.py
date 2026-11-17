from flask import Blueprint, jsonify, g
from database.models import Notification, Message, Item
from services.matching import find_matches, match_label
from utils.helpers import login_required

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/counts")
@login_required
def counts():
    return jsonify(
        notifications=Notification.query.filter_by(user_id=g.user.id, is_read=False).count(),
        messages=Message.query.filter_by(recipient_id=g.user.id, is_read=False).count())


@bp.route("/matches/<int:item_id>")
@login_required
def matches(item_id):
    item = Item.query.get_or_404(item_id)
    if item.user_id != g.user.id and not g.user.is_admin:
        return jsonify(error="forbidden"), 403
    return jsonify(matches=[{"id": o.id, "title": o.title, "score": s, "label": match_label(s),
                             "location": o.location} for o, s in find_matches(item, create_records=False)[:6]])


@bp.route("/stats")
@login_required
def stats():
    return jsonify(lost=Item.query.filter_by(kind="lost", status="open").count(),
                   found=Item.query.filter_by(kind="found", status="open").count(),
                   returned=Item.query.filter_by(status="returned").count())
