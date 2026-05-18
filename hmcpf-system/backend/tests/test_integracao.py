"""Testes unitários para o módulo de integração."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.modules.integracao.service import (
    _remove_accents,
    _apenas_numeros,
    _valida_cns,
    _dn_iso,
    _parse_endereco,
    _format_telefone,
    _gerar_linha_bpa,
    _salvar_buffer,
)


class TestHelpers(unittest.TestCase):
    def test_remove_accents(self):
        self.assertEqual(_remove_accents("João Souza"), "JOAO SOUZA")
        self.assertEqual(_remove_accents("Coração"), "CORACAO")
        self.assertEqual(_remove_accents(""), "")
        self.assertEqual(_remove_accents("MARIA"), "MARIA")

    def test_apenas_numeros(self):
        self.assertEqual(_apenas_numeros("123.456.789-00"), "12345678900")
        self.assertEqual(_apenas_numeros("(84) 9999-8888"), "8499998888")
        self.assertEqual(_apenas_numeros(""), "")
        self.assertEqual(_apenas_numeros(None), "")

    def test_valida_cns(self):
        # CNS inválido (não passa no dígito verificador)
        self.assertFalse(_valida_cns("123456789012345"))
        self.assertFalse(_valida_cns(""))
        self.assertFalse(_valida_cns("1234"))
        self.assertFalse(_valida_cns("12345678901234"))  # 14 dígitos
        # Deve ter 15 dígitos começando com 1,2,7,8,9
        self.assertFalse(_valida_cns("012345678901234"))  # começa com 0

    def test_dn_iso(self):
        self.assertEqual(_dn_iso("01/02/1990"), "19900201")
        self.assertEqual(_dn_iso("01-02-1990"), "19900201")
        self.assertEqual(_dn_iso("19900101"), "19900101")
        self.assertEqual(_dn_iso(""), "19900101")
        self.assertEqual(_dn_iso(None), "19900101")

    def test_parse_endereco_estruturado(self):
        rua, num, bairro = _parse_endereco("Rua das Flores, 123 - Centro")
        self.assertEqual(rua, "RUA DAS FLORES")
        self.assertEqual(num, "123")
        self.assertEqual(bairro, "CENTRO")

    def test_parse_endereco_baguncado(self):
        rua, num, bairro = _parse_endereco("RUA 1, 456 APT 302 PONTA NEGRA")
        # Último número (302) vira o número, ou "456" se estruturado
        self.assertIn(num, ("456", "302"))
        self.assertTrue(len(rua) > 0)

    def test_parse_endereco_vazio(self):
        rua, num, bairro = _parse_endereco("")
        self.assertEqual(rua, "NAO INFORMADO")
        self.assertEqual(num, "S/N")
        self.assertEqual(bairro, "CENTRO")

    def test_format_telefone_completo(self):
        ddd, fone = _format_telefone("84981881207")
        self.assertEqual(ddd, "84")
        self.assertEqual(fone, "981881207")

    def test_format_telefone_8dig(self):
        ddd, fone = _format_telefone("99998888")
        self.assertEqual(ddd, "84")
        self.assertEqual(fone, "999988880")

    def test_gerar_linha_bpa(self):
        linha = _gerar_linha_bpa(
            sus="174657188440009",
            nome="JOAO SOUZA".ljust(30),
            dn="19900201",
            sexo="M",
            endereco="RUA DAS FLORES".ljust(30),
            numero="123".ljust(5),
            bairro="CENTRO".ljust(15),
            ddd="84",
            fone="981881207",
        )
        self.assertEqual(len(linha.rstrip("\r\n")), 167)
        self.assertIn("JOAO SOUZA", linha)
        self.assertIn("174657188440009", linha)
        self.assertIn("RUA DAS FLORES", linha)
        self.assertIn("\r\n", linha)

    def test_salvar_buffer(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "teste.txt"
            result = _salvar_buffer("conteudo", str(path))
            self.assertEqual(path.read_text(), "conteudo")
            self.assertEqual(result, str(path.resolve()))


if __name__ == "__main__":
    unittest.main()
