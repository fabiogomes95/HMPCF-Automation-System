# ==============================================================================
# 🚀 ASSISTENTE BPA: VISUALIZAÇÃO FORMATADA (SUS & CPF)
# ==============================================================================
# Desenvolvido por: Fábio Gomes da Silva
# Objetivo: Priorizar o CPF e exibir dados com máscaras para facilitar a leitura.
# ==============================================================================

import os
import tkinter as tk
from tkinter import messagebox
import firebirdsql 

# ==============================================================================
# 1. CARREGAMENTO DA BASE DE DADOS (FIREBIRD)
# ==============================================================================
def carregar_base():
    """Conecta ao BPAMAG.GDB e carrega os pacientes para a memória RAM."""
    caminho_gdb = r'C:/BPA/BPAMAG.GDB'
    pacientes = []
    try:
        con = firebirdsql.connect(
            host='localhost', database=caminho_gdb,
            user='SYSDBA', password='masterkey', charset='WIN1252'
        )
        cur = con.cursor()
        cur.execute("SELECT CNS, NOME, DTNASC, NUM_CPF FROM CADCNS")
        rows = cur.fetchall()
        for r in rows:
            sus = str(r[0] or "").strip()
            nome = str(r[1] or "").strip().upper()
            dn_raw = str(r[2] or "").strip()
            cpf = str(r[3] or "").strip()
            
            # Formata data para visualização: AAAAMMDD -> DD/MM/AAAA
            dn = f"{dn_raw[6:8]}/{dn_raw[4:6]}/{dn_raw[0:4]}" if len(dn_raw) == 8 else "  /  /    "
            pacientes.append((sus, nome, dn, cpf))
        con.close()
        return pacientes
    except Exception as e:
        messagebox.showerror("Erro de Conexão", f"Não foi possível acessar o banco BPA:\n{e}")
        return []

# ==============================================================================
# 2. INTERFACE GRÁFICA (GUI)
# ==============================================================================
class AssistenteBPA:
    def __init__(self, root, base_pacientes):
        self.root = root
        self.base_pacientes = base_pacientes
        self.ficheiro_dia = ""
        
        self.root.title("⚡ Assistente BPA - HMPCF - Visualização Formatada")
        self.root.geometry("1000x650") # Largura aumentada para as máscaras de texto
        self.root.config(padx=20, pady=20)
        
        # TELA 1: CONFIGURAÇÃO DO LOTE
        self.frame_config = tk.Frame(self.root)
        self.frame_config.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(self.frame_config, text="Nome do Profissional:", font=("Arial", 12)).pack(pady=5)
        self.entry_medico = tk.Entry(self.frame_config, font=("Arial", 16), width=35)
        self.entry_medico.pack(pady=5)
        self.entry_medico.focus_set()
        
        tk.Label(self.frame_config, text="Data do Lote (DDMMYYYY):", font=("Arial", 12)).pack(pady=5)
        self.entry_data = tk.Entry(self.frame_config, font=("Arial", 16), width=35)
        self.entry_data.pack(pady=5)
        self.entry_data.bind("<Return>", self.iniciar_sessao)
        
        tk.Button(self.frame_config, text="INICIAR PRODUÇÃO", command=self.iniciar_sessao, 
                  bg="#2E7D32", fg="white", font=("Arial", 12, "bold"), height=2).pack(pady=30)
        
        # TELA 2: MODO OPERACIONAL (DIGITAÇÃO)
        self.frame_pesquisa = tk.Frame(self.root)
        self.lbl_info = tk.Label(self.frame_pesquisa, text="", font=("Arial", 11, "bold"), fg="#1565C0")
        self.lbl_info.pack(pady=5)
        
        self.lbl_status = tk.Label(self.frame_pesquisa, text="Pesquise por Nome, CPF ou SUS...", font=("Arial", 10))
        self.lbl_status.pack()
        
        self.entry_busca = tk.Entry(self.frame_pesquisa, font=("Arial", 22), bg="#FFFDE7")
        self.entry_busca.pack(pady=10, fill=tk.X)
        
        self.entry_busca.bind("<KeyRelease>", self.filtrar_resultados)
        self.entry_busca.bind("<Tab>", self.focar_lista)
        self.entry_busca.bind("<Down>", self.focar_lista)
        
        self.lista_resultados = tk.Listbox(
            self.frame_pesquisa, font=("Consolas", 14), height=15, 
            selectbackground="#1976D2", bg="#F5F5F5", exportselection=False
        )
        self.lista_resultados.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.lista_resultados.bind("<Return>", self.salvar_e_limpar)
        self.lista_resultados.bind("<Tab>", self.navegar_com_tab)
        
        tk.Button(self.frame_pesquisa, text="↩ Mudar Profissional", command=self.voltar_config, 
                  bg="#C62828", fg="white").pack(pady=5, side=tk.RIGHT)

    def iniciar_sessao(self, event=None):
        medico = self.entry_medico.get().strip().upper()
        data = self.entry_data.get().strip()
        if not medico or not data: return
        
        pasta = os.path.dirname(os.path.abspath(__file__))
        self.ficheiro_dia = os.path.join(pasta, f"PRODUCAO_{data}.txt")
        
        with open(self.ficheiro_dia, 'a', encoding='utf-8') as f:
            f.write(f"\n{'-'*50}\nPROFISSIONAL: {medico} | DATA: {data}\n{'-'*50}\n")
            
        self.lbl_info.config(text=f"👨‍⚕️ {medico} | 📅 {data}")
        self.frame_config.pack_forget()
        self.frame_pesquisa.pack(fill=tk.BOTH, expand=True)
        self.entry_busca.focus_set()
        self.atualizar_lista(self.base_pacientes[:50])

    def filtrar_resultados(self, event):
        if event.keysym in ('Tab', 'Down', 'Up', 'Return'): return
        termo = self.entry_busca.get().strip().upper()
        if not termo:
            self.atualizar_lista(self.base_pacientes[:50])
            return
        res = [p for p in self.base_pacientes if termo in p[1] or termo in p[0] or termo in p[3]][:50]
        self.atualizar_lista(res)

    # ----------------------------------------------------------------------
    # 🎯 ATUALIZAÇÃO VISUAL: MÁSCARAS DE SUS E CPF
    # ----------------------------------------------------------------------
    def atualizar_lista(self, resultados):
        """Aplica máscaras visuais e garante alinhamento das colunas."""
        self.lista_resultados.delete(0, tk.END)
        for sus, nome, dn, cpf in resultados:
            # Máscara SUS: 000 0000 0000 0000
            sus_fmt = f"{sus[0:3]} {sus[3:7]} {sus[7:11]} {sus[11:15]}" if len(sus) == 15 else sus
            
            # Máscara CPF: 000.000.000-00
            cpf_fmt = f"{cpf[0:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}" if len(cpf) == 11 else cpf

            c_nome = f"{nome[:30]:<30}"
            c_dn   = f"{dn:<12}"
            c_sus  = f"{sus_fmt:<20}" # Aumentado para acomodar os espaços
            c_cpf  = f"CPF: {cpf_fmt if cpf_fmt else '              '}"
            
            self.lista_resultados.insert(tk.END, f"{c_nome} | {c_dn} | {c_sus} | {c_cpf}")

    def focar_lista(self, event):
        if self.lista_resultados.size() > 0:
            self.lista_resultados.focus_set()
            self.lista_resultados.selection_set(0)
            self.lista_resultados.activate(0)
        return "break"

    def navegar_com_tab(self, event):
        selecao = self.lista_resultados.curselection()
        if selecao:
            prox = selecao[0] + 1
            if prox < self.lista_resultados.size():
                self.lista_resultados.selection_clear(selecao[0])
                self.lista_resultados.selection_set(prox)
                self.lista_resultados.activate(prox)
        return "break"

    def salvar_e_limpar(self, event):
        """Salva o CPF (prioridade) ou SUS limpos no arquivo TXT."""
        selecao = self.lista_resultados.curselection()
        if not selecao: return
        
        item = self.lista_resultados.get(selecao[0])
        partes = item.split(" | ")
        
        nome_paciente = partes[0].strip()
        # Limpa espaços da máscara do SUS
        sus_paciente = partes[2].replace(" ", "").strip()
        # Limpa pontos e traço da máscara do CPF
        cpf_paciente = partes[3].replace("CPF:", "").replace(".", "").replace("-", "").strip()
        
        # Prioridade CPF
        documento_final = cpf_paciente if cpf_paciente else sus_paciente
        
        if not documento_final:
            messagebox.showwarning("Aviso", f"Paciente {nome_paciente} sem documento!")
            return

        try:
            with open(self.ficheiro_dia, 'a', encoding='utf-8') as f:
                f.write(documento_final + "\n")
                
            self.lbl_status.config(text=f"✅ GRAVADO: {nome_paciente}", fg="#2E7D32")
            self.entry_busca.delete(0, tk.END)
            self.entry_busca.focus_set()
            self.atualizar_lista(self.base_pacientes[:50])
            
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar: {e}")

    def voltar_config(self):
        self.frame_pesquisa.pack_forget()
        self.frame_config.pack(fill=tk.BOTH, expand=True)
        self.entry_medico.focus_set()

if __name__ == "__main__":
    base = carregar_base()
    if base:
        root = tk.Tk()
        app = AssistenteBPA(root, base)
        root.mainloop()