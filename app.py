from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
from datetime import datetime, timedelta
import random

app = FastAPI()

SECRET_KEY = "super_secret_key_change_me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

users_db = {}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user(username: str):
    return users_db.get(username)

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user

@app.get("/")
def root():
    return {"status": "running"}

@app.post("/register")
def register(username: str, password: str):
    if username in users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = get_password_hash(password)
    users_db[username] = {
        "username": username,
        "hashed_password": hashed,
        "balance": 1000.0,
    }
    return {"message": "User registered", "username": username, "balance": users_db[username]["balance"]}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/balance")
def get_balance(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"], "balance": current_user["balance"]}

SYMBOLS = ["🍒", "🍋", "⭐", "💎", "7️⃣"]
PAYOUTS = {
    "🍒": 2.0,
    "🍋": 3.0,
    "⭐": 5.0,
    "💎": 10.0,
    "7️⃣": 20.0,
}

@app.post("/spin")
def spin(bet: float, current_user: dict = Depends(get_current_user)):
    if bet <= 0:
        raise HTTPException(status_code=400, detail="Bet must be positive")
    if current_user["balance"] < bet:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    current_user["balance"] -= bet
    reels = [random.choice(SYMBOLS) for _ in range(3)]

    win = 0.0
    if reels[0] == reels[1] == reels[2]:
        symbol = reels[0]
        win = bet * PAYOUTS.get(symbol, 0.0)
        current_user["balance"] += win

    return {
        "reels": reels,
        "bet": bet,
        "win": win,
        "balance": current_user["balance"],
    }
