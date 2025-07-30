import bcrypt

password_to_hash = "LcRd@1804"

# Codificar la contraseña a bytes
password_bytes = password_to_hash.encode('utf-8')

# Generar el salt y el hash
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password_bytes, salt)

# Imprimir el hash para que puedas copiarlo y pegarlo
print("Copia el siguiente hash:")
print(hashed_password.decode('utf-8'))