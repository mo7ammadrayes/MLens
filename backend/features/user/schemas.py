from pydantic import BaseModel, Field


class UpdateUser(BaseModel):
    # Email is owned by Supabase Auth and changed there.
    name: str | None = Field(default=None, min_length=1)
    phone: str | None = None
