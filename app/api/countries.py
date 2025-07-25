# Se añaden HTTPException y Request a los imports de FastAPI
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db
# Se importa la función de logging desde el nuevo módulo
from app.utils.mongo_logger import log_error

router = APIRouter()

# Endpoint 1: Lista de códigos IDD por país
# Se añade 'request: Request' para poder pasar datos del cliente al logger
@router.get("/countries/idd")
def get_country_idd_list(request: Request, db: Session = Depends(get_db)):
    try:
        # La lógica original se mantiene dentro del bloque 'try'
        results = db.execute(text("SELECT idd, name, iso2 FROM countries ORDER BY name")).fetchall()
        return [{"idd": row.idd, "name": row.name, "iso2": row.iso2} for row in results]
    except Exception as e:
        # --- IMPLEMENTACIÓN DEL NUEVO PATRÓN DE ERRORES ---

        # 1. Registra el error detallado en MongoDB para los desarrolladores.
        log_error(
            endpoint="/countries/idd",
            method="GET",
            error=e,
            user_context={"client_ip": request.client.host} # Se puede añadir cualquier contexto útil
        )

        # 2. Lanza una excepción HTTP con una clave de error genérica para el usuario.
        raise HTTPException(
            status_code=500, 
            detail="error_loading_data" # El frontend usará esta clave
        )

# Endpoint 2: Lista de nombres de países con su ISO (sin cambios)
@router.get("/countries/names")
def get_country_names(db: Session = Depends(get_db)):
    results = db.execute(text("SELECT name, iso2 FROM countries ORDER BY name")).fetchall()
    return [{"name": row.name, "iso2": row.iso2} for row in results]

# Endpoint 3: Detalle de un país por su ISO2 (sin cambios)
@router.get("/countries/{iso2}")
def get_country_by_iso(iso2: str, db: Session = Depends(get_db)):
    result = db.execute(text("SELECT * FROM countries WHERE iso2 = :iso2"), {"iso2": iso2.upper()}).fetchone()
    return dict(result) if result else {"error": "Country not found"}

# Endpoint 4: Lista de países ordenados alfabéticamente con claves (sin cambios)
@router.get("/countries/list")
def get_country_list(db: Session = Depends(get_db)):
    results = db.execute(text("SELECT id, name FROM countries ORDER BY name ASC")).fetchall()
    return [{"id": row.id, "name": row.name} for row in results]

# Endpoint 5: Lista de regiones asociadas a un país (sin cambios)
@router.get("/countries/{country_id}/regions")
def get_regions_by_country(country_id: int, db: Session = Depends(get_db)):
    query = text("""
        SELECT r.id, r.name 
        FROM countries_has_regions chr
        JOIN regions r ON chr.region_id = r.id
        WHERE chr.country_id = :country_id
        ORDER BY r.name
    """)
    results = db.execute(query, {"country_id": country_id}).fetchall()
    return [{"id": row.id, "name": row.name} for row in results]

