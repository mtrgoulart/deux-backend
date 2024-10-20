import customtkinter as ctk
from PIL import Image
from tkinter import messagebox, Scrollbar
import os
from source.director import OperationManager

# Configuração inicial do CustomTkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class DynamicForm(ctk.CTkFrame):
    def __init__(self, app_instance,master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.saved_data = {}
        self.app_instance=app_instance

        # Lista para armazenar os dados dos conjuntos
        self.data_entries = []

        self.scroll_frame = ctk.CTkFrame(self)
        self.scroll_frame.pack(side="top", fill="both", expand=True)

        # Canvas e Scrollbar dentro de um frame separado
        self.canvas = ctk.CTkCanvas(self.scroll_frame, height=400)
        self.scrollbar = Scrollbar(self.scroll_frame,orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ctk.CTkFrame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Captura o evento de rolagem do mouse
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Para sistemas com trackpads ou rolagem "horizontal"
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set,width=1000)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y",padx=5)

        # Botão de adicionar novo conjunto de dados
        self.add_button = ctk.CTkButton(self, text="Adicionar", command=self.add_new_data_set)
        self.add_button.pack(padx=10,pady=10)

    def _on_mousewheel(self, event):
        # Rola verticalmente
        self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    def _on_shift_mousewheel(self, event):
        # Rola horizontalmente (caso necessário)
        self.canvas.xview_scroll(-1 * int(event.delta / 120), "units")


    def add_new_data_set(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_path, "img")

        # Frame para o novo conjunto de dados
        data_set_frame = ctk.CTkFrame(self.scrollable_frame)
        data_set_frame.pack(pady=5, padx=5, fill="x")

        # Definindo os campos por linha
        field_rows = [
            ["URL"],  # Linha para o campo URL
            ["symbol", "side", "TP", "SL"],  # Linha de novos campos
            ["% Operações", "OP Simul", "Condicionantes", "Delay"]  # Linha de campos antigos
        ]

        # Criação dos campos de entrada de dados
        entries = self.create_data_entries(data_set_frame, field_rows)

        # Criação dos botões (Salvar, Excluir e Executar)
        self.create_buttons(data_set_frame, entries, img_path)

        # Adiciona o novo conjunto ao array
        self.data_entries.append({"entries": entries, "frame": data_set_frame})

    def create_data_entries(self, data_set_frame, field_rows):
        # Dicionário para armazenar as entradas
        entries = {}

        for row_fields in field_rows:
            row_frame = ctk.CTkFrame(data_set_frame)
            row_frame.pack(pady=5, padx=5, fill="x")

            for field in row_fields:
                label = ctk.CTkLabel(row_frame, text=field)
                label.pack(side="left", padx=5, pady=5)

                entry = ctk.CTkEntry(row_frame, width=80, height=30)
                entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)

                entries[field] = entry

        return entries
    

    def create_buttons(self, data_set_frame, entries, img_path):
        # Caminho para os ícones
        save_icon_path = os.path.join(img_path, "save_icon.png")
        edit_icon_path = os.path.join(img_path, "edit_icon.png")  # Ícone de edição
        delete_icon_path = os.path.join(img_path, "delete_icon.png")
        run_icon_path = os.path.join(img_path, "run_icon.png")

        # Criação dos ícones
        self.save_icon = ctk.CTkImage(Image.open(save_icon_path), size=(20, 20))
        self.edit_icon = ctk.CTkImage(Image.open(edit_icon_path), size=(20, 20))  # Ícone de edição
        delete_icon = ctk.CTkImage(Image.open(delete_icon_path), size=(20, 20))
        run_icon = ctk.CTkImage(Image.open(run_icon_path), size=(20, 20))

        # Botão de execução com ícone, desabilitado inicialmente
        run_button = ctk.CTkButton(data_set_frame, image=run_icon, text="", width=40, height=30, state="disabled")
        run_button.pack(side="right", padx=5, pady=5)

        # Botão de salvar/editar com ícone de salvar inicialmente
        save_button = ctk.CTkButton(data_set_frame, image=self.save_icon, text="Salvar", width=40, height=30,
                                    command=lambda: self.toggle_edit(entries, save_button, run_button))
        save_button.pack(side="right", padx=5, pady=5)

        # Botão de excluir com ícone
        delete_button = ctk.CTkButton(data_set_frame, image=delete_icon, text="", width=40, height=30,
                                    command=lambda: self.delete_data_set(data_set_frame))
        delete_button.pack(side="right", padx=5, pady=5)

    def run_action(self, symbol, side):
        try:
            # Construir a chave de self.saved_data com base em symbol e side
            key = f"{symbol}_{side}"

            # Verificar se os dados para esse símbolo e lado existem
            if key not in self.saved_data:
                raise ValueError(f"Não existem dados salvos para o par {symbol} e {side}.")

            # Obter os dados salvos
            saved_entry = self.saved_data[key]

            # Validação e extração de entradas do dicionário, com fallback para valores padrão
            url = saved_entry.get('URL')
            symbol= saved_entry.get('symbol')
            percent = float(saved_entry.get('% Operações', 0.0))
            saldo = self.app_instance.obter_saldo('USDT')
            condition = int(saved_entry.get('Condicionantes', 1))
            interval = int(saved_entry.get('Delay', 5))  # Intervalo padrão de 5 segundos
            side = saved_entry.get('side')


            # Validação de entradas obrigatórias
            if not url or not symbol or not saldo:
                raise ValueError("As chaves 'URL', 'symbol' e 'saldo' são obrigatórias.")

            # Logging de informações
            print(f"\n =========================\n Executando run_action com os valores: {url=}, {percent=}, {saldo=}, {condition=}, {interval=}, {symbol=}")

            # Passando os valores extraídos para a classe OperationManager
            operation_manager = OperationManager(
                webhook_url=url,
                percent=percent,
                avaiable_size=saldo,
                condition_limit=condition,
                interval=interval,
                symbol=symbol,
                side=side
            )
            operation_manager.start_operation()
            print("OperationManager inicializado com sucesso.")

        except Exception as e:
            print(f"Ocorreu um erro durante a execução de run_action: {e}")
            raise

    def toggle_edit(self, entries, save_button, run_button):
        # Coleta os valores de symbol e side
        symbol = entries['symbol'].get()
        side = entries['side'].get()

        if symbol and side:
            # Verificar se estamos no modo de edição ou salvamento
            if save_button.cget("text") == "Salvar":
                # Salvando os dados, então o botão run_button deve ser habilitado
                self.saved_data[f"{symbol}_{side}"] = {
                    key: entry.get() for key, entry in entries.items()
                }
                print(f"Dados salvos!")  # Para visualização

                # Habilitar o botão de execução após salvar os dados
                run_button.configure(state="normal", command=lambda: self.run_action(symbol, side))

                # Alterar o texto do botão para "Editar" e trocar o ícone para editar
                save_button.configure(text="Editar", image=self.edit_icon)
                
                # Desabilitar os campos de entrada
                self.disable_entries(entries)

            else:
                # Estamos em modo de edição, então o botão run_button deve ser desativado
                run_button.configure(state="disabled")

                # Alterar o texto do botão para "Salvar" e trocar o ícone para salvar
                save_button.configure(text="Salvar", image=self.save_icon)

                # Habilitar os campos de entrada
                self.enable_entries(entries)
        else:
            print("Os campos 'symbol' e 'side' são obrigatórios para salvar.")

    def disable_entries(self, entries):
        for entry in entries.values():
            entry.configure(state="disabled")

    def enable_entries(self, entries):
        for entry in entries.values():
            entry.configure(state="normal")


    def delete_data_set(self, frame):
        # Remover o conjunto de dados
        frame.pack_forget()
        frame.destroy()
