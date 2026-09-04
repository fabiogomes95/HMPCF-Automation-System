from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=200)


class UsuarioResponse(BaseSchema):
    """Nunca expõe password_hash nem qualquer dado da tabela sessoes."""
    username: str
    role: str
