from fastapi import APIRouter, Query, Path, HTTPException, status, Depends
from pydantic import BaseModel, field_validator, Field
from typing import Optional, List
from enum import Enum
import datetime
from utils.dependencies import verify_api_key
from utils.auth import get_current_user, check_admin_role, UserInDB

# Création d'un routeur pour les livres
router = APIRouter(
    prefix="/books",  # Préfixe pour toutes les routes liées aux livres
    tags=["books"],  # Tag pour regrouper les routes dans la documentation
    responses={404: {"description": "Livre non trouvé"}}  # Réponse par défaut pour 404
)

# Liste fictive pour stocker les livres
books = [
    {"id": 1, "titre": "Le Petit Prince", "auteur": "Antoine de Saint-Exupéry", "ISBN": "978-2-07-040850-4", "annee": 1943, "genre": "Conte"},
    {"id": 2, "titre": "Harry Potter", "auteur": "J.K. Rowling", "ISBN": "978-0-7475-3269-9", "annee": 1997, "genre": "Fantasy"},
    {"id": 3, "titre": "1984", "auteur": "George Orwell", "ISBN": "978-0-14-103614-4", "annee": 1949, "genre": "Science-fiction"}
]

# Enumération pour les genres de livres
class GenreEnum(str, Enum):
    SF = "Science-fiction"
    FANTASY = "Fantasy"
    ROMAN = "Roman"
    CONTE = "Conte"
    THRILLER = "Thriller"
    AUTRE = "Autre"

# Modèle de base pour les livres
class BookBase(BaseModel):
    titre: str
    auteur: str
    ISBN: str = Field(..., pattern=r'^\d{3}-\d-\d{3}-\d{5}-\d$')  # Validation du format ISBN
    annee: Optional[int] = Field(None, gt=1900, le=datetime.datetime.now().year)  # Année entre 1900 et l'année actuelle
    genre: Optional[GenreEnum] = None  # Genre facultatif

    # Validation supplémentaire pour l'ISBN
    @field_validator('ISBN')
    def validate_isbn(cls, v):
        if not (v and len(v) >= 10):
            raise ValueError("ISBN invalide")
        return v

# Modèle pour représenter un livre (avec ID)
class Book(BookBase):
    id: int

# Dépendance pour récupérer un livre par son ID
def get_book_by_id(book_id: int):
    for book in books:
        if book["id"] == book_id:
            return book
    raise HTTPException(status_code=404, detail="Livre non trouvé")

# Route pour récupérer tous les livres
@router.get("/", response_model=List[dict])
async def get_books(format: Optional[str] = Query("simple", enum=["simple", "detailed"])):
    # Format simple : uniquement ID et titre
    if format == "simple":
        return [{"id": book["id"], "titre": book["titre"]} for book in books]
    # Format détaillé : toutes les informations
    else:
        return books

# Route pour rechercher des livres par titre
@router.get("/search")
async def search_books(q: str = Query(..., min_length=1, description="Terme de recherche")):
    # Recherche insensible à la casse dans les titres
    results = [book for book in books if q.lower() in book["titre"].lower()]
    return results

# Route pour récupérer un livre par son ID
@router.get("/{book_id}", response_model=dict)
async def get_book(book: dict = Depends(get_book_by_id)):
    return book

# Route pour créer un nouveau livre
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Book)
async def create_book(book: BookBase, current_user: UserInDB = Depends(get_current_user)):
    # Générer un nouvel ID
    new_id = max([b["id"] for b in books]) + 1 if books else 1
    new_book = book.model_dump()  # Convertir le modèle en dictionnaire
    new_book["id"] = new_id
    books.append(new_book)  # Ajouter le livre à la liste
    return new_book

# Route pour mettre à jour un livre existant
@router.put("/{book_id}", response_model=Book)
async def update_book(book_id: int, 
                     book: BookBase,
                     current_user: UserInDB = Depends(get_current_user)):
    # Récupérer le livre existant
    book_dict = get_book_by_id(book_id)
    
    # Mettre à jour les informations du livre
    updated_book = book.model_dump()
    updated_book["id"] = book_id
    
    # Remplacer le livre dans la liste
    for i, stored_book in enumerate(books):
        if stored_book["id"] == book_id:
            books[i] = updated_book
            return updated_book
    
    # Ne devrait jamais arriver puisque get_book_by_id vérifie déjà l'existence
    raise HTTPException(status_code=404, detail="Livre non trouvé")

# Route pour supprimer un livre
@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, current_user: UserInDB = Depends(check_admin_role)):
    # Seuls les administrateurs peuvent supprimer des livres
    book = get_book_by_id(book_id)
    
    # Supprimer le livre de la liste
    for i, b in enumerate(books):
        if b["id"] == book_id:
            books.pop(i)
            return