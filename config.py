"""
Campus Lost & Found — config.py
Centralised configuration: reads .env and exposes all settings.
"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # ── Flask core ────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-change-me")
    APP_BASE_URL = os.environ.get(
        "APP_BASE_URL",
        os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000"),
    ).rstrip("/")
    DEMO_MODE = os.environ.get("DEMO_MODE", "1") == "1"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 days

    # ── Database / uploads ────────────────────────────────────────
    DATABASE = os.environ.get(
        "DATABASE_PATH", os.path.join(BASE_DIR, "instance", "lostfound.db")
    )
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(BASE_DIR, "static", "uploads")
    )
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB

    # ── Matching engine ───────────────────────────────────────────
    MATCH_THRESHOLD = 0.40       # minimum score (0-1) to count as a match
    MATCH_DATE_WINDOW_DAYS = 14

    PAGE_SIZE = 12


# category key -> (material icon, label, tint)
CATEGORIES = {
    "electronics": ("devices", "Electronics", "blue"),
    "id_cards": ("badge", "ID & Cards", "purple"),
    "books": ("menu_book", "Books & Notes", "amber"),
    "keys": ("key", "Keys", "teal"),
    "bags": ("backpack", "Bags", "green"),
    "clothing": ("checkroom", "Clothing", "pink"),
    "wallet": ("account_balance_wallet", "Wallets & Money", "red"),
    "accessories": ("watch", "Accessories", "blue"),
    "sports": ("sports_basketball", "Sports Gear", "amber"),
    "other": ("category", "Other", "slate"),
}

LOCATIONS = [
    "Main Library", "Cafeteria", "Admin Block", "Computer Lab",
    "Engineering Block", "Science Block", "Sports Complex", "Auditorium",
    "Hostel Area", "Parking Area", "Bus Stop", "Other",
]

STATUS_LABELS = {
    "open": "Open",
    "claimed": "Claim in progress",
    "returned": "Returned",
    "closed": "Closed",
}
