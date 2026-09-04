class HMPCFError(Exception):
    """Exceção base do domínio HMPCF — agnóstica a HTTP."""

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(message)


class NotFoundError(HMPCFError):
    """Recurso não encontrado → HTTP 404."""

    def __init__(self, resource: str, identifier: object = None) -> None:
        detail = f"{resource} não encontrado"
        if identifier is not None:
            detail = f"{resource} '{identifier}' não encontrado"
        super().__init__(detail)


class ConflictError(HMPCFError):
    """Conflito de unicidade → HTTP 409."""


class BusinessRuleError(HMPCFError):
    """Violação de regra de negócio → HTTP 422."""


class ValidationError(HMPCFError):
    """Erro de validação de dados → HTTP 422."""


class UnauthorizedError(HMPCFError):
    """Sem sessão válida (ausente, expirada, conta inativa/bloqueada) → HTTP 401."""


class ForbiddenError(HMPCFError):
    """Sessão válida mas sem permissão pro papel exigido → HTTP 403.

    Reservado para quando dashboard/bpa também tiverem login e existir
    diferenciação real de papel — a recepção em si (v1) não usa ainda.
    """
