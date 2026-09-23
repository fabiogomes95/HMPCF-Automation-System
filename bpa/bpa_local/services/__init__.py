"""Regras do BPA local. Cada função recebe dados já lidos da requisição e
devolve o dict/list que vira JSON — mesmas respostas do antigo app Flask
(a página atual e a aba BPA do sistema dependem desse formato)."""
import re


def limpar(valor) -> str:
    return re.sub(r"\D", "", str(valor)) if valor else ""
