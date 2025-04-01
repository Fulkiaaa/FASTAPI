from fastapi import Header, HTTPException, Depends, Request
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Cache pour limiter le taux de requêtes
request_cache: Dict[str, List[Tuple[str, datetime]]] = {}

# Dépendance pour vérifier l'API-Key
async def verify_api_key(api_key: str = Header(..., description="Clé API pour l'authentification")):
    if api_key != "my-secret-key":  # Vérification de la clé API
        raise HTTPException(status_code=403, detail="Clé API invalide")
    return api_key

# Dépendance pour limiter le taux de requêtes
async def rate_limit(request: Request, api_key: str = Depends(verify_api_key)):
    now = datetime.now()
    # Nettoyer les requêtes expirées
    if api_key in request_cache:
        request_cache[api_key] = [req for req in request_cache[api_key] 
                                 if now - req[1] < timedelta(minutes=1)]
    else:
        request_cache[api_key] = []
    
    # Vérifier le nombre de requêtes
    if len(request_cache[api_key]) >= 10:
        raise HTTPException(
            status_code=429, 
            detail="Trop de requêtes. Limite: 10 requêtes par minute."
        )
    
    # Enregistrer la nouvelle requête
    request_cache[api_key].append((str(request.url), now))
    return True