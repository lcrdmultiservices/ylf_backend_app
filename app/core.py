from fastapi import APIRouter
from slowapi import Limiter
from slowapi.util import get_remote_address

# --- Pieza 1: El Limiter ---
limiter = Limiter(key_func=get_remote_address)


# --- Pieza 2: El Router Personalizado ---
# Esta clase asegura que todas las rutas se registren sin una barra final.
class NoTrailingSlashRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redirect_slashes = False