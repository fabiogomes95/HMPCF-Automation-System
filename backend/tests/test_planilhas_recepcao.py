"""Leitura das planilhas manuais da recepção — casos tirados das planilhas reais."""
from datetime import date, datetime, time

from app.importacao.planilhas_recepcao import _cpf, ano_das_abas, ler_aba, nome_busca


def pac(nome, hora, cpf=None, nasc=None, n=1.0):
    """Linha de paciente no layout 2024+: nº, nome, nascimento, idade, sexo, raça, cidade, hora, CPF."""
    return (n, nome, nasc, 30.0, "F", "PARDA", "EXTREMOZ", hora, cpf, 700001234567890.0)


def test_dias_pelos_plantoes_e_madrugada_no_dia_seguinte():
    linhas = [
        ("", "NOME COMPLETO", "DATA DE NASCIMENTO", "IDADE"),
        ("PLANTÃO DIURNO - 01/05/2022 - FULANA",),
        pac("ANA SOUZA", time(7, 10), "529.982.247-25", datetime(1990, 1, 1)),
        ("PLANTAO NOTURNO 01/05/2022 - BELTRANA",),
        pac("BIA LIMA", time(22, 0)),
        pac("CAIO MELO", time(2, 15)),                     # madrugada: chegou em 02/05
        ("PLANTÃO DIURNO 02/05/2022",),
        pac("DUDA REIS", "07;25"),                          # hora digitada com ;
    ]
    e = list(ler_aba(linhas, "MAIO 2022"))
    assert [(x.nome, x.data) for x in e] == [
        ("ANA SOUZA", date(2022, 5, 1)), ("BIA LIMA", date(2022, 5, 1)),
        ("CAIO MELO", date(2022, 5, 2)), ("DUDA REIS", date(2022, 5, 2)),
    ]
    assert e[0].cpf == "52998224725" and e[0].nascimento == date(1990, 1, 1)
    assert e[3].hora == time(7, 25)


def test_erros_de_digitacao_nas_linhas_de_plantao():
    linhas = [
        (datetime(2007, 8, 7),),                              # nascimento solto no topo: não é dia
        ("PLANTÃO DIURNO - 03/05/2022",),
        pac("A A", time(8, 0)),
        ("PLANÃO NOTURNO - 03/05/2022",),                     # "PLANÃO"
        pac("B B", time(20, 0)),
        ("PLANÃO DIURNO 07/05/2022/ MARIA",),                 # erro: era 04
        pac("C C", time(8, 0)),
        ("PLANTÃO NOTURNO - 04/05/2022 -",),
        pac("D D", time(20, 0)),
        ("PLANTÃO DIURNO 0505/2022/ DANI",),                  # DDMM grudado
        pac("ELI ELI", time(8, 0)),
        ("PLANTÃO DIURNO 05/05/2022",),                       # o mesmo plantão repetido = noturno
        pac("F F", time(21, 0)),
    ]
    dias = {x.nome: x.data.day for x in ler_aba(linhas, "MAIO 2022")}
    assert dias == {"A A": 3, "B B": 3, "C C": 4, "D D": 4, "ELI ELI": 5, "F F": 5}


def test_aba_com_dias_faltando_e_virada_do_mes():
    linhas = [
        ("PLANTAO DIURNO 05/08/2025",), pac("A A", time(8, 0)),
        ("PLANTAO DIURNO 09/08/2025",), pac("B B", time(8, 0)),     # dias 6-8 estão em outra planilha
        ("PLANTAO DIURNO 10/08/2025",), pac("C C", time(8, 0)),
        ("PLANTAO DIURNO 31/08/2025",), pac("D D", time(8, 0)),
        ("PLANTÃO DIURNO - 01/09/2025 - LEINA",), pac("ELI ELI", time(8, 0)),  # 1º do mês seguinte
    ]
    datas = {x.nome: x.data for x in ler_aba(linhas, "AGOSTO2025")}
    assert datas["B B"] == date(2025, 8, 9) and datas["C C"] == date(2025, 8, 10)
    assert datas["ELI ELI"] == date(2025, 9, 1)


def test_linha_deslocada_e_linhas_que_nao_sao_paciente():
    linhas = [
        ("PLANTAO DIURNO 02/03/2026",),
        ("714.448.834-10", "ADRIELLY DOS SANTOS", datetime(2011, 10, 9), "F", "PARDA", "EXTREMOZ", time(9, 18)),
        (None, None, None, None, "SEM SISTEMA", "EXTREMOZ"),
        (None, "R. PEDRO RUFINO, 5", None),
        ("PLANTAO NOTURNO - FRANCISCA E JOANA",),              # plantão sem data
        pac("G G", time(23, 0)),
    ]
    e = list(ler_aba(linhas, "MARÇO 2026"))
    assert [x.nome for x in e] == ["ADRIELLY DOS SANTOS", "G G"]
    assert e[0].cpf == "71444883410"
    assert e[1].data == date(2026, 3, 2) and e[1].turno == "NOTURNO"


def test_cpf_nao_confunde_telefone_nem_sus():
    assert _cpf("529.982.247-25") == "52998224725"
    assert _cpf("123.456.789-00") == "12345678900"      # formatado vale mesmo com dígito errado
    assert _cpf(84991234567.0) is None                    # 11 números soltos inválidos: telefone
    assert _cpf(5299822472.0) is None                     # 10 dígitos que não fecham CPF
    assert _cpf(1234567890.0) == "01234567890"             # zero da frente perdido no Excel
    assert _cpf("(84) 99218-7115") is None
    assert _cpf(700001234567890.0) is None                # SUS
    assert _cpf("SEM CPF") is None


def test_ano_das_abas_sem_ano_e_nome_busca():
    anos = ano_das_abas(["SETEMBRO", "DEZEMBRO", "JANEIRO 2022", "MAIO2025", "Página42"])
    assert anos == {"SETEMBRO": 2021, "DEZEMBRO": 2021, "JANEIRO 2022": 2022, "MAIO2025": 2025, "Página42": None}
    assert nome_busca("  José  da Conceição ") == "JOSE DA CONCEICAO"
