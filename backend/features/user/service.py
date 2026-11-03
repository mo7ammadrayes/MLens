import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# User service
from backend.features.user.model import User


class AccountLinkError(Exception):
    pass


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_or_create_auth_user(
    db: Session,
    *,
    auth_id: uuid.UUID,
    email: str | None,
    name: str | None,
    email_verified: bool,
) -> User:
    """Map a Supabase Auth identity to an application user row."""
    user = db.scalar(select(User).where(User.auth_id == auth_id))

    if user is not None:
        return user

    if not email:
        raise AccountLinkError("The account has no email address")

    email = email.strip().lower()

    existing = db.scalar(
        select(User).where(func.lower(User.email) == email)
    )

    if existing is not None:
        if existing.auth_id is not None:
            raise AccountLinkError(
                "This email is already linked to another account"
            )

        # Claim a pre-auth user row only with a confirmed email address.
        if not email_verified:
            raise AccountLinkError(
                "Confirm your email address to access this account"
            )

        existing.auth_id = auth_id

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(existing)
        return existing

    user = User(
        name=(name or "").strip() or email.split("@")[0],
        email=email,
        auth_id=auth_id,
    )

    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        # A concurrent first request may have created the row.
        db.rollback()
        user = db.scalar(select(User).where(User.auth_id == auth_id))
        if user is None:
            raise AccountLinkError(
                "This email is already linked to another account"
            )
        return user

    db.refresh(user)
    return user


def update_user_db(db: Session, user: User, changes: dict) -> User:
    for field, value in changes.items():
        setattr(user, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(user)
    return user
