from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "staff"

class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    disabled: bool | None = None

class UserRoleUpdate(BaseModel):
    role: str

class UserStatusUpdate(BaseModel):
    disabled: bool

class UserManagementOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    disabled: bool