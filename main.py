from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from routers import books, users  # Importation des routeurs pour les livres et les utilisateurs
from utils.dependencies import rate_limit  # Dépendance pour limiter le taux de requêtes
from utils.auth import authenticate_user, create_access_token, Token, set_users_reference
from datetime import timedelta
from utils.auth import ACCESS_TOKEN_EXPIRE_MINUTES

# Création de l'application FastAPI avec des métadonnées (titre, description, version)
app = FastAPI(
    title="Bibliothèque API",  # Titre de l'API
    description="API de gestion de bibliothèque",  # Description de l'API
    version="0.1.0",  # Version de l'API
    dependencies=[Depends(rate_limit)]  # Dépendance globale pour limiter le taux de requêtes
)

# Inclusion des routeurs pour gérer les routes liées aux livres et aux utilisateurs
app.include_router(books.router)  # Routeur pour les livres
app.include_router(users.router)  # Routeur pour les utilisateurs

# Événement de démarrage de l'application (exécuté au lancement de l'API)
@app.on_event("startup")
async def startup_event():
    # Importation de la liste des utilisateurs pour éviter les problèmes d'importation circulaire
    from routers.users import users
    set_users_reference(users)  # Initialisation de la référence des utilisateurs

# Route de base pour vérifier que l'API fonctionne
@app.get("/")
async def root():
    # Retourne un message de bienvenue
    return {"message": "Bienvenue sur l'API de gestion de bibliothèque"}

# Route pour générer un token d'accès (authentification des utilisateurs)
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Importation de la liste des utilisateurs
    from routers.users import users
    
    # Authentification de l'utilisateur avec son nom d'utilisateur et son mot de passe
    user = authenticate_user(users, form_data.username, form_data.password)
    if not user:
        # Si l'utilisateur n'est pas authentifié, une exception HTTP 401 est levée
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Création d'un token d'accès avec une durée d'expiration
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},  # Les données du token incluent l'email de l'utilisateur
        expires_delta=access_token_expires  # Durée d'expiration du token
    )
    # Retourne le token d'accès et son type
    return {"access_token": access_token, "token_type": "bearer"}