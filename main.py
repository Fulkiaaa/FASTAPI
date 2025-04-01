from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from routers import books, users
from utils.dependencies import rate_limit
from utils.auth import authenticate_user, create_access_token, Token, set_users_reference
from datetime import timedelta
from utils.auth import ACCESS_TOKEN_EXPIRE_MINUTES

# Création de l'application FastAPI avec des métadonnées
app = FastAPI(
    title="Bibliothèque API",
    description="API de gestion de bibliothèque",
    version="0.1.0",
    dependencies=[Depends(rate_limit)]
)

# Inclusion des routeurs pour les livres et les utilisateurs
app.include_router(books.router)
app.include_router(users.router)

# Configuration initiale - résout les dépendances circulaires
@app.on_event("startup")
async def startup_event():
    # Référencer la liste des utilisateurs pour éviter les importations circulaires
    from routers.users import users
    set_users_reference(users)

# Route de base pour vérifier que l'API fonctionne
@app.get("/")
async def root():
    return {"message": "Bienvenue sur l'API de gestion de bibliothèque"}

# Route pour générer un token d'accès (authentification)
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Importation de la liste des utilisateurs
    from routers.users import users
    
    # Authentification de l'utilisateur
    user = authenticate_user(users, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Création d'un token d'accès avec une durée d'expiration
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}