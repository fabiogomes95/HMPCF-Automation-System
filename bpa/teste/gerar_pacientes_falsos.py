"""Gera bpa/teste/pacientes_falsos.json: pacientes e atendimentos FALSOS que
fazem o papel do PostgreSQL do hospital no modo de teste do BPA
(BPA_POSTGRES_FALSO no bpa/.env) — testar a migração sem acesso ao hospital.

Todos os nomes começam com "TESTE" (fácil de achar e apagar no Firebird de
teste). CPFs válidos pelo dígito verificador, mas inventados.

Uso:  python bpa/teste/gerar_pacientes_falsos.py
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

SAIDA = Path(__file__).with_name("pacientes_falsos.json")
random.seed(2026)  # sempre a mesma lista

NOMES = ["MARIA", "JOSE", "ANA", "JOAO", "FRANCISCA", "ANTONIO", "ANTONIA", "FRANCISCO", "RAIMUNDA",
         "PAULO", "LUCIA", "CARLOS", "FATIMA", "PEDRO", "SEVERINA", "MANOEL", "JULIANA", "RAFAEL"]
SOBRENOMES = ["SILVA", "SANTOS", "OLIVEIRA", "SOUZA", "LIMA", "PEREIRA", "COSTA", "FERREIRA",
              "ALVES", "RODRIGUES", "NASCIMENTO", "ARAUJO", "BEZERRA", "MEDEIROS"]
BAIRROS = ["CENTRO", "MOINHO DOS VENTOS", "PITANGUI", "ESTIVAS", "MALVINAS", "SANTA RITA", "GRACANDU"]
RUAS = ["RUA DAS FLORES", "RUA PRINCIPAL", "AV. PRES. CAFE FILHO", "RUA DO SOL", "TRAVESSA BOA VISTA"]


def _dv(nums: list[int], peso_ini: int) -> int:
    resto = sum(n * p for n, p in zip(nums, range(peso_ini, 1, -1))) % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido() -> str:
    base = [random.randint(0, 9) for _ in range(9)]
    if len(set(base)) == 1:
        base[0] = (base[0] + 1) % 10
    d1 = _dv(base, 10)
    d2 = _dv(base + [d1], 11)
    return "".join(map(str, base + [d1, d2]))


def cns_valido() -> str:
    """CNS definitivo (começa com 1/2): 11 dígitos do PIS + '00X' + dígito, soma ponderada % 11 == 0."""
    while True:
        pis = str(random.choice([1, 2])) + "".join(str(random.randint(0, 9)) for _ in range(10))
        soma = sum(int(pis[i]) * (15 - i) for i in range(11))
        dv = 11 - soma % 11
        if dv == 11:
            dv = 0
        if dv == 10:
            continue  # evita o caso "001" pra manter simples
        cns = pis + "000" + str(dv)
        if sum(int(cns[i]) * (15 - i) for i in range(15)) % 11 == 0:
            return cns


def main() -> None:
    hoje = date.today()
    inicio = (hoje.replace(day=1) - timedelta(days=60)).replace(day=1)  # ~3 meses
    dias = (hoje - inicio).days + 1
    pacientes = []
    for i in range(1, 121):
        nome = f"TESTE {random.choice(NOMES)} {random.choice(SOBRENOMES)} {random.choice(SOBRENOMES)}"
        nasc = date(random.randint(1940, 2024), random.randint(1, 12), random.randint(1, 28))
        pac = {
            "cns": cns_valido() if i % 4 else "",          # 1 em 4 sem SUS
            "num_cpf": cpf_valido(),
            "nome": nome,
            "dtnasc": nasc.strftime("%Y%m%d"),
            "sexo": random.choice("MF"),
            "raca": random.choice(["01", "02", "03", "03", "03", "04"]),
            "maepcn": f"TESTE MAE {random.choice(NOMES)} {random.choice(SOBRENOMES)}",
            "logpcn": random.choice(RUAS),
            "numpcn": str(random.randint(1, 999)),
            "bairro_pcnte": random.choice(BAIRROS),
            "ceppcn": "59575000",
            "ibge": "240360",
            "nacionalidade": "010",
            "ddtel_pcnte": "84",
            "tel_pcnte": "9" + "".join(str(random.randint(0, 9)) for _ in range(8)),
            # datas dos atendimentos na recepção (a migração filtra por elas)
            "atendimentos": sorted({(inicio + timedelta(days=random.randrange(dias))).isoformat()
                                    for _ in range(random.choice([1, 1, 1, 2, 3]))}),
        }
        pacientes.append(pac)

    # Casos difíceis, de propósito (inclui 6 pacientes sem CPF nem SUS)
    pacientes[0]["num_cpf"] = "12345678900"   # CPF inválido: a migração tem que pular
    pacientes[1]["num_cpf"] = "11111111111"   # CPF inválido (todos iguais)
    pacientes[2]["dtnasc"] = ""                # sem data de nascimento
    pacientes[3]["atendimentos"] = [hoje.isoformat()]  # atendido hoje
    for pac in pacientes[4:10]:                # 6 SEM DOCUMENTO: sem CPF e sem SUS
        pac["num_cpf"] = ""
        pac["cns"] = ""

    SAIDA.write_text(json.dumps({"gerado_em": hoje.isoformat(), "pacientes": pacientes},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(pacientes)} pacientes falsos em {SAIDA}")


if __name__ == "__main__":
    main()
