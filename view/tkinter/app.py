import customtkinter as ctk
from source.pp import ConfigLoader
import tkinter as tk
from tkinter import scrolledtext, messagebox
import sys
#from source.webhook import WebhookHandler,NgrokLinkGenerator
import threading
from source.manager import OKX_interface
import time
from .form import DynamicForm
import os
os.environ['TCL_LIBRARY'] = r'C:\Users\Finn\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\Finn\AppData\Local\Programs\Python\Python313\tcl\tk8.6'

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.geometry("1080x400")
        self.title("Trade Bot")

        # Configuração das colunas
        self.grid_columnconfigure(0, weight=1, minsize=200)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=2)

        # Inicialização dos componentes necessários
        self.config_loader = ConfigLoader()
        self.okx_client = OKX_interface(self.config_loader)  # Inicialize o cliente OKX aqui

        # Interface
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Estado de controle para a thread de saldo
        self.stop_thread = False
        self.start_saldo_update_thread()

    def setup_ui(self):
        # Coluna 1
        self.coluna1 = ctk.CTkFrame(self)
        self.coluna1.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.label_titulo = ctk.CTkLabel(self.coluna1, text="Trade Bot", font=("Helvetica", 20))
        self.label_titulo.pack(pady=(10, 5))

        self.label_autor = ctk.CTkLabel(self.coluna1, text="by Goulart", font=("Helvetica", 12))
        self.label_autor.pack(pady=(0, 20))

        self.botao_configurar_api = ctk.CTkButton(self.coluna1, text="Configure OKX API", command=self.configurar_okx_api)
        self.botao_configurar_api.pack(pady=10)

        # Coluna 2
        coluna2 = ctk.CTkFrame(self)
        coluna2.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        dark_bg = '#1e1e1e'
        dark_fg = '#d4d4d4'
        font = ('Courier', 10)

        self.terminal = scrolledtext.ScrolledText(coluna2, wrap=tk.WORD, state='disabled',
                                                  bg=dark_bg, fg=dark_fg, font=font, insertbackground=dark_fg)
        self.terminal.pack(expand=True, fill='both')

        # Redirecionando os prints para o terminal
        stdout_redirector = self.RedirectText(self.terminal)
        sys.stdout = stdout_redirector
        sys.stderr = stdout_redirector

        # Coluna 3
        coluna3 = ctk.CTkFrame(self)
        coluna3.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)

        self.dynamic_form = DynamicForm(self, coluna3)
        self.dynamic_form.pack(padx=10, pady=10)

        self.saldo_label = ctk.CTkLabel(coluna3, text="Saldo: U$ --", font=("Helvetica", 20))
        self.saldo_label.pack(pady=10)

    def start_saldo_update_thread(self):
        thread = threading.Thread(target=self.update_saldo, daemon=True)
        thread.start()

    def update_saldo(self):
        while not self.stop_thread:
            self.saldo_value = self.obter_saldo('USDT')
            self.saldo_label.configure(text=f"Saldo: U$ {self.saldo_value}")
            time.sleep(3)

    def obter_saldo(self, ccy=None):
        return self.okx_client.get_balance(ccy)

    def configurar_okx_api(self):
        self.janela_config = ctk.CTkToplevel(self)
        self.janela_config.title("Configure OKX API")
        self.janela_config.geometry("400x300")

        self.entries = {}

        for section in self.config_loader.config.sections():
            for key, value in self.config_loader.config.items(section):
                frame = ctk.CTkFrame(self.janela_config)
                frame.pack(fill='x', padx=10, pady=5)
                label = ctk.CTkLabel(frame, text=f"{section} - {key}")
                label.pack(side='left')
                entry = ctk.CTkEntry(frame)
                entry.insert(0, value)
                entry.pack(side='right', fill='x', expand=True)
                self.entries[f"{section}-{key}"] = entry

        salvar_botao = ctk.CTkButton(self.janela_config, text="Save", command=self.salvar_config)
        salvar_botao.pack(pady=10)

    def salvar_config(self):
        try:
            for entry_key, entry in self.entries.items():
                section, key = entry_key.split('-')
                self.config_loader.config.set(section, key, entry.get())

            with open(self.config_loader.config_file, 'w') as configfile:
                self.config_loader.config.write(configfile)

            messagebox.showinfo("Success", "Configurations saved successfully!")
            self.janela_config.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Error saving configurations: {e}")

    def on_closing(self):
        self.stop_thread = True
        self.destroy()
        sys.exit()

    class RedirectText(object):
        def __init__(self, text_widget):
            self.output = text_widget

        def write(self, string):
            self.output.config(state=tk.NORMAL)
            self.output.insert(tk.END, string)
            self.output.see(tk.END)
            self.output.config(state=tk.DISABLED)

        def flush(self):
            pass

if __name__ == "__main__":
    app = App()
    app.mainloop()
