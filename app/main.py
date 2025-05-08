from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from app.config import DATABASE_URL
import traceback

app = FastAPI()

@app.get("/test_db")
def test_db_connection():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return {"success": True, "result": [row[0] for row in result]}
    except Exception as e:
        print("Database connection error:")
        traceback.print_exc()
        return {"success": False, "error": str(e)}
