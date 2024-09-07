import customtkinter as ctk
from source.pp import ConfigLoader,Market
import tkinter as tk
from tkinter import scrolledtext, messagebox
import sys
from source.webhook import WebhookHandler,NgrokLinkGenerator
import threading
from source.manager import OperationHandler,OKX_interface,conditionHandler
import time

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
        self.okx_client=OKX_interface(self.config_loader)
        
        self.languages = {
            "en": {
                "title": "Trade Bot",
                "author": "by Goulart",
                "config_api": "Configure OKX API",
                "activate_webhook": "Activate Webhook",
                "deactivate_webhook": "Deactivate Webhook",
                "webhook_status": "Webhook status:",
                "status_on": "Webhook status: \nOn",
                "status_off": "Webhook status: \nOff",
                "save": "Save",
                "config_title": "Configure OKX API",
                "success": "Success",
                "save_success": "Configurations saved successfully!",
                "error": "Error",
                "save_error": "Error saving configurations:"
            },
            "es": {
                "title": "Trade Bot",
                "author": "por Goulart",
                "config_api": "Configurar API de OKX",
                "activate_webhook": "Activar Webhook",
                "deactivate_webhook": "Desactivar Webhook",
                "webhook_status": "Estado del Webhook:",
                "status_on": "Estado del Webhook: \nEncendido",
                "status_off": "Estado del Webhook: \nApagado",
                "botao_ativar_ngrok":"Activar ngrok",
                "save": "Guardar",
                "config_title": "Configurar API de OKX",
                "success": "Éxito",
                "save_success": "¡Configuraciones guardadas con éxito!",
                "error": "Error",
                "save_error": "Error al guardar configuraciones:"
            },
            "pt": {
                "title": "Trade Bot",
                "author": "por Goulart",
                "config_api": "Configurar API da OKX",
                "activate_webhook": "Ativar Webhook",
                "deactivate_webhook": "Desativar Webhook",
                "webhook_status": "Status do Webhook:",
                "status_on": "Status do Webhook: \nLigado",
                "status_off": "Status do Webhook: \nDesligado",
                "save": "Salvar",
                "config_title": "Configurar API da OKx",
                "success": "Sucesso",
                "save_success": "Configurações salvas com sucesso!",
                "error": "Erro",
                "save_error": "Erro ao salvar configurações:"
            }
        }
        
        self.current_language = "es"
        
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.webhook_status = False

        self.stop_thread = False
        self.start_saldo_update_thread()
        

    def setup_ui(self):
        # Menu de idiomas
        menu_bar = tk.Menu(self)
        lang_menu = tk.Menu(menu_bar, tearoff=0)
        lang_menu.add_command(label="English", command=lambda: self.change_language("en"))
        lang_menu.add_command(label="Español", command=lambda: self.change_language("es"))
        lang_menu.add_command(label="Português", command=lambda: self.change_language("pt"))
        menu_bar.add_cascade(label="Language", menu=lang_menu)
        self.config(menu=menu_bar)

        # Coluna 1
        self.coluna1 = ctk.CTkFrame(self)
        self.coluna1.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.label_titulo = ctk.CTkLabel(self.coluna1, font=("Helvetica", 20))
        self.label_titulo.pack(pady=(10, 5))

        self.label_autor = ctk.CTkLabel(self.coluna1, font=("Helvetica", 12))
        self.label_autor.pack(pady=(0, 20))

        self.botao_configurar_api = ctk.CTkButton(self.coluna1, command=self.configurar_okx_api)
        self.botao_configurar_api.pack(pady=10)

        self.botao_ativar_ngrok = ctk.CTkButton(self.coluna1, command=self.ativa_ngrok)
        self.botao_ativar_ngrok.pack(pady=10)

        self.botao_ativar_webhook = ctk.CTkButton(self.coluna1, command=self.ativar_webhook)
        self.botao_ativar_webhook.pack(pady=10)

        self.botao_desativar_webhook = ctk.CTkButton(self.coluna1, command=self.desativar_webhook, state=tk.DISABLED)
        self.botao_desativar_webhook.pack(pady=10)

        self.status_label = ctk.CTkLabel(self.coluna1)
        self.status_label.pack(pady=10)

        self.botao_salvar = ctk.CTkButton(self.coluna1, text="Salvar", command=self.salvar_valores)
        self.botao_salvar.pack(pady=10)

        self.entry1 = ctk.CTkEntry(self.coluna1, placeholder_text="Conditions")
        self.entry1.pack(pady=10, padx=10)

        self.entry2 = ctk.CTkEntry(self.coluna1, placeholder_text="Value")
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

        # Coluna 3 (opcional, pode ser usada para outros controles ou informações)
        coluna3 = ctk.CTkFrame(self)
        coluna3.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)

        self.saldo_label = ctk.CTkLabel(coluna3, text="Saldo: U$ --", font=("Helvetica", 20))
        self.saldo_label.pack(pady=10)

        # Atualiza a interface para o idioma atual
        self.update_labels()
        self.entradas_editaveis = True

    def start_saldo_update_thread(self):
        thread = threading.Thread(target=self.update_saldo, daemon=True)
        thread.start()

    def update_saldo(self):
        while not self.stop_thread:
            self.saldo_value = self.obter_saldo('USDT')
            self.saldo_label.configure(text=f"Saldo: U$ {self.saldo_value}")
            time.sleep(3)

    def obter_saldo(self,ccy=None):
        return self.okx_client.get_balance(ccy)
    

    def salvar_valores(self):
        if self.entradas_editaveis:
            # Captura os valores dos campos de entrada
            self.valor_salvo1 = self.entry1.get()
            self.valor_salvo2 = self.entry2.get()
            self.valor_salvo3 = self.entry3.get()

            # Tornar os campos de entrada não editáveis
            self.entry1.configure(state='disabled')
            self.entry2.configure(state='disabled')
            self.entry3.configure(state='disabled')

            # Atualiza o texto do botão para "Editar"
            self.botao_salvar.configure(text="Editar")

            # Atualizar o status na interface, se desejar
            self.status_label.configure(text="Valores salvos e campos bloqueados!")
        else:
            # Tornar os campos de entrada editáveis novamente
            self.entry1.configure(state='normal')
            self.entry2.configure(state='normal')
            self.entry3.configure(state='normal')

            # Atualiza o texto do botão para "Salvar"
            self.botao_salvar.configure(text="Salvar")

            # Atualizar o status na interface, se desejar
            self.status_label.configure(text="Campos desbloqueados para edição!")

    def configurar_okx_api(self):
        self.janela_config = ctk.CTkToplevel(self)
        self.janela_config.title(self.languages[self.current_language]["config_title"])
        self.janela_config.geometry("400x300")

        self.entries = {}

        # Carregar configurações existentes
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

        salvar_botao = ctk.CTkButton(self.janela_config, text=self.languages[self.current_language]["save"], command=self.salvar_config)
        salvar_botao.pack(pady=10)

    def update_status_indicator(self):
        if self.webhook_status:
            self.status_label.configure(text=self.languages[self.current_language]["status_on"])
        else:
            self.status_label.configure(text=self.languages[self.current_language]["status_off"])

    def salvar_config(self):
        try:
            for entry_key, entry in self.entries.items():
                section, key = entry_key.split('-')
                self.config_loader.config.set(section, key, entry.get())

            with open(self.config_loader.config_file, 'w') as configfile:
                self.config_loader.config.write(configfile)

            messagebox.showinfo(self.languages[self.current_language]["success"], self.languages[self.current_language]["save_success"])
            self.janela_config.destroy()
        except Exception as e:
            messagebox.showerror(self.languages[self.current_language]["error"], f"{self.languages[self.current_language]['save_error']} {e}")

    def ativa_ngrok(self):
        ngrok=NgrokLinkGenerator()
        link=ngrok.generate_link()
        return  link

    def ativar_webhook(self):
        print("\nAtivando Webhook...")
        self.botao_ativar_webhook.configure(state=tk.DISABLED)
        self.botao_desativar_webhook.configure(state=tk.NORMAL)
        self.update_status_indicator()
        self.webhook_handler = WebhookHandler(self.valor_salvo3)
        self.webhook_handler.run()
        self.unit_size=float(0.01)*float(self.saldo_value)
        self.market=Market(size=self.unit_size)
        self.condition_handler=conditionHandler(self.valor_salvo1)
        self.operation=OperationHandler(self.webhook_handler.webhook_data_manager,self.market,self.condition_handler)
        self.operation.start()
        self.webhook_status = True
        self.update_status_indicator()

    def desativar_webhook(self):
        self.botao_ativar_webhook.configure(state=tk.NORMAL)
        self.botao_desativar_webhook.configure(state=tk.DISABLED)
        self.webhook_handler.stop()
        self.operation.stop()
        self.webhook_status = False
        self.update_status_indicator()
        print("\n\nWebhook desativado\n\n======================================")

    def ativar_webhook_thread(self):
        threading.Thread(target=self.ativar_webhook).start()

    def desativar_webhook_thread(self):
        threading.Thread(target=self.desativar_webhook).start()

    def on_closing(self):
        if self.webhook_status:
            self.desativar_webhook()
        self.destroy()
        sys.exit()

    def change_language(self, lang_code):
        self.current_language = lang_code
        self.update_labels()

    def update_labels(self):
        self.label_titulo.configure(text=self.languages[self.current_language]["title"])
        self.label_autor.configure(text=self.languages[self.current_language]["author"])
        self.botao_configurar_api.configure(text=self.languages[self.current_language]["config_api"])
        self.botao_ativar_webhook.configure(text=self.languages[self.current_language]["activate_webhook"])
        self.botao_desativar_webhook.configure(text=self.languages[self.current_language]["deactivate_webhook"])
        self.status_label.configure(text=self.languages[self.current_language]["webhook_status"])

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
