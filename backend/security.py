import hashlib
import hmac
import os
import secrets
import time

import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# For a real deployment, set these as environment variables. The defaults are for the demo.
JWT_SECRET = os.getenv("SMARTFLOW_JWT_SECRET", "smartflow-demo-secret-change-me-before-real-use")
SIM_API_KEY = os.getenv("SMARTFLOW_SIM_KEY", "smartflow-sim-key")
TOKEN_HOURS = 8


# ---------- Passwords ----------
def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
    return f"{salt}${digest.hex()}"


def verify_password(password, stored):
    try:
        salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
        return hmac.compare_digest(digest.hex(), expected)
    except Exception:
        return False


# ---------- Tokens ----------
def create_token(username, role):
    payload = {"sub": username, "role": role, "exp": int(time.time()) + TOKEN_HOURS * 3600}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token):
    """Returns the token's data, or None if it is forged, damaged or expired."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


# ---------- Dependencies: FastAPI runs these before an endpoint ----------
bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if creds is None:
        raise HTTPException(status_code=401, detail="Login required")
    payload = decode_token(creds.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"username": payload["sub"], "role": payload["role"]}


def require_role(*allowed):
    def check(user=Depends(current_user)):
        if user["role"] not in allowed:
            raise HTTPException(status_code=403, detail="Your role is not allowed to do this")
        return user
    return check


def require_api_key(x_api_key: str = Header(default="")):
    if not hmac.compare_digest(x_api_key.encode(), SIM_API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")