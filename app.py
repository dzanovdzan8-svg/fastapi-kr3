from fastapi import FastAPI, Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
import secrets
import os
from dotenv import load_dotenv
from models import User, UserInDB, LoginRequest, Token, TodoCreate, TodoUpdate, Todo
from database import get_db_connection, init_db

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key")
ALGORITHM = "HS256"
MODE = os.getenv("MODE", "DEV")
DOCS_USER = os.getenv("DOCS_USER", "admin")
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD", "secret")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBasic()
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Todo API")
app.add_middleware(SlowAPIMiddleware)

fake_users_db = {}
todo_counter = 1

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user_basic(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(credentials.username, DOCS_USER)
    correct_pass = secrets.compare_digest(credentials.password, DOCS_PASSWORD)
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"}
        )
    return credentials.username

def get_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

async def get_current_jwt_user(authorization: str = Header(None)):
    if authorization is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid scheme")
    
    token = parts[1]
    username = get_user_from_token(token)
    if username is None or username not in fake_users_db:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return fake_users_db[username]

def check_role(role: str):
    async def role_check(current_user: dict = Depends(get_current_jwt_user)):
        if current_user.get("role") != role and role != "user":
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return role_check

if MODE == "DEV":
    app.docs_url = "/docs"
    app.redoc_url = "/redoc"
    app.openapi_url = "/openapi.json"
else:
    app.docs_url = None
    app.redoc_url = None
    app.openapi_url = None

@app.post("/register", status_code=201)
@limiter.limit("1/minute")
async def register(request: Request, user: User):
    if user.username in fake_users_db:
        raise HTTPException(status_code=409, detail="User already exists")
    
    hashed = get_password_hash(user.password)
    fake_users_db[user.username] = {
        "username": user.username,
        "hashed_password": hashed,
        "role": "user"
    }
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (user.username, hashed)
    )
    conn.commit()
    conn.close()
    
    return {"message": "New user created"}

@app.get("/login_basic")
async def login_basic(current_user: str = Depends(get_current_user_basic)):
    return {"message": f"Welcome, {current_user}!"}

@app.post("/login")
@limiter.limit("5/minute")
async def login_jwt(request: Request, login_data: LoginRequest):
    if login_data.username not in fake_users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = fake_users_db[login_data.username]
    if not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Authorization failed")
    
    token = create_access_token(data={"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/protected_resource")
async def protected(current_user: dict = Depends(get_current_jwt_user)):
    return {"message": "Access granted"}

@app.get("/admin_panel")
async def admin_panel(current_user: dict = Depends(check_role("admin"))):
    return {"message": "Admin panel"}

@app.get("/user_data")
async def user_data(current_user: dict = Depends(check_role("user"))):
    return {"message": "User data"}

@app.get("/guest_area")
async def guest_area():
    return {"message": "Guest area"}

@app.post("/todos", status_code=201)
async def create_todo(todo: TodoCreate, current_user: dict = Depends(get_current_jwt_user)):
    global todo_counter
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO todos (title, description, completed, owner) VALUES (?, ?, 0, ?)",
        (todo.title, todo.description, current_user["username"])
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return Todo(id=new_id, title=todo.title, description=todo.description, completed=False)

@app.get("/todos/{todo_id}")
async def get_todo(todo_id: int, current_user: dict = Depends(get_current_jwt_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM todos WHERE id = ? AND owner = ?",
        (todo_id, current_user["username"])
    )
    row = cur.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    return Todo(id=row[0], title=row[1], description=row[2], completed=bool(row[3]))

@app.put("/todos/{todo_id}")
async def update_todo(todo_id: int, update: TodoUpdate, current_user: dict = Depends(get_current_jwt_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute(
        "SELECT * FROM todos WHERE id = ? AND owner = ?",
        (todo_id, current_user["username"])
    )
    row = cur.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo not found")
    
    data = update.model_dump(exclude_unset=True)
    if "completed" in data:
        data["completed"] = 1 if data["completed"] else 0
    
    sets = [f"{k} = ?" for k in data.keys()]
    vals = list(data.values()) + [todo_id, current_user["username"]]
    cur.execute(f"UPDATE todos SET {', '.join(sets)} WHERE id = ? AND owner = ?", vals)
    conn.commit()
    
    cur.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
    updated = cur.fetchone()
    conn.close()
    
    return Todo(id=updated[0], title=updated[1], description=updated[2], completed=bool(updated[3]))

@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int, current_user: dict = Depends(get_current_jwt_user)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM todos WHERE id = ? AND owner = ?",
        (todo_id, current_user["username"])
    )
    
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo not found")
    
    conn.commit()
    conn.close()
    return {"message": "Todo deleted"}

if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
