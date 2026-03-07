from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "VENTAS"


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class PasswordChange(BaseModel):
    new_password: str
