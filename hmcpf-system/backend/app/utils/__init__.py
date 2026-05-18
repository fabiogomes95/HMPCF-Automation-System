import re


def apenas_numeros(valor: str | None) -> str:
    return re.sub(r"\D", "", str(valor)) if valor else ""


def valida_cns(cns: str | None) -> bool:
    c = apenas_numeros(cns)
    if len(c) != 15 or c[0] not in "12789":
        return False
    if c[0] in "789":
        return sum(int(c[i]) * (15 - i) for i in range(15)) % 11 == 0
    pis = c[:11]
    soma = sum(int(pis[i]) * (15 - i) for i in range(11))
    resto = soma % 11
    dv = 11 - resto
    if dv == 11:
        dv = 0
    if dv == 10:
        soma += 2
        resto = soma % 11
        dv = 11 - resto
        resultado = pis + "001" + str(dv)
    else:
        resultado = pis + "000" + str(dv)
    return c == resultado
