"""
Testes de bpa_gerador.py — layout DATASUS (351 chars/linha), checksum,
rollover de folha/sequência e validações puras (CPF/CNS/idade/data).

Sem fixture de banco: usa unittest.mock.MagicMock pra simular a conexão
Firebird só onde é indispensável (calcular_atendimentos_producao).
Vetores de CPF/CNS válidos foram derivados à mão a partir do algoritmo
documentado no próprio módulo, não gerados pela função sendo testada —
senão o teste só provaria que a função concorda consigo mesma.
"""
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

import bpa_gerador as bpa

PROC_MEDICO = bpa.PROCEDIMENTOS["medico"]["codigo"]
CBO_MEDICO = bpa.PROCEDIMENTOS["medico"]["cbo"]


def _pac_exemplo(**overrides) -> dict:
    """Paciente já no formato pré-formatado que _buscar_dados_pacientes
    produz (larguras fixas) — é o que _linha_detalhe/montar_row_prd esperam
    receber."""
    pac = {
        "cns": "123456789010000",
        "nome": "MARIA DA SILVA".ljust(30),
        "nasc": "19900115",
        "sexo": "F",
        "ibge": "240360",
        "raca": "03",
        "etnia": "    ",
        "nac": "010",
        "cep": "59575000",
        "lograd": "081",
        "end": "RUA TESTE".ljust(30),
        "compl": "".ljust(10),
        "num": "123".ljust(5),
        "bairro": "CENTRO".ljust(30),
        "ddd": "84",
        "tel": "999999999".ljust(9),
        "email": "".ljust(40),
        "cpf": "12345678909",
    }
    pac.update(overrides)
    return pac


# ── Camada 1: layout posicional ──────────────────────────────────────────

def test_linha_detalhe_tem_351_caracteres():
    linha = bpa._linha_detalhe(
        _pac_exemplo(), PROC_MEDICO, CBO_MEDICO, "123456789012345", "20260615", "202606", 1, 1
    )
    assert len(linha) == 351


def test_linha_detalhe_le_proc_e_qtd_nas_posicoes_do_checksum():
    """_calcular_checksum lê [49:59] e [88:94] direto da string -- se algum
    campo antes dessas posições mudar de largura em _linha_detalhe sem
    atualizar o checksum, este teste quebra."""
    linha = bpa._linha_detalhe(
        _pac_exemplo(), PROC_MEDICO, CBO_MEDICO, "123456789012345", "20260615", "202606", 1, 1
    )
    assert linha[49:59] == PROC_MEDICO.zfill(10)
    assert linha[88:94] == "000001"


def test_linha_detalhe_muda_com_folha_seq_diferentes():
    linha1 = bpa._linha_detalhe(
        _pac_exemplo(), PROC_MEDICO, CBO_MEDICO, "123456789012345", "20260615", "202606", 1, 1
    )
    linha2 = bpa._linha_detalhe(
        _pac_exemplo(), PROC_MEDICO, CBO_MEDICO, "123456789012345", "20260615", "202606", 2, 5
    )
    assert linha1 != linha2
    assert len(linha1) == len(linha2) == 351


def test_calcular_checksum_bate_com_calculo_manual():
    linhas = [
        bpa._linha_detalhe(
            _pac_exemplo(), PROC_MEDICO, CBO_MEDICO, "123456789012345", "20260615", "202606", 1, s
        )
        for s in range(1, 4)
    ]
    # cada linha contribui (proc + qtd=1) pro checksum; 3 linhas iguais
    esperado = str((int(PROC_MEDICO) + 1) * 3 % 1111 + 1111).zfill(4)
    assert bpa._calcular_checksum(linhas) == esperado


def test_montar_cabecalho_tem_130_caracteres_e_checksum_na_posicao_certa():
    linhas = [
        bpa._linha_detalhe(
            _pac_exemplo(), PROC_MEDICO, CBO_MEDICO, "123456789012345", "20260615", "202606", 1, 1
        )
    ]
    checksum_esperado = bpa._calcular_checksum(linhas)
    cabecalho = bpa.montar_cabecalho("202606", 1, 1, linhas)
    assert len(cabecalho) == 130
    # "01" + "#BPA#" + competencia(6) + n_linhas(6) + n_folhas(6) = 25 chars antes do checksum
    assert cabecalho[25:29] == checksum_esperado


def test_validar_linhas():
    assert bpa.validar([]) == (True, 0)
    assert bpa.validar(["a" * 351, "b" * 351]) == (True, 351)
    assert bpa.validar(["a" * 351, "b" * 350]) == (False, 351)


# ── Camada 2: rollover de folha/sequência ────────────────────────────────

def test_montar_linhas_rollover_folha_no_centesimo_paciente():
    pacientes = [_pac_exemplo() for _ in range(100)]
    linhas, folha_final = bpa.montar_linhas(
        pacientes, PROC_MEDICO, CBO_MEDICO, "123456789012345", "20260615", "202606"
    )
    assert len(linhas) == 100
    assert folha_final == 2
    # folha=44:47, seq=47:49 na linha de detalhe
    assert linhas[98][44:47] == "001" and linhas[98][47:49] == "99"
    assert linhas[99][44:47] == "002" and linhas[99][47:49] == "01"


def test_montar_linhas_continua_de_folha_seq_inicial():
    pacientes = [_pac_exemplo() for _ in range(3)]
    linhas, folha_final = bpa.montar_linhas(
        pacientes, PROC_MEDICO, CBO_MEDICO, "123456789012345", "20260615", "202606",
        folha_inicial=5, seq_inicial=98,
    )
    assert linhas[0][44:47] == "005" and linhas[0][47:49] == "98"
    assert linhas[1][44:47] == "005" and linhas[1][47:49] == "99"
    assert linhas[2][44:47] == "006" and linhas[2][47:49] == "01"
    assert folha_final == 6


def test_montar_row_prd_reflete_folha_seq_e_ordem_das_colunas():
    row = bpa.montar_row_prd(
        _pac_exemplo(), PROC_MEDICO, CBO_MEDICO, "123456789012345", "20260615", "202606", 3, 7
    )
    assert len(row) == len(bpa._COLS_S_PRD)
    assert row[bpa._COLS_S_PRD.index("PRD_FLH")] == "003"
    assert row[bpa._COLS_S_PRD.index("PRD_SEQ")] == "07"


@pytest.mark.parametrize("producao_anterior,folha_esperada,seq_esperada", [
    (0, 1, 1),
    (98, 1, 99),
    (99, 2, 1),
    (197, 2, 99),
    (198, 3, 1),
])
def test_calcular_atendimentos_producao_rollover_nas_fronteiras(
    producao_anterior, folha_esperada, seq_esperada
):
    """Valores de fronteira (98/99/197/198) são os que colidiram em produção
    na auditoria de 06/2026 -- ver docs/historico/AUDITORIA_BPA_2026-06.md."""
    con = MagicMock()
    con.cursor.return_value.fetchone.return_value = (producao_anterior,)

    resultado = bpa.calcular_atendimentos_producao(
        con, "123456789012345", "medico", "20260615", [_pac_exemplo()], gravar=False,
    )

    assert resultado == [{"folha": folha_esperada, "seq": seq_esperada}]


def test_calcular_atendimentos_producao_gravar_false_nao_executa_insert():
    con = MagicMock()
    con.cursor.return_value.fetchone.return_value = (0,)

    bpa.calcular_atendimentos_producao(
        con, "123456789012345", "medico", "20260615", [_pac_exemplo(), _pac_exemplo()], gravar=False,
    )

    # a única query executada deve ser a de contar_producao_real (SELECT COUNT) --
    # nenhum INSERT em S_PRD quando gravar=False
    for chamada in con.cursor.return_value.execute.call_args_list:
        assert "INSERT" not in chamada.args[0].upper()


# ── Camada 3: validações puras ───────────────────────────────────────────

@pytest.mark.parametrize("cpf,esperado", [
    ("11144477735", True),
    ("12345678909", True),
    ("52998224725", True),
    ("11111111111", False),  # todos os dígitos iguais
    ("1114447773", False),   # tamanho errado
    ("11144477736", False),  # dígito verificador errado
    ("", False),
])
def test_valida_cpf(cpf, esperado):
    assert bpa.valida_cpf(cpf) == esperado


@pytest.mark.parametrize("cns,esperado", [
    ("123456789010000", True),   # ramo PIS/PASEP (prefixo 1/2)
    ("700000000000005", True),   # ramo temporário (prefixo 7/8/9)
    ("700000000000000", False),  # checksum errado
    ("323456789010000", False),  # primeiro dígito fora de 1,2,7,8,9
    ("12345678901000", False),   # tamanho errado
    ("", False),
])
def test_valida_cns(cns, esperado):
    assert bpa.valida_cns(cns) == esperado


def test_calcular_idade_aniversario_ja_passou_no_ano():
    assert bpa._calcular_idade("19900101", date(2026, 6, 15)) == 36


def test_calcular_idade_aniversario_ainda_nao_chegou():
    assert bpa._calcular_idade("19900801", date(2026, 6, 15)) == 35


def test_calcular_idade_atravessa_ano_bissexto():
    assert bpa._calcular_idade("20000229", date(2026, 3, 1)) == 26


def test_calcular_idade_data_invalida_retorna_zero():
    assert bpa._calcular_idade("lixo-nao-e-data", date(2026, 6, 15)) == 0


def test_normalizar_dtnasc_none_usa_data_padrao():
    assert bpa._normalizar_dtnasc(None) == "19000101"


def test_normalizar_dtnasc_aceita_date():
    assert bpa._normalizar_dtnasc(date(1990, 5, 20)) == "19900520"


def test_normalizar_dtnasc_aceita_datetime():
    assert bpa._normalizar_dtnasc(datetime(1990, 5, 20, 10, 30)) == "19900520"


def test_normalizar_dtnasc_remove_separadores():
    assert bpa._normalizar_dtnasc("1990-05-20") == "19900520"


def test_normalizar_dtnasc_string_curta_cai_no_fallback():
    assert bpa._normalizar_dtnasc("2026") == "19000101"


def test_extrair_documentos_validos_descarta_cpf_invalido():
    texto = "linha com cpf invalido 111.111.111-11\n"
    assert bpa.extrair_documentos_validos(texto) == []


def test_extrair_documentos_validos_remove_repeticao_consecutiva():
    texto = "111.444.777-35\n111.444.777-35\n"
    assert bpa.extrair_documentos_validos(texto) == ["11144477735"]


def test_extrair_documentos_validos_mantem_repeticao_nao_consecutiva():
    texto = "111.444.777-35\n123.456.789-09\n111.444.777-35\n"
    assert bpa.extrair_documentos_validos(texto) == [
        "11144477735", "12345678909", "11144477735",
    ]


def test_resolver_profissional_por_nome_auto():
    profissionais = [("111", "RAFHAELA LOPES"), ("222", "JOAO SILVA")]
    r = bpa.resolver_profissional_por_nome(profissionais, "RAFHAELA")
    assert r == {"status": "auto", "cns": "111", "nome": "RAFHAELA LOPES"}


def test_resolver_profissional_por_nome_ambiguo():
    profissionais = [("111", "MARIA SILVA"), ("222", "MARIA SANTOS")]
    r = bpa.resolver_profissional_por_nome(profissionais, "MARIA")
    assert r["status"] == "ambiguo"
    assert set(r["candidatos"]) == set(profissionais)


def test_resolver_profissional_por_nome_nao_encontrado():
    profissionais = [("111", "MARIA SILVA")]
    r = bpa.resolver_profissional_por_nome(profissionais, "PEDRO")
    assert r["status"] == "nao_encontrado"
    assert r["candidatos"] == profissionais


def test_resolver_profissional_por_nome_nao_casa_prefixo_parcial():
    """'STELA' não pode casar com 'ESTELA' -- token precisa ser palavra
    inteira (regra explícita no docstring da função)."""
    profissionais = [("111", "ESTELA COSTA")]
    r = bpa.resolver_profissional_por_nome(profissionais, "STELA")
    assert r["status"] == "nao_encontrado"


def test_dividir_em_lotes_quebra_em_blocos_de_99():
    documentos = [str(i).zfill(11) for i in range(150)]
    resultado = bpa.dividir_em_lotes(documentos, ["DR TESTE"], "15/06/2026")
    cabecalhos = [l for l in resultado.split("\n") if l.startswith("PROFISSIONAL:")]
    assert len(cabecalhos) == 2


def test_dividir_em_lotes_round_robin_entre_profissionais():
    documentos = [str(i).zfill(11) for i in range(150)]
    resultado = bpa.dividir_em_lotes(documentos, ["MEDICO A", "MEDICO B"], "15/06/2026")
    cabecalhos = [l for l in resultado.split("\n") if l.startswith("PROFISSIONAL:")]
    assert "MEDICO A" in cabecalhos[0]
    assert "MEDICO B" in cabecalhos[1]


def test_dividir_em_lotes_lista_vazia():
    assert bpa.dividir_em_lotes([], ["DR TESTE"], "15/06/2026") == ""


def test_dividir_por_profissionais_round_robin():
    documentos = [str(i).zfill(11) for i in range(150)]
    profissionais = [{"cns": "111", "nome": "A"}, {"cns": "222", "nome": "B"}]
    resultado = bpa.dividir_por_profissionais(documentos, profissionais)
    assert len(resultado["111"]) == 99
    assert len(resultado["222"]) == 51


def test_dividir_por_profissionais_sem_profissionais():
    assert bpa.dividir_por_profissionais(["123"], []) == {}


def test_nome_arquivo_lote():
    assert bpa.nome_arquivo_lote("16/04/2026") == "16-04-2026.txt"
