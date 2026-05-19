class HMPCFError(Exception):
    pass


class NotFoundError(HMPCFError):
    pass


class ValidationError(HMPCFError):
    pass


class DatabaseError(HMPCFError):
    pass
