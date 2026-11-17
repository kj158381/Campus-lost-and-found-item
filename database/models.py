"""SQLAlchemy ORM models."""
import secrets
from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

AVATAR_COLORS = ["#006BFF", "#00C2A8", "#8B5CF6", "#F59E0B", "#EF4444", "#10B981", "#EC4899"]


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="student")  # student | staff | admin
    department = db.Column(db.String(80), default="")
    phone = db.Column(db.String(30), default="")
    avatar_color = db.Column(db.String(10), default="#006BFF")
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("Item", backref="owner", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def initials(self):
        parts = self.name.split()
        return "".join(p[0] for p in parts[:2]).upper() or "U"

    @property
    def first_name(self):
        return self.name.split()[0] if self.name else "there"


class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(10), nullable=False, index=True)  # lost | found
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(30), default="other", index=True)
    location = db.Column(db.String(80), default="")
    date_event = db.Column(db.Date, default=date.today)
    image = db.Column(db.String(200), default="")
    status = db.Column(db.String(20), default="open", index=True)  # open|claimed|returned|closed
    # For FOUND items: a question only the real owner can answer (never shown publicly with the answer)
    security_question = db.Column(db.String(200), default="")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    claims = db.relationship("Claim", backref="item", lazy="dynamic", cascade="all, delete-orphan")


class MatchRecord(db.Model):
    __tablename__ = "matches"
    id = db.Column(db.Integer, primary_key=True)
    lost_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    found_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("lost_id", "found_id", name="uq_match_pair"),)

    lost = db.relationship("Item", foreign_keys=[lost_id])
    found = db.relationship("Item", foreign_keys=[found_id])


class Claim(db.Model):
    __tablename__ = "claims"
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    claimant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    proof = db.Column(db.Text, default="")         # claimant's answer / description of proof
    status = db.Column(db.String(20), default="pending")  # pending|approved|rejected|completed
    qr_token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    claimant = db.relationship("User", foreign_keys=[claimant_id])

    def issue_token(self):
        self.qr_token = secrets.token_urlsafe(18)


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    item = db.relationship("Item")
    sender = db.relationship("User", foreign_keys=[sender_id])
    recipient = db.relationship("User", foreign_keys=[recipient_id])


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    kind = db.Column(db.String(20), default="info")  # info|match|claim|message|success
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.String(300), default="")
    link = db.Column(db.String(200), default="")
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
