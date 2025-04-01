from fastapi import APIRouter, Query, Path, HTTPException, status, Depends
from pydantic import BaseModel, field_validator, Field
from typing import Optional, List
from enum import Enum
import datetime
from utils.dependencies import verify_api_key
from utils.auth import get_current_user, check_admin_role, UserInDB

# Création d'un routeur pour les livres avec un préfixe et des tags
router = APIRouter(
    prefix="/books",  # Toutes les routes sous "/books"
    tags=["books"],  # Catégorie dans la documentation
    responses={404: {"description": "Livre non trouvé"}}  # Gestion de la réponse 404
)

# Liste fictive pour stocker les livres (simulation d'une base de données)
books = [
    {"id": 1, "titre": "Le Petit Prince", "auteur": "Antoine de Saint-Exupéry", "ISBN": "978-2-07-040850-4", "annee": 1943, "genre": "Conte"},
    {"id": 2, "titre": "Harry Potter", "auteur": "J.K. Rowling", "ISBN": "978-0-7475-3269-9", "annee": 1997, "genre": "Fantasy"},
    {"id": 3, "titre": "1984", "auteur": "George Orwell", "ISBN": "978-0-14-103614-4", "annee": 1949, "genre": "Science-fiction"}
]

# Enumération pour représenter différents genres de livres
class GenreEnum(str, Enum):
    SF = "Science-fiction"
    FANTASY = "Fantasy"
    ROMAN = "Roman"
    CONTE = "Conte"
    THRILLER = "Thriller"
    AUTRE = "Autre"

# Modèle Pydantic de base pour la validation des livres
class BookBase(BaseModel):
    titre: str
    auteur: str
    ISBN: str = Field(..., pattern=r'^\d{3}-\d-\d{3}-\d{5}-\d$')  # Validation de l'ISBN
    annee: Optional[int] = Field(None, gt=1900, le=datetime.datetime.now().year)  # Année entre 1900 et l'année actuelle
    genre: Optional[GenreEnum] = None  # Genre facultatif

    # Validation supplémentaire pour l'ISBN
    @field_validator('ISBN')
    def validate_isbn(cls, v):
        if not (v and len(v) >= 10):
            raise ValueError("ISBN invalide")
        return v

# Modèle représentant un livre avec un ID
class Book(BookBase):
    id: int

# Fonction de dépendance pour récupérer un livre par son ID
def get_book_by_id(book_id: int):
    for book in books:
        if book["id"] == book_id:
            return book
    raise HTTPException(status_code=404, detail="Livre non trouvé")

# Route pour récupérer tous les livres
@router.get("/", response_model=List[dict])
async def get_books(format: Optional[str] = Query("simple", enum=["simple", "detailed"])):
    if format == "simple":
        return [{"id": book["id"], "titre": book["titre"]} for book in books]  # Retourne ID et titre uniquement
    else:
        return books  # Retourne tous les détails

# Route pour rechercher des livres par titre
@router.get("/search")
async def search_books(q: str = Query(..., min_length=1, description="Terme de recherche")):
    results = [book for book in books if q.lower() in book["titre"].lower()]
    return results

# Route pour récupérer un livre par son ID
@router.get("/{book_id}", response_model=dict)
async def get_book(book: dict = Depends(get_book_by_id)):
    return book

# Route pour créer un nouveau livre
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Book)
async def create_book(book: BookBase, current_user: UserInDB = Depends(get_current_user)):
    new_id = max([b["id"] for b in books]) + 1 if books else 1  # Générer un nouvel ID
    new_book = book.model_dump()  # Convertir le modèle en dictionnaire
    new_book["id"] = new_id
    books.append(new_book)  # Ajouter le livre à la liste
    return new_book

# Route pour mettre à jour un livre existant
@router.put("/{book_id}", response_model=Book)
async def update_book(book_id: int, book: BookBase, current_user: UserInDB = Depends(get_current_user)):
    book_dict = get_book_by_id(book_id)  # Vérifier si le livre existe
    
    updated_book = book.model_dump()
    updated_book["id"] = book_id  # Conserver l'ID
    
    for i, stored_book in enumerate(books):
        if stored_book["id"] == book_id:
            books[i] = updated_book  # Mise à jour des données
            return updated_book
    
    raise HTTPException(status_code=404, detail="Livre non trouvé")

# Route pour supprimer un livre (réservé aux administrateurs)
@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, current_user: UserInDB = Depends(check_admin_role)):
    book = get_book_by_id(book_id)  # Vérifier si le livre existe
    
    for i, b in enumerate(books):
        if b["id"] == book_id:
            books.pop(i)  # Suppression du livre
            return