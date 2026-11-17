"""
app.py — Campus Lost & Found
Flask application factory. Run with:  python app.py
"""
import os, logging
from datetime import datetime
from flask import Flask, g, session, render_template, request, jsonify
from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import Config, CATEGORIES, LOCATIONS, STATUS_LABELS
from database.models import db, User, Notification, Message
from utils.helpers import csrf_token, check_csrf, time_ago

logging.basicConfig(level=logging.INFO)


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_conn, _):
    try:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
    except Exception:
        pass


def create_app():
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=Config.SECRET_KEY,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=Config.PERMANENT_SESSION_LIFETIME,
        MAX_CONTENT_LENGTH=Config.MAX_CONTENT_LENGTH,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{Config.DATABASE}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    os.makedirs(os.path.dirname(Config.DATABASE), exist_ok=True)
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        if Config.DEMO_MODE:
            from services.seed import seed_demo
            seed_demo()

    # ── Blueprints (7) ────────────────────────────────────────
    from blueprints import auth, main, items, claims, chat, admin, api
    for m in (auth, main, items, claims, chat, admin, api):
        app.register_blueprint(m.bp)

    # ── Request lifecycle ─────────────────────────────────────
    @app.before_request
    def load_user():
        g.user = None
        uid = session.get("uid")
        if uid:
            u = db.session.get(User, uid)
            if u and u.is_active_user:
                g.user = u
            else:
                session.clear()
        check_csrf()

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        return resp

    @app.context_processor
    def inject():
        ctx = dict(CATEGORIES=CATEGORIES, LOCATIONS=LOCATIONS, STATUS_LABELS=STATUS_LABELS,
                   csrf_token=csrf_token, time_ago=time_ago, user=g.get("user"), unread_notes=0, unread_msgs=0)
        if g.get("user"):
            ctx["unread_notes"] = Notification.query.filter_by(user_id=g.user.id, is_read=False).count()
            ctx["unread_msgs"] = Message.query.filter_by(recipient_id=g.user.id, is_read=False).count()
        return ctx

    # ── Errors ────────────────────────────────────────────────
    def _err(code, title, msg):
        if request.path.startswith("/api/"):
            return jsonify(error=msg), code
        return render_template("error.html", code=code, title=title, msg=msg), code

    app.register_error_handler(400, lambda e: _err(400, "Bad request", getattr(e, "description", "Bad request.")))
    app.register_error_handler(403, lambda e: _err(403, "Access denied", "You don't have permission to view this page."))
    app.register_error_handler(404, lambda e: _err(404, "Page not found", "We couldn't find what you were looking for."))
    app.register_error_handler(413, lambda e: _err(413, "File too large", "Images must be under 5 MB."))
    app.register_error_handler(500, lambda e: _err(500, "Something went wrong", "An unexpected error occurred. Please try again."))
    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    print(f"\n  Campus Lost & Found running at  http://localhost:{port}\n"
          "  Demo logins:  student@campus.edu / student123   |   admin@campus.edu / admin123\n")
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "1") == "1")
