# 🔎 Campus Lost & Found

A professional, full-stack **Flask + SQLite** web app where students and staff report lost or found items,
get **smart matches automatically**, chat privately, and recover belongings with a **QR hand-over pass**.
The app features a sidebar layout, blue/teal design system, and light + dark mode.

## ⚡ Quick start

**Windows:** double-click `run.bat`  
**Mac / Linux:** `./run.sh`

Or manually:

```bash
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5001** (or the port set in the `PORT` environment variable).

| Role    | Email               | Password     |
|---------|---------------------|--------------|
| Student | student@campus.edu  | student123   |
| Admin   | admin@campus.edu    | admin123     |
| Others  | priya@ / rahul@ / meera@campus.edu | student123 |

The login page also has one-click **Student / Admin demo buttons**. Demo login accounts are created on first run; reports start empty.
> Needs internet in the browser for Tailwind, Google Fonts, Material Icons and Chart.js (CDN).

## ✨ Features

- **Report lost / found items** with photo upload (drag & drop + preview), category, place and date
- **Smart matching engine** (`services/matching.py`): scores every lost↔found pair 0–100% using
  keyword overlap (40%), category (25%), location (20%) and date proximity (15%). Both owners are notified
- **Claim verification**: found items carry a *verification question*; claimants submit proof, the finder approves/rejects
- **QR hand-over pass**: approved claims get a unique QR code; the security desk scans it (camera or paste code) and confirms hand-over → item becomes *Returned*
- **Private AJAX chat** per item (auto-polling, no page reloads) + in-app **notifications** with live unread badges
- **Browse & filter**: search text, lost/found, category, location, status, pagination
- **Dashboard**: live stats, recovery rate, your top matches, category breakdown, recent reports
- **Admin panel**: Chart.js analytics (14-day trend, categories, hotspot locations), manage users/roles, all reports, all claims
- **Dark mode**, fully **mobile responsive** (slide-in sidebar)
- **Security**: hashed passwords, CSRF protection on every POST, safe redirects, validated image uploads (Pillow), role-based access, security headers

## 📁 Structure

```
campus_lostfound/
├── app.py                 # App factory, request lifecycle, error handlers
├── config.py              # Settings, categories, locations
├── requirements.txt · run.bat · run.sh · .env.example
├── database/models.py     # User, Item, MatchRecord, Claim, Message, Notification
├── blueprints/            # 7 blueprints
│   ├── auth.py            #   login / register / demo login / logout
│   ├── main.py            #   dashboard, profile, notifications
│   ├── items.py           #   browse, report, detail, edit, delete
│   ├── claims.py          #   claims, QR pass, hand-over verification
│   ├── chat.py            #   inbox, thread, AJAX message API
│   ├── admin.py           #   analytics, users, reports, claims
│   └── api.py             #   counts, matches, stats JSON endpoints
├── services/              # matching.py · qr_service.py · notifications.py · seed.py
├── utils/helpers.py       # auth decorators, CSRF, safe image upload, time_ago
├── templates/             # base, dashboard, auth/, items/, claims/, chat/, admin/
├── static/                # css/main.css · js/main.js · js/chat.js · uploads/
└── instance/lostfound.db  # SQLite (auto-created)
```

## 🔧 Configuration (`.env`)

| Variable      | Purpose                                              |
|---------------|------------------------------------------------------|
| `SECRET_KEY`  | Session signing key — **change in production**       |
| `APP_BASE_URL`| URL encoded into QR codes (use your LAN/public URL so phones can scan) |
| `DEMO_MODE`   | `1` shows demo-login buttons, `0` hides them         |

To reset all data, stop the app and delete `instance/lostfound.db`.

## 🚀 Deploy to Render

1. Push this project to GitHub.
2. In Render, choose **New → Blueprint** and select the repository. Render reads `render.yaml`,
   builds the app, and creates a 1 GB persistent disk for the SQLite database and image uploads.
   The blueprint uses a paid Starter web service because Render disks are not available on free web services.
3. After deployment, open the generated `onrender.com` URL and register your account. The production
   configuration generates a secret key and disables demo accounts and one-click demo login.
4. To make your account an administrator, open the Render Shell and run the following, replacing
   the email with the address you registered:

   ```bash
   python -c "from app import app; from database.models import db, User; app.app_context().push(); user = User.query.filter_by(email='you@example.com').one(); user.role = 'admin'; db.session.commit()"
   ```

For a custom domain, set `APP_BASE_URL` in the Render environment to the public site URL so QR
handover links point to the correct address. The `192.168.1.1` address is private to your local
network and is not the public deployment URL.

The Render disk stores both uploads and SQLite data between deploys. Keep `SECRET_KEY` private
and do not enable `DEMO_MODE` on a public production deployment.

## 🧠 How the flow works

1. **Aarav** reports a *lost* black laptop bag → engine finds Priya's *found* backpack (82%) → both get notified
2. Aarav opens it and submits a **claim** answering the finder's verification question
3. **Priya** approves → Aarav gets a **QR pass**
4. At the security desk the admin scans the pass → **Confirm hand-over** → item is *Returned*, stats update
