"""Pacientes (CADCNS) e profissionais (CADMED) do Firebird em memória —
a busca da digitação é por letra digitada e não pode ir ao Firebird a cada
tecla. Recarregado no início, pelo botão "recarregar" e depois de migração
ou de completar CPF.

Ao ligar o PC, a tarefa HMPCF-BPA liga este processo ~30s depois do logon,
mas o Firebird do BPA Magnético (fbguard/fbserver) liga por fora, sem
sincronia com isso -- em boots mais lentos pode ainda não estar de pé nesse
momento. Se a primeira carga falhar, tenta de novo sozinho em segundo plano
(mesma ideia da migração automática) em vez de ficar quebrado até alguém
clicar em "recarregar".

Carga inicial rápida: a CADCNS inteira (~20 mil linhas) demora bem mais que
os profissionais (46 linhas) pra trazer do Firebird e converter em Python --
isso sozinho já segurava a tela por um bom tempo a cada boot. Por isso a
largada carrega só os CARGA_INICIAL_PACIENTES cadastros mais recentes (maior
ID_CADCNS -- os pacientes mais prováveis de aparecer na digitação do mês
corrente) e devolve a tela na hora; a CADCNS completa vem depois, sozinha,
em segundo plano, substituindo a amostra quando terminar."""
import threading
import time

import bpa_gerador as bpa

# Falhou (Firebird ainda não subiu / fechado): tenta de novo a cada tanto,
# sem martelar -- se for erro de verdade (senha errada, .GDB sumiu), ainda assim
# desiste de ficar tentando pra sempre.
ESPERA_ENTRE_TENTATIVAS = 15
TENTATIVAS_MAXIMAS = 20  # ~5 min

CARGA_INICIAL_PACIENTES = 4000  # cadastros mais recentes -- carga rápida pra abrir a tela


class CacheFirebird:
    def __init__(self) -> None:
        self.pacientes: list[dict] = []
        self.profissionais: list[dict] = []
        self.erro: str = ""
        self.pacientes_completo = False  # False = só a amostra recente (carga inicial)
        self._retentando = False
        self._lock_retentando = threading.Lock()

    def carregar_pacientes(self, limite: int | None = None) -> None:
        try:
            self.pacientes = bpa.carregar_pacientes_cadcns(limite)
            self.erro = ""
            self.pacientes_completo = limite is None
            rotulo = f"{len(self.pacientes)} mais recentes" if limite else str(len(self.pacientes))
            print(f"[BPA] {rotulo} pacientes carregados do Firebird.")
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
        """Chamado na largada do BPA -- só a parte rápida (profissionais +
        amostra recente de pacientes), pra tela responder já. A CADCNS
        inteira é buscada depois, sem segurar o startup."""
        self.carregar_profissionais()
        self.carregar_pacientes(CARGA_INICIAL_PACIENTES)
        if self.erro:
            self._tentar_de_novo_em_segundo_plano()
        else:
            threading.Thread(
                target=self._carregar_pacientes_completo_em_segundo_plano,
                name="cache-firebird-completo", daemon=True,
            ).start()

    def _carregar_pacientes_completo_em_segundo_plano(self) -> None:
        self.carregar_pacientes()  # CADCNS inteira, substitui a amostra recente
        if self.erro:
            self._tentar_de_novo_em_segundo_plano()

    def recarregar_tudo(self) -> None:
        """Botão "recarregar" -- ação deliberada do usuário (ex.: depois de
        completar CPF de um paciente antigo), então traz a CADCNS inteira na
        hora em vez da amostra recente da largada."""
        self.carregar_profissionais()
        self.carregar_pacientes()
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
