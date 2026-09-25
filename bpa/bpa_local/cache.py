"""Pacientes (CADCNS) e profissionais (CADMED) do Firebird em memória —
a busca da digitação é por letra digitada e não pode ir ao Firebird a cada
tecla. Recarregado no início, pelo botão "recarregar" e depois de migração
ou de completar CPF.

Ao ligar o PC, a tarefa HMPCF-BPA liga este processo ~30s depois do logon,
mas o Firebird do BPA Magnético (fbguard/fbserver) liga por fora, sem
sincronia com isso -- em boots mais lentos pode ainda não estar de pé nesse
momento. Se a primeira carga falhar, tenta de novo sozinho em segundo plano
(mesma ideia da migração automática) em vez de ficar quebrado até alguém
clicar em "recarregar"."""
import threading
import time

import bpa_gerador as bpa

# Falhou (Firebird ainda não subiu / fechado): tenta de novo a cada tanto,
# sem martelar -- se for erro de verdade (senha errada, .GDB sumiu), ainda assim
# desiste de ficar tentando pra sempre.
ESPERA_ENTRE_TENTATIVAS = 15
TENTATIVAS_MAXIMAS = 20  # ~5 min


class CacheFirebird:
    def __init__(self) -> None:
        self.pacientes: list[dict] = []
        self.profissionais: list[dict] = []
        self.erro: str = ""
        self._retentando = False
        self._lock_retentando = threading.Lock()

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
        if self.erro:
            self._tentar_de_novo_em_segundo_plano()

    def _tentar_de_novo_em_segundo_plano(self) -> None:
        with self._lock_retentando:
            if self._retentando:
                return  # já tem uma tentativa em andamento
            self._retentando = True
        threading.Thread(target=self._laco_retentativas, name="cache-firebird-retry", daemon=True).start()

    def _laco_retentativas(self) -> None:
        try:
            for tentativa in range(1, TENTATIVAS_MAXIMAS + 1):
                time.sleep(ESPERA_ENTRE_TENTATIVAS)
                print(f"[BPA] Firebird ainda não respondeu -- tentativa {tentativa}/{TENTATIVAS_MAXIMAS}...")
                self.carregar_pacientes()
                self.carregar_profissionais()
                if not self.erro:
                    return
        finally:
            with self._lock_retentando:
                self._retentando = False


cache = CacheFirebird()
