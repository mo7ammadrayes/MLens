from pydantic import BaseModel, EmailStr


class AddUser(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None


class UpdateUser(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None