# app/limiter.py modificacion octubre 2 25 se cambia nombre a core.py para centralizar procesos y evitar referencias circulares enn imports

from slowapi import Limiter
from slowapi.util import get_remote_address

# Creamos y configuramos la instancia del limiter aquí
limiter = Limiter(key_func=get_remote_address)clear