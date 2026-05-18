from __future__ import annotations

from app.utils import apenas_numeros, valida_cns


def valida_cpf(cpf: str | None) -> bool:
    c = apenas_numeros(cpf)
    if not c or len(c) != 11 or len(set(c)) == 1:
        return False
    s1 = sum(int(c[i]) * (10 - i) for i in range(9))
    d1 = (s1 * 10 % 11) % 10
    s2 = sum(int(c[i]) * (11 - i) for i in range(10))
    d2 = (s2 * 10 % 11) % 10
    return str(d1) == c[9] and str(d2) == c[10]
