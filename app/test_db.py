from app.database import engine

try:
    with engine.connect() as connection:
        print("✅ Conexión a la base de datos exitosa")
except Exception as e:
    print("❌ Error de conexión:", e)