from sqlalchemy.orm import Session
from datetime import datetime
import database
import schemas
import auth

# --- USER CRUD ---

def get_user_by_username(db: Session, username: str):
    return db.query(database.User).filter(database.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(database.User).filter(database.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_pwd = auth.get_password_hash(user.password)
    db_user = database.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pwd,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- ACCESS LOGS CRUD ---

def create_access_log(db: Session, name: str, status: str, confidence: float, signal_sent: str):
    log = database.AccessLog(
        name=name,
        status=status,
        confidence=confidence,
        signal_sent=signal_sent
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def get_access_logs(db: Session, limit: int = 100, status: str = None):
    query = db.query(database.AccessLog)
    if status:
        query = query.filter(database.AccessLog.status == status)
    return query.order_by(database.AccessLog.timestamp.desc()).limit(limit).all()

# --- INTRUDER ALERTS CRUD ---

def create_intruder_alert(db: Session, snapshot_path: str, email_sent: bool):
    alert = database.IntruderAlert(
        snapshot_path=snapshot_path,
        email_sent=email_sent
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert

def get_intruder_alerts(db: Session, limit: int = 100):
    return db.query(database.IntruderAlert).order_by(database.IntruderAlert.timestamp.desc()).limit(limit).all()

def delete_intruder_alert(db: Session, alert_id: int):
    alert = db.query(database.IntruderAlert).filter(database.IntruderAlert.id == alert_id).first()
    if alert:
        db.delete(alert)
        db.commit()
        return True
    return False

# --- AUTHORIZED USER CRUD ---

def get_authorized_users(db: Session):
    return db.query(database.AuthorizedUser).all()

def get_authorized_user_by_name(db: Session, name: str):
    return db.query(database.AuthorizedUser).filter(database.AuthorizedUser.name == name).first()

def create_authorized_user(db: Session, name: str, image_count: int):
    existing = get_authorized_user_by_name(db, name)
    if existing:
        existing.image_count = image_count
        existing.created_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
        
    user = database.AuthorizedUser(
        name=name,
        image_count=image_count
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def remove_authorized_user(db: Session, name: str):
    user = get_authorized_user_by_name(db, name)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False

# --- NOTIFICATIONS CRUD ---

def create_notification(db: Session, message: str, type: str):
    notification = database.Notification(
        message=message,
        type=type
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification

def get_notifications(db: Session, limit: int = 50, unread_only: bool = False):
    query = db.query(database.Notification)
    if unread_only:
        query = query.filter(database.Notification.is_read == False)
    return query.order_by(database.Notification.timestamp.desc()).limit(limit).all()

def mark_notifications_as_read(db: Session):
    unread = db.query(database.Notification).filter(database.Notification.is_read == False).all()
    for n in unread:
        n.is_read = True
    db.commit()
    return len(unread)
