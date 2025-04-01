from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, Union

# Configuration pour le JWT
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"  # Clé secrète pour signer les tokens
ALGORITHM = "HS256"  # Algorithme utilisé pour le JWT
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Durée de validité des tokens

# Modèle pour le token
class Token(BaseModel):
    access_token: str
    token_type: str

# Modèle pour les données contenues dans le token
class TokenData(BaseModel):
    username: Optional[str] = None

# Modèle pour représenter un utilisateur dans la base de données
class UserInDB(BaseModel):
    id: int
    nom: str
    email: str
    role: str
    hashed_password: str

# Contexte pour le hachage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Liste fictive des utilisateurs
users_db = []

# Vérifier si un mot de passe correspond à son hachage
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Hacher un mot de passe
def get_password_hash(password):
    return pwd_context.hash(password)

# Récupérer un utilisateur par son email
def get_user(db, username: str):
    for user in db:
        if user["email"] == username:
            return UserInDB(
                id=user["id"],
                nom=user["nom"],
                email=user["email"],
                role=user["role"],
                hashed_password=user["mot_de_passe"]
            )
    return None

# Authentifier un utilisateur
def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# Créer un token d'accès
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})  # Ajouter la date d'expiration
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Récupérer l'utilisateur actuel à partir du token
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
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # Utiliser la liste globale des utilisateurs
    from routers.users import users
    user = get_user(users, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

# Vérifier si l'utilisateur est administrateur
async def check_admin_role(current_user: UserInDB = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return current_user