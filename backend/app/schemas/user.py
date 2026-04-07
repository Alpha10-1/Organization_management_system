from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    disabled: bool = False


class UserPublic(UserBase):
    pass


class UserInDB(UserBase):
    hashed_password: str