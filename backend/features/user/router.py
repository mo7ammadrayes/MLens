
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.features.user.schemas import AddUser, UpdateUser
from backend.features.user.service import (
    create_user,
    get_user_by_id,
    get_all_users,
    update_user_db,
    delete_user_db,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user_by_id(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
    }


@router.get("")
def get_users(db: Session = Depends(get_db)):
    users = get_all_users(db)

    final_results = []

    for user in users:
        result = {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
        }
        final_results.append(result)

    return final_results



@router.post("", status_code=201)
def adding_user(user: AddUser, db: Session = Depends(get_db)):
    try:
        saved_user = create_user(
            db,
            name=user.name,
            email=str(user.email),
            phone=user.phone,
        )
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise HTTPException(
                status_code=409,
                detail="Email already exists",
            ) from error
        raise

    return {
        "user_id": saved_user.user_id,
        "name": saved_user.name,
        "email": saved_user.email,
        "phone": saved_user.phone,
    }



@router.patch("/{user_id}")
def update_user(
    user_id: int,
    user: UpdateUser,
    db: Session = Depends(get_db),
):
    changes = user.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    if any(
        field in changes and changes[field] is None
        for field in ("name", "email")
    ):
        raise HTTPException(
            status_code=422,
            detail="Name and email cannot be null",
        )

    try:
        updated_user = update_user_db(db, user_id, changes)
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise HTTPException(
                status_code=409,
                detail="Email already exists",
            ) from error
        raise

    if updated_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return {
        "user_id": updated_user.user_id,
        "name": updated_user.name,
        "email": updated_user.email,
        "phone": updated_user.phone,
    }



@router.delete("/{user_id}")
def delete_user(user_id: int,db: Session = Depends(get_db)):
    deleted = delete_user_db(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
