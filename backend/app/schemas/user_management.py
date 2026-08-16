from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "staff"
    department_id: int | None = None
    position: str | None = None
    manager_id: int | None = None

class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    disabled: bool | None = None
    department_id: int | None = None
    position: str | None = None
    manager_id: int | None = None

class UserRoleUpdate(BaseModel):
    role: str

class UserStatusUpdate(BaseModel):
    disabled: bool

class UserDepartmentUpdate(BaseModel):
    department_id: int | None = None

class UserPositionUpdate(BaseModel):
    position: str | None = None
    manager_id: int | None = None

class UserManagementOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    disabled: bool
    department_id: int | None = None
    position: str | None = None
    manager_id: int | None = None
    is_verified: bool = False

    model_config = {"from_attributes": True}