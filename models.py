from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    username: str

class User(UserBase):
    password: str

class UserInDB(UserBase):
    hashed_password: str
    role: str = "user"

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None

class TodoCreate(TodoBase):
    pass

class TodoUpdate(TodoBase):
    completed: Optional[bool] = None

class Todo(TodoBase):
    id: int
    completed: bool = False

    class Config:
        from_attributes = True
