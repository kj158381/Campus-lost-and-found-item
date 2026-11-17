from database.models import db, Notification


def notify(user_id, title, body="", link="", kind="info"):
    db.session.add(Notification(user_id=user_id, title=title, body=body[:300], link=link, kind=kind))
