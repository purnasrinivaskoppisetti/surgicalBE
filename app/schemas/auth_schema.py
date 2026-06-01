from pydantic import BaseModel
from pydantic import EmailStr


class AdminRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str


class UserRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str