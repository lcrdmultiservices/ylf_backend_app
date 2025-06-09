from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db

router = APIRouter()

# Endpoint 1: Lista de códigos IDD por país
@router.get("/api/countries/idd")
def get_country_idd_list(db: Session = Depends(get_db)):
    results = db.execute("SELECT idd, name, iso2 FROM countries ORDER BY name").fetchall()
    return [{"idd": row.idd, "name": row.name, "iso2": row.iso2} for row in results]

# Endpoint 2: Lista de nombres de países con su ISO
@router.get("/api/countries/names")
def get_country_names(db: Session = Depends(get_db)):
    results = db.execute("SELECT name, iso2 FROM countries ORDER BY name").fetchall()
    return [{"name": row.name, "iso2": row.iso2} for row in results]

# Endpoint 3: Detalle de un país por su ISO2
@router.get("/api/countries/{iso2}")
def get_country_by_iso(iso2: str, db: Session = Depends(get_db)):
    result = db.execute("SELECT * FROM countries WHERE iso2 = :iso2", {"iso2": iso2.upper()}).fetchone()
    return dict(result) if result else {"error": "Country not found"}

# Endpoint 4: Lista de países ordenados alfabéticamente con claves
@router.get("/api/countries/list")
def get_country_list(db: Session = Depends(get_db)):
    results = db.execute("SELECT id, name FROM countries ORDER BY name ASC").fetchall()
    return [{"id": row.id, "name": row.name} for row in results]

# Endpoint 5: Lista de regiones asociadas a un país
@router.get("/api/countries/{country_id}/regions")
def get_regions_by_country(country_id: int, db: Session = Depends(get_db)):
    query = """
        SELECT r.id, r.name 
        FROM countries_has_regions chr
        JOIN regions r ON chr.region_id = r.id
        WHERE chr.country_id = :country_id
        ORDER BY r.name
    """
    results = db.execute(query, {"country_id": country_id}).fetchall()
    return [{"id": row.id, "name": row.name} for row in results]
