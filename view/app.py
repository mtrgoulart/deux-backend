import customtkinter as ctk
from source.pp import ConfigLoader,Market
import tkinter as tk
from tkinter import scrolledtext, messagebox
import sys
from source.webhook import WebhookHandler,NgrokLinkGenerator
import threading
from source.director import OperationManager
from source.manager import OperationHandler,OKX_interface,conditionHandler
import time
from .form import DynamicForm

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.geometry("1080x400")
        self.title("Trade Bot")

        # Definindo as colunas
        self.grid_columnconfigure(0, weight=1, minsize=200)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=2)

        self.config_loader = ConfigLoader()
        self.okx_client = OKX_interface(self.config_loader)

        
        
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.webhook_status = False

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

        self.botao_ativar_ngrok = ctk.CTkButton(self.coluna1, text="Activate ngrok", command=self.ativa_ngrok)
        self.botao_ativar_ngrok.pack(pady=10)

        self.botao_ativar_webhook = ctk.CTkButton(self.coluna1, text="Activate Webhook", command=self.ativar_webhook)
        self.botao_ativar_webhook.pack(pady=10)

        self.botao_desativar_webhook = ctk.CTkButton(self.coluna1, text="Deactivate Webhook", command=self.desativar_webhook, state=tk.DISABLED)
        self.botao_desativar_webhook.pack(pady=10)

        self.status_label = ctk.CTkLabel(self.coluna1, text="Webhook status:")
        self.status_label.pack(pady=10)

        self.botao_salvar = ctk.CTkButton(self.coluna1, text="Save", command=self.salvar_valores)
        self.botao_salvar.pack(pady=10)

        self.entry1 = ctk.CTkEntry(self.coluna1, placeholder_text="Conditions")
        self.entry1.pack(pady=10, padx=10)

        self.entry2 = ctk.CTkEntry(self.coluna1, placeholder_text="Interval")
        self.entry2.pack(pady=10, padx=10)

        self.entry3 = ctk.CTkEntry(self.coluna1, placeholder_text="Webhook URL")
        self.entry3.pack(pady=10, padx=10)

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

        self.dynamic_form = DynamicForm(self,coluna3)
        self.dynamic_form.pack(padx=10, pady=10)

        self.saldo_label = ctk.CTkLabel(coluna3, text="Saldo: U$ --", font=("Helvetica", 20))
        self.saldo_label.pack(pady=10)

        self.entradas_editaveis = True

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

    def salvar_valores(self):
        if self.entradas_editaveis:
            self.valor_salvo1 = self.entry1.get()
            self.valor_salvo2 = self.entry2.get()
            self.valor_salvo3 = self.entry3.get()

            self.entry1.configure(state='disabled')
            self.entry2.configure(state='disabled')
            self.entry3.configure(state='disabled')

            self.botao_salvar.configure(text="Edit")
            self.entradas_editaveis = False
            self.status_label.configure(text="Values saved and fields locked!")
        else:
            self.entry1.configure(state='normal')
            self.entry2.configure(state='normal')
            self.entry3.configure(state='normal')

            self.botao_salvar.configure(text="Save")
            self.entradas_editaveis = True
            self.status_label.configure(text="Fields unlocked for editing!")

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

    def ativa_ngrok(self):
        ngrok = NgrokLinkGenerator()
        link = ngrok.generate_link()
        return link
    
    def update_status_indicator(self):
        if self.webhook_status:
            self.status_label.configure(text="Webhook status: On")
        else:
            self.status_label.configure(text="Webhook status: Off")

    def iniciar_operation_manager(self,url,percent,saldo,condition,interval,symbol):
        self.operation_manager = OperationManager(
            webhook_url=url,
            percent=percent,
            avaiable_size=saldo,
            condition_limit=condition,
            interval=interval,
            symbol=symbol
        )
        

        self.operation_manager.start_operation()
        self.webhook_status = True

    def ativar_webhook(self):
        print("\nAtivando Webhook...")

        self.botao_ativar_webhook.configure(state=tk.DISABLED)
        self.botao_desativar_webhook.configure(state=tk.NORMAL)
        self.update_status_indicator()
        self.iniciar_operation_manager(url=self.valor_salvo3,
            percent=0.01,
            saldo=self.saldo_value,
            condition=self.valor_salvo1,
            interval=self.valor_salvo2,
            symbol='BTC-USDT')        

        self.webhook_status = True
        self.update_status_indicator()

    def desativar_webhook(self):
        self.botao_ativar_webhook.configure(state=tk.NORMAL)
        self.botao_desativar_webhook.configure(state=tk.DISABLED)
        self.webhook_status = False
        self.update_status_indicator()
        print("\n\nWebhook desativado\n\n======================================")

    def on_closing(self):
        if self.webhook_status:
            self.desativar_webhook()
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
