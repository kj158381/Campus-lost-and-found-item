import os, uuid, secrets
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, request, abort, g, flash, jsonify
from PIL import Image
from werkzeug.utils import secure_filename
from config import Config
from database.models import db, User


# ── Auth decorators ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not getattr(g, "user", None):
            if request.path.startswith("/api/"):
                return jsonify(error="auth required"), 401
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return f(*a, **kw)
    return wrapper


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*a, **kw):
        if not g.user.is_admin:
            abort(403)
        return f(*a, **kw)
    return wrapper


def safe_next(url, default="/dashboard"):
    """Block open redirects."""
    if not url or not isinstance(url, str) or not url.startswith("/") or url.startswith("//"):
        return default
    return url


# ── CSRF ───────────────────────────────────────────────────────
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def check_csrf():
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        sent = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
        if not sent or sent != session.get("_csrf"):
            abort(400, "Invalid or missing CSRF token. Refresh the page and try again.")


# ── Uploads ────────────────────────────────────────────────────
def save_image(file_storage):
    """Validate + store an uploaded image. Returns filename or '' ."""
    if not file_storage or not file_storage.filename:
        return ""
    ext = secure_filename(file_storage.filename).rsplit(".", 1)[-1].lower()
    if ext not in Config.ALLOWED_EXTENSIONS:
        raise ValueError("Only PNG, JPG, GIF or WEBP images are allowed.")
    try:
        img = Image.open(file_storage.stream)
        img.verify()
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream)
        img = img.convert("RGB") if img.mode in ("P", "RGBA", "LA") and ext in ("jpg", "jpeg") else img
        img.thumbnail((1280, 1280))
    except Exception:
        raise ValueError("That file is not a valid image.")
    name = f"{uuid.uuid4().hex}.{'jpg' if ext == 'jpeg' else ext}"
    img.save(os.path.join(Config.UPLOAD_FOLDER, name))
    return name


def delete_image(name):
    if name:
        try:
            os.remove(os.path.join(Config.UPLOAD_FOLDER, name))
        except OSError:
            pass


def time_ago(dt):
    if not dt:
        return ""
    s = (datetime.utcnow() - dt).total_seconds()
    if s < 60: return "just now"
    if s < 3600: return f"{int(s // 60)}m ago"
    if s < 86400: return f"{int(s // 3600)}h ago"
    if s < 86400 * 7: return f"{int(s // 86400)}d ago"
    return dt.strftime("%d %b %Y")
