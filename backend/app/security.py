import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # Argon2id com parâmetros padrão da biblioteca

# Hash fixo usado para equalizar o tempo de resposta quando o usuário não existe.
_DUMMY_HASH = _hasher.hash("usuario-inexistente")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def validate_password_policy(password: str) -> None:
    if len(password) < 10:
        raise ValueError("A senha deve ter pelo menos 10 caracteres.")
