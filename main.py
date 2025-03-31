from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from routers import books, users
from utils.dependencies import rate_limit
from utils.auth import authenticate_user, create_access_token, Token
from datetime import timedelta
from utils.auth import ACCESS_TOKEN_EXPIRE_MINUTES

app = FastAPI(
    title="Bibliothèque API",
    description="API de gestion de bibliothèque",
    version="0.1.0",
    dependencies=[Depends(rate_limit)]  # Dépendance globale pour limiter le taux
)

app.include_router(books.router)
app.include_router(users.router)

@app.get("/")
async def root():
    return {"message": "Bienvenue sur l'API de gestion de bibliothèque"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    from routers.users import users  # Importation locale pour éviter les dépendances circulaires
    
    user = authenticate_user(users, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}