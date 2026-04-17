# ==============================================================================
# 🚀 ASSISTENTE BPA: ORGANIZAÇÃO DE LOTE ÚNICO POR DATA (VERSÃO TURBO GUI)
# ==============================================================================
# ESTE SCRIPT TEM 3 OBJETIVOS PRINCIPAIS:
# 1. RAPIDEZ: Carrega 27 mil pacientes na memória RAM para busca instantânea.
# 2. ORGANIZAÇÃO: Agrupa vários profissionais em um único arquivo TXT por data.
# 3. ERGONOMIA: Totalmente operável via teclado (Enter/Tab) para agilizar o fluxo.
# ==============================================================================

import os
import re
import tkinter as tk          
from tkinter import messagebox 

# ==============================================================================
# 1. CARREGAMENTO DA BASE DE DADOS (EXPACIENTE.TXT)
# ==============================================================================
def carregar_base():
    """
    Função que lê o arquivo bruto do DATASUS e organiza os dados em memória.
    Em Análise de Sistemas, isso é chamado de 'Data Mapping' (Mapeamento de Dados).
    """
    caminho_datasus = os.path.join(os.path.dirname(__file__), "ExpPaciente.txt")
    pacientes = []
    
    # Verifica se o arquivo existe para evitar que o programa feche com erro (Crash)
    if not os.path.exists(caminho_datasus):
        messagebox.showerror("Erro Crítico", f"Arquivo '{caminho_datasus}' não encontrado.")
        return pacientes

    # 'latin-1' é a codificação usada pelos sistemas legados do Governo (BPA/DATASUS)
    with open(caminho_datasus, 'r', encoding='latin-1', errors='ignore') as f:
        for linha in f:
            # Filtro de segurança: Linhas menores que 53 caracteres estão incompletas no layout
            if len(linha) >= 53:
                # O Slicing [x:y] extrai caracteres em posições fixas (Layout Posicional)
                sus = linha[0:15].strip()
                nome = linha[15:45].strip()
                dn_bruta = linha[45:53].strip() # Posição oficial da Data de Nascimento
                
                # Formatação de Data: Inverte AAAAMMDD para o padrão brasileiro DD/MM/AAAA
                dn = f"{dn_bruta[6:8]}/{dn_bruta[4:6]}/{dn_bruta[0:4]}" if len(dn_bruta) == 8 else "00/00/0000"

                # REGEX: 're.search' busca 11 números seguidos (padrão de CPF) em qualquer parte da linha
                match_cpf = re.search(r'\d{11}', linha)
                cpf = match_cpf.group(0) if match_cpf else ""

                # Apenas pacientes com SUS válido (15 dígitos) entram na nossa lista de busca
                if len(sus) == 15:
                    pacientes.append((sus, nome, dn, cpf))
    return pacientes

# ==============================================================================
# 2. CLASSE DA INTERFACE GRÁFICA (LÓGICA DA GUI)
# ==============================================================================
class AssistenteBPA:
    def __init__(self, root, base_pacientes):
        """Inicializa a interface e define as variáveis de controle do lote."""
        self.root = root
        self.base_pacientes = base_pacientes
        self.ficheiro_dia = ""
        self.medico_atual = ""
        self.data_atual = ""
        
        # Título e dimensões da janela principal
        self.root.title("⚡ Assistente BPA - Gestão de Produção")
        self.root.geometry("700x650")
        self.root.config(padx=20, pady=20)

        # ----------------------------------------------------------------------
        # TELA 1: CONFIGURAÇÃO (LOGIN DO PROFISSIONAL)
        # ----------------------------------------------------------------------
        self.frame_config = tk.Frame(self.root)
        self.frame_config.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(self.frame_config, text="Nome do Médico ou Enfermeiro:", font=("Arial", 11)).pack(pady=5)
        self.entry_medico = tk.Entry(self.frame_config, font=("Arial", 14), width=30)
        self.entry_medico.pack(pady=5)
        self.entry_medico.focus_set() # Inicia o cursor aqui para você não precisar clicar

        tk.Label(self.frame_config, text="Data do Atendimento (Ex: 30012026):", font=("Arial", 11)).pack(pady=5)
        self.entry_data = tk.Entry(self.frame_config, font=("Arial", 14), width=30)
        self.entry_data.pack(pady=5)
        
        # ATALHOS DE TECLADO TELA 1:
        # 'Return' (Enter) na data aciona a função de iniciar a digitação
        self.entry_data.bind("<Return>", self.iniciar_sessao)
        # 'Tab' no campo médico pula para o campo data (Comportamento nativo do Windows)

        self.btn_iniciar = tk.Button(self.frame_config, text="Iniciar Produção (ENTER)", command=self.iniciar_sessao, 
                                     bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
        self.btn_iniciar.pack(pady=20)

        # ----------------------------------------------------------------------
        # TELA 2: ÁREA DE PESQUISA (MODO DIGITAÇÃO)
        # ----------------------------------------------------------------------
        self.frame_pesquisa = tk.Frame(self.root)
        
        # Cabeçalho informativo sobre o arquivo e profissional ativo
        self.lbl_info = tk.Label(self.frame_pesquisa, text="", font=("Arial", 10, "bold"), fg="darkblue")
        self.lbl_info.pack(pady=2)
        
        self.lbl_status = tk.Label(self.frame_pesquisa, text="Aguardando busca...", font=("Arial", 9))
        self.lbl_status.pack()

        # Campo principal de pesquisa (Nome/CPF/SUS)
        self.entry_busca = tk.Entry(self.frame_pesquisa, font=("Arial", 16), width=40)
        self.entry_busca.pack(pady=5, fill=tk.X)
        
        # EVENTOS DE TECLADO TELA 2:
        self.entry_busca.bind("<KeyRelease>", self.filtrar_resultados) # Filtra a cada tecla pressionada
        self.entry_busca.bind("<Tab>", self.focar_lista)               # TAB pula para a lista
        self.entry_busca.bind("<Down>", self.focar_lista)              # Seta baixo pula para a lista
        
        # Lista visual de resultados (Listbox)
        self.lista_resultados = tk.Listbox(self.frame_pesquisa, font=("Consolas", 11), height=15, exportselection=False)
        self.lista_resultados.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # ENTER na lista executa o salvamento
        self.lista_resultados.bind("<Return>", self.salvar_e_limpar)
        self.lista_resultados.bind("<Double-Button-1>", self.salvar_e_limpar)

        # Botão para trocar de profissional sem fechar o programa
        tk.Button(self.frame_pesquisa, text="↩ Trocar Profissional", command=self.voltar_config, bg="#f44336", fg="white").pack(pady=5)

    # ----------------------------------------------------------------------
    # 3. LÓGICA DE GESTÃO DE ARQUIVOS (SESSÃO)
    # ----------------------------------------------------------------------
    def iniciar_sessao(self, event=None):
        """
        Valida os dados e cria/abre o arquivo único do dia.
        Insere o cabeçalho do médico atual no final do arquivo (Append).
        """
        self.medico_atual = self.entry_medico.get().strip().upper()
        self.data_atual = self.entry_data.get().strip()
        
        if not self.medico_atual or not self.data_atual:
            messagebox.showwarning("Aviso", "Preencha o profissional e a data!")
            return
            
        # O nome do arquivo é fixo pela DATA (Um arquivo agrupa todos os médicos do dia)
        self.ficheiro_dia = f"PRODUCAO_{self.data_atual}.txt"
        
        # Formata a data para exibir bonito no cabeçalho interno
        d = self.data_atual
        data_fmt = f"{d[0:2]}/{d[2:4]}/{d[4:8]}"

        # Abre o arquivo no modo 'a' (Append). Se não existir, ele cria. Se existir, ele anexa no final.
        with open(self.ficheiro_dia, 'a', encoding='utf-8') as f:
            # Se o arquivo já tiver conteúdo, pula duas linhas para separar os profissionais
            if os.path.exists(self.ficheiro_dia) and os.path.getsize(self.ficheiro_dia) > 0:
                f.write("\n\n")
            
            # Escreve o cabeçalho separador do profissional atual
            f.write("==================================================\n")
            f.write(f"PROFISSIONAL: {self.medico_atual}\n")
            f.write(f"DATA: {data_fmt}\n")
            f.write("==================================================\n")

        # Atualiza a interface: Esconde a configuração e mostra a pesquisa
        self.lbl_info.config(text=f"ARQUIVO: {self.ficheiro_dia}\nPROFISSIONAL: {self.medico_atual}")
        self.frame_config.pack_forget()
        self.frame_pesquisa.pack(fill=tk.BOTH, expand=True)
        self.entry_busca.focus_set() # Foca no campo de busca para começar a digitar o paciente
        self.atualizar_lista(self.base_pacientes[:50])

    # ----------------------------------------------------------------------
    # 4. LÓGICA DE PESQUISA E SALVAMENTO (OPERACIONAL)
    # ----------------------------------------------------------------------
    def filtrar_resultados(self, event):
        """Realiza a filtragem dinâmica baseada no que o usuário digita no campo de busca."""
        # Teclas de controle não devem disparar a pesquisa novamente
        if event.keysym in ('Tab', 'Down', 'Up', 'Return'): return
        
        termo = self.entry_busca.get().strip().upper()
        
        # Se o campo estiver vazio, mostra os primeiros 50 da base
        if not termo:
            self.atualizar_lista(self.base_pacientes[:50])
            return
        
        # List Comprehension: Filtra por Nome[1], SUS[0] ou CPF[3]
        res = [p for p in self.base_pacientes if termo in p[1] or termo in p[0] or termo in p[3]][:50]
        self.atualizar_lista(res)

    def atualizar_lista(self, resultados):
        """Limpa a Listbox e insere os novos resultados encontrados."""
        self.lista_resultados.delete(0, tk.END)
        for sus, nome, dn, cpf in resultados:
            # Exibe os dados formatados para conferência visual rápida
            self.lista_resultados.insert(tk.END, f"{sus} | {dn} | {nome}")

    def focar_lista(self, event):
        """Move o foco do teclado para a lista, permitindo selecionar o paciente com as setas."""
        if self.lista_resultados.size() > 0:
            self.lista_resultados.focus_set()
            self.lista_resultados.selection_set(0) # Seleciona o primeiro da lista automaticamente
            self.lista_resultados.activate(0)
            return "break" # Impede que o 'Tab' faça o foco sair do programa

    def salvar_e_limpar(self, event):
        """
        Função acionada pelo ENTER na lista.
        Extrai o SUS, salva no arquivo diário e reseta o campo para a próxima busca.
        """
        selecao = self.lista_resultados.curselection()
        if not selecao: return
        
        # Pega o texto da linha selecionada
        item = self.lista_resultados.get(selecao[0])
        sus = item[:15] # Os primeiros 15 caracteres são sempre o SUS
        nome_paciente = item[28:].strip() # Pega o nome para mostrar no feedback

        try:
            # Salva apenas o número do SUS, um por linha, conforme exigência do robô RPA
            with open(self.ficheiro_dia, 'a', encoding='utf-8') as f:
                f.write(sus + "\n")
            
            # Feedback visual de que o dado foi gravado com sucesso
            self.lbl_status.config(text=f"✅ SALVO NO LOTE: {nome_paciente}", fg="green")
            
            # Reseta o campo de busca e volta o cursor para lá automaticamente
            self.entry_busca.delete(0, tk.END)
            self.atualizar_lista(self.base_pacientes[:50])
            self.entry_busca.focus_set()
            
        except Exception as e:
            messagebox.showerror("Erro de Gravação", f"Não foi possível salvar no arquivo: {e}")

    def voltar_config(self):
        """Volta para a tela inicial para trocar de médico sem fechar o arquivo diário."""
        self.frame_pesquisa.pack_forget()
        self.frame_config.pack(fill=tk.BOTH, expand=True)
        self.entry_medico.focus_set()

# ==============================================================================
# INICIALIZAÇÃO DO SISTEMA
# ==============================================================================
if __name__ == "__main__":
    # Carrega a base antes de abrir a janela para garantir que os dados já estejam prontos
    base = carregar_base()
    if base:
        root = tk.Tk()
        app = AssistenteBPA(root, base)
        root.mainloop() # Mantém a janela aberta e escutando os eventos de teclado