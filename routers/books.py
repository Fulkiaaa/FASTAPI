from fastapi import APIRouter, Query, Path, HTTPException, status, Depends
from pydantic import BaseModel, field_validator, Field
from typing import Optional, List
from enum import Enum
import datetime
from utils.dependencies import verify_api_key
from utils.auth import get_current_user, check_admin_role, UserInDB

router = APIRouter(
    prefix="/books",
    tags=["books"],
    responses={404: {"description": "Livre non trouvé"}}
)

# Données fictives
books = [
    {"id": 1, "titre": "Le Petit Prince", "auteur": "Antoine de Saint-Exupéry", "ISBN": "978-2-07-040850-4", "annee": 1943, "genre": "Conte"},
    {"id": 2, "titre": "Harry Potter", "auteur": "J.K. Rowling", "ISBN": "978-0-7475-3269-9", "annee": 1997, "genre": "Fantasy"},
    {"id": 3, "titre": "1984", "auteur": "George Orwell", "ISBN": "978-0-14-103614-4", "annee": 1949, "genre": "Science-fiction"}
]

class GenreEnum(str, Enum):
    SF = "Science-fiction"
    FANTASY = "Fantasy"
    ROMAN = "Roman"
    CONTE = "Conte"
    THRILLER = "Thriller"
    AUTRE = "Autre"

class BookBase(BaseModel):
    titre: str
    auteur: str
    ISBN: str = Field(..., pattern=r'^\d{3}-\d-\d{3}-\d{5}-\d$')
    annee: Optional[int] = Field(None, gt=1900, le=datetime.datetime.now().year)
    genre: Optional[GenreEnum] = None

    @field_validator('ISBN')
    def validate_isbn(cls, v):
        # Vérification simplifiée du format ISBN
        if not (v and len(v) >= 10):
            raise ValueError("ISBN invalide")
        return v

class Book(BookBase):
    id: int

# Dépendance pour vérifier si un livre existe
def get_book_by_id(book_id: int):
    for book in books:
        if book["id"] == book_id:
            return book
    raise HTTPException(status_code=404, detail="Livre non trouvé")

@router.get("/", response_model=List[dict])
async def get_books(format: Optional[str] = Query("simple", enum=["simple", "detailed"])):
    if format == "simple":
        return [{"id": book["id"], "titre": book["titre"]} for book in books]
    else:
        return books

@router.get("/search")
async def search_books(q: str = Query(..., min_length=1, description="Terme de recherche")):
    results = [book for book in books if q.lower() in book["titre"].lower()]
    return results

@router.get("/{book_id}", response_model=dict)
async def get_book(book: dict = Depends(get_book_by_id)):
    return book

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Book)
async def create_book(book: BookBase, current_user: UserInDB = Depends(get_current_user)):
    new_id = max([b["id"] for b in books]) + 1 if books else 1
    new_book = book.model_dump()
    new_book["id"] = new_id
    books.append(new_book)
    return new_book

@router.put("/{book_id}", response_model=Book)
async def update_book(book_id: int, 
                     book: BookBase,
                     current_user: UserInDB = Depends(get_current_user)):
    book_dict = get_book_by_id(book_id)
    
    updated_book = book.model_dump()
    updated_book["id"] = book_id
    
    # Mettre à jour le livre dans la liste
    for i, stored_book in enumerate(books):
        if stored_book["id"] == book_id:
            books[i] = updated_book
            return updated_book
    
    # Ne devrait jamais arriver puisque get_book_by_id vérifie déjà l'existence
    raise HTTPException(status_code=404, detail="Livre non trouvé")

@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, current_user: UserInDB = Depends(check_admin_role)):
    # Seuls les administrateurs peuvent supprimer des livres (vérifié par check_admin_role)
    book = get_book_by_id(book_id)
    
    for i, b in enumerate(books):
        if b["id"] == book_id:
            books.pop(i)
            return