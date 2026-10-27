from sqlalchemy.orm import Session
from sqlalchemy import select
# User service
from backend.features.user.model import User

def create_user(
    db: Session,
    name: str,
    email: str,
    phone: str | None,
) -> User:
    user = User(name=name, email=email, phone=phone)

    try:
        db.add(user)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(user)
    return user

def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)

def get_all_users(db: Session) -> list[User]:
    return db.scalars(select(User)).all()


def update_user_db(db: Session,user_id, changes) ->User | None:
    user = db.get(User, user_id)

    if user is None:
        return None

    for field, value in changes.items():
        setattr(user, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(user)
    return user

def delete_user_db(db: Session, user_id: int) -> bool:
    user = db.get(User, user_id)

    if user is None:
        return False

    db.delete(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return True

