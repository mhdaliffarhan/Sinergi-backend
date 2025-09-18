from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload

# Impor dari file proyek Anda
import models, schemas, database

# ===================================================================
# KONFIGURASI KEAMANAN
# ===================================================================
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 300

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ===================================================================
# FUNGSI-FUNGSI UTILITAS KEAMANAN
# ===================================================================

def verify_password(plain_password, hashed_password):
    """Memverifikasi password asli dengan hash di database."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Membuat hash dari password asli."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Membuat JSON Web Token (JWT)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ===================================================================
# FUNGSI DEPENDENCY UNTUK OTENTIKASI & OTORISASI
# ===================================================================

def get_user(db: Session, username: str):
    """Mencari user berdasarkan username beserta relasinya + status ketua tim valid."""
    user = db.query(models.User).options(
        joinedload(models.User.sistem_role),
        joinedload(models.User.jabatan),
        joinedload(models.User.teams)
    ).filter(models.User.username == username).first()

    if not user:
        return None

    # cek apakah user adalah ketua tim aktif
    now = datetime.now()
    ketua_tim_aktif = db.query(models.Team).filter(
        models.Team.ketua_tim_id == user.id,
        models.Team.valid_from <= now,
        models.Team.valid_until >= now
    ).all()

    # tambahkan atribut dinamis ke user
    setattr(user, "ketua_tim_aktif", ketua_tim_aktif)
    setattr(user, "is_ketua_tim", len(ketua_tim_aktif) > 0)

    return user

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
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
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

def require_role(allowed_roles: List[str]):
    """
    Dependensi factory yang membuat "satpam" untuk memeriksa peran.
    Ini adalah "satpam" otorisasi.
    """
    def role_checker(current_user: models.User = Depends(get_current_user)):
        if current_user.sistem_role.nama_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki hak akses untuk operasi ini."
            )
        return current_user
    return role_checker