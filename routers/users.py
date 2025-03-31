from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List  
from enum import Enum
import re
from utils.auth import get_password_hash, get_current_user, check_admin_role, UserInDB

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Utilisateur non trouvé"}}
)

# Données fictives
users = []

class RoleEnum(str, Enum):
    ADMIN = "admin"
    MEMBRE = "membre"

class UserBase(BaseModel):
    nom: str
    email: EmailStr
    role: RoleEnum = RoleEnum.MEMBRE

class UserCreate(UserBase):
    mot_de_passe: str

    @field_validator('mot_de_passe')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not re.search(r'[0-9]', v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "nom": "Jean Dupont",
                "email": "jean.dupont@example.com",
                "mot_de_passe": "MotDePasse123",
                "role": "membre"
            }
        }

class User(UserBase):
    id: int

    class Config:
        orm_mode = True

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    # Vérifier si l'email existe déjà
    for existing_user in users:
        if existing_user["email"] == user.email:
            raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    new_id = max([u["id"] for u in users]) + 1 if users else 1
    
    # Créer le nouvel utilisateur avec mot de passe haché
    hashed_password = get_password_hash(user.mot_de_passe)
    new_user = {
        "id": new_id,
        "nom": user.nom,
        "email": user.email,
        "role": user.role,
        "mot_de_passe": hashed_password
    }
    users.append(new_user)
    
    # Retourner l'utilisateur sans le mot de passe
    return User(
        id=new_user["id"],
        nom=new_user["nom"],
        email=new_user["email"],
        role=new_user["role"]
    )

@router.get("/", response_model=List[User])
async def get_users(current_user: UserInDB = Depends(check_admin_role)):
    # Seuls les administrateurs peuvent voir tous les utilisateurs
    return [User(
        id=user["id"],
        nom=user["nom"],
        email=user["email"],
        role=user["role"]
    ) for user in users]

@router.get("/me", response_model=User)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    return User(
        id=current_user.id,
        nom=current_user.nom,
        email=current_user.email,
        role=current_user.role
    )

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: int, current_user: UserInDB = Depends(get_current_user)):
    # Vérifier que l'utilisateur demande ses propres infos ou est admin
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Accès non autorisé")
        
    for user in users:
        if user["id"] == user_id:
            return User(
                id=user["id"],
                nom=user["nom"],
                email=user["email"],
                role=user["role"]
            )
    raise HTTPException(status_code=404, detail="Utilisateur non trouvé")