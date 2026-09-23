"""Pacientes (CADCNS) e profissionais (CADMED) do Firebird em memória —
a busca da digitação é por letra digitada e não pode ir ao Firebird a cada
tecla. Recarregado no início, pelo botão "recarregar" e depois de migração
ou de completar CPF."""
import bpa_gerador as bpa


class CacheFirebird:
    def __init__(self) -> None:
        self.pacientes: list[dict] = []
        self.profissionais: list[dict] = []
        self.erro: str = ""

    def carregar_pacientes(self) -> None:
        try:
            self.pacientes = bpa.carregar_pacientes_cadcns()
            self.erro = ""
            print(f"[BPA] {len(self.pacientes)} pacientes carregados do Firebird.")
        except Exception as e:
            self.erro = str(e)
            print(f"[BPA] ERRO ao carregar pacientes: {e}")

    def carregar_profissionais(self) -> None:
        try:
            self.profissionais = bpa.carregar_profissionais_cadmed()
            print(f"[BPA] {len(self.profissionais)} profissionais carregados do Firebird.")
        except Exception as e:
            print(f"[BPA] ERRO ao carregar profissionais: {e}")

    def carregar_tudo(self) -> None:
        self.carregar_pacientes()
        self.carregar_profissionais()


cache = CacheFirebird()
