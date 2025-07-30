from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, constr
from sqlalchemy.orm import Session
from sqlalchemy import text
import bcrypt

# Importaciones de nuestro proyecto
from app.db.database import get_db, get_mongo_db
from app.utils.mailgun_client import send_verification_email
# Reutilizamos las funciones de OTP que ya creamos para el registro
from app.api.register_local_personal import generate_and_store_otp, verify_otp

router = APIRouter(
    prefix="/password",
    tags=["Password Recovery"]
)

# --- Modelos Pydantic para la validación de datos ---

class ForgotPasswordRequest(BaseModel):
    """Modelo para la solicitud de envío de OTP."""
    email: EmailStr

class VerifyOtpRequest(BaseModel):
    """Modelo para la verificación del OTP."""
    email: EmailStr
    otp: constr(min_length=6, max_length=6)

class ResetPasswordRequest(BaseModel):
    """Modelo para el reseteo final de la contraseña."""
    email: EmailStr
    otp: constr(min_length=6, max_length=6)
    new_password: str


# --- Endpoint 1: Solicitar código de recuperación ---
@router.post("/forgot", status_code=200)
async def request_password_reset(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    Inicia el flujo de recuperación de contraseña.
    Busca al usuario por email. Si existe, genera y envía un OTP.
    Importante: Siempre devuelve una respuesta genérica para evitar la enumeración de usuarios.
    """
    # Consulta para encontrar al usuario y su nombre para el email
    query = text("""
        SELECT u.idusers, p.first_name
        FROM users u
        JOIN accounts a ON u.idusers = (SELECT uha.users_idusers FROM users_has_accounts uha WHERE uha.accounts_idaccounts = a.idaccounts)
        JOIN person p ON u.person_idperson = p.idperson
        WHERE a.email = :email AND a.authentication_type_idauthentication_type = 1
    """)
    user_data = db.execute(query, {"email": data.email}).first()

    # Medida de seguridad: No revelar si el correo electrónico existe.
    # Si el usuario existe, procedemos a enviar el correo.
    if user_data:
        otp_code = generate_and_store_otp(
            mongo_db=mongo_db,
            user_id=user_data.idusers,
            email=data.email,
            otp_context="PASSWORD_RESET", # Contexto específico para este flujo
            lifespan_minutes=5 # Tiempo de vida corto
        )
        
        if otp_code:
            # Enviar el correo electrónico con el código
            send_verification_email(
                email_to=data.email,
                otp_code=otp_code,
                first_name=user_data.first_name,
                language='es', # O el idioma que corresponda
                email_type='password_reset' # Un tipo de plantilla diferente
            )

    # Devolvemos una respuesta exitosa genérica en todos los casos.
    return {"detail": "If an account with that email exists, a recovery code has been sent."}


# --- Endpoint 2: Verificar el código OTP ---
@router.post("/verify-otp", status_code=200)
async def check_otp_validity(
    data: VerifyOtpRequest,
    mongo_db = Depends(get_mongo_db)
):
    """
    Verifica si el OTP proporcionado es válido, no ha expirado y
    corresponde al contexto de reseteo de contraseña.
    """
    is_valid = verify_otp(
        mongo_db=mongo_db,
        email=data.email,
        otp_code=data.otp,
        otp_context="PASSWORD_RESET"
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail="error_invalid_otp")

    return {"detail": "OTP is valid."}


# --- Endpoint 3: Restablecer la contraseña ---
@router.post("/reset", status_code=200)
async def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    Verifica el OTP una última vez y, si es válido, actualiza la contraseña del usuario.
    """
    # 1. Verificar el OTP de nuevo como medida de seguridad final.
    is_valid = verify_otp(
        mongo_db=mongo_db,
        email=data.email,
        otp_code=data.otp,
        otp_context="PASSWORD_RESET",
        delete_on_verify=True # Importante: Eliminar el OTP después de usarlo.
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail="error_invalid_or_expired_otp")

    # 2. Hashear la nueva contraseña
    hashed_password = bcrypt.hashpw(data.new_password.encode('utf-8'), bcrypt.gensalt())

    # 3. Actualizar la contraseña en la base de datos
    update_query = text("""
        UPDATE accounts
        SET hash_password = :new_password
        WHERE email = :email AND authentication_type_idauthentication_type = 1
    """)
    
    try:
        result = db.execute(update_query, {
            "new_password": hashed_password.decode('utf-8'),
            "email": data.email
        })
        db.commit()

        # Verificar si alguna fila fue realmente actualizada
        if result.rowcount == 0:
            # Esto podría ocurrir si el email fue eliminado entre la verificación y el reseteo.
            raise HTTPException(status_code=404, detail="error_user_not_found")

    except Exception as e:
        db.rollback()
        # Aquí podrías registrar el error con tu logger
        raise HTTPException(status_code=500, detail="error_database_update_failed")

    return {"detail": "Password has been reset successfully."}
