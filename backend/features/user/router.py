from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth.dependencies import CurrentUser
from backend.database.session import get_db
from backend.features.user.schemas import UpdateUser
from backend.features.user.service import update_user_db

router = APIRouter(prefix="/users", tags=["Users"])


def user_response(user):
    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
    }


@router.get("/me")
def get_me(user: CurrentUser):
    return user_response(user)


@router.patch("/me")
def update_me(
    changes: UpdateUser,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    values = changes.model_dump(exclude_unset=True)

    if not values:
        raise HTTPException(400, "No fields provided for update")

    if "name" in values and values["name"] is None:
        raise HTTPException(422, "Name cannot be null")

    return user_response(update_user_db(db, user, values))
