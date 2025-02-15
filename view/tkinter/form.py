import customtkinter as ctk
from PIL import Image
from tkinter import messagebox, Scrollbar
import os
from source.director import OperationManager
import re

# Configuração inicial do CustomTkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class ButtonManager:
    def __init__(self, entries, img_path, saved_data, app_instance, data_set_frame):
        self.entries = entries
        self.img_path = img_path
        self.saved_data = saved_data
        self.app_instance = app_instance
        self.data_set_frame = data_set_frame
        self.operation_running = False  # Estado da operação

        # Caminho para os ícones
        save_icon_path = os.path.join(self.img_path, "save_icon.png")
        edit_icon_path = os.path.join(self.img_path, "edit_icon.png")  # Ícone de edição
        delete_icon_path = os.path.join(self.img_path, "delete_icon.png")
        run_icon_path = os.path.join(self.img_path, "run_icon.png")
        stop_icon_path = os.path.join(self.img_path, "stop_icon.png")

        # Criação dos ícones
        self.save_icon = ctk.CTkImage(Image.open(save_icon_path), size=(20, 20))
        self.edit_icon = ctk.CTkImage(Image.open(edit_icon_path), size=(20, 20))
        delete_icon = ctk.CTkImage(Image.open(delete_icon_path), size=(20, 20))
        self.run_icon = ctk.CTkImage(Image.open(run_icon_path), size=(20, 20))
        self.stop_icon = ctk.CTkImage(Image.open(stop_icon_path), size=(20, 20))

        # Criação dos botões
        self.run_button = ctk.CTkButton(
            self.data_set_frame, image=self.run_icon, text="", width=40, height=30, 
            state="disabled", command=self.toggle_run_action
        )
        self.run_button.pack(side="right", padx=5, pady=5)

        self.save_button = ctk.CTkButton(self.data_set_frame, image=self.save_icon, text="Salvar", width=40, height=30,
                                         command=self.toggle_edit)
        self.save_button.pack(side="right", padx=5, pady=5)

        delete_button = ctk.CTkButton(self.data_set_frame, image=delete_icon, text="", width=40, height=30,
                                      command=self.delete_data_set)
        delete_button.pack(side="right", padx=5, pady=5)

    def toggle_run_action(self):
        if not self.operation_running:
            # Iniciar a operação
            self.start_operation()
            self.run_button.configure(image=self.stop_icon)
            self.operation_running = True
        else:
            # Parar a operação
            self.stop_operation()
            self.run_button.configure(image=self.run_icon)
            self.operation_running = False

    def toggle_edit(self):
        symbol = self.entries['symbol'].get()
        side = self.entries['side'].get()

        if symbol and side:
            if self.save_button.cget("text") == "Salvar":
                # Salvando os dados
                self.saved_data[f"{symbol}_{side}"] = {key: entry.get() for key, entry in self.entries.items()}
                print(f"Dados salvos!")

                # Habilitar o botão de execução após salvar
                self.run_button.configure(state="normal")

                # Alterar o texto e o ícone para "Editar"
                self.save_button.configure(text="Editar", image=self.edit_icon)
                self.disable_entries()

            else:
                # Desativar o botão de execução para edição
                self.run_button.configure(state="disabled")
                self.save_button.configure(text="Salvar", image=self.save_icon)
                self.enable_entries()
        else:
            print("Os campos 'symbol' e 'side' são obrigatórios para salvar.")

    def start_operation(self):
        symbol = self.entries['symbol'].get()
        side = self.entries['side'].get()
        try:
            key = f"{symbol}_{side}"
            if key not in self.saved_data:
                raise ValueError(f"Não existem dados salvos para o par {symbol} e {side}.")
            
            
            match = re.match(r"^([^-]+)-([^-]+)$", symbol)
            if not match:
                raise ValueError(f"O símbolo '{symbol}' não está no formato esperado 'parte1-parte2'.")
            
            part1, part2 = match.groups()
            
            # Define `ccy` com base no valor de `side`
            ccy = part2 if side == 'buy' else part1

            saved_entry = self.saved_data[key]
            percent = float(saved_entry.get('% Operações', 0.0))
            saldo = float(self.app_instance.obter_saldo(ccy) or 0.0)
            condition = int(saved_entry.get('Condicionantes', 1))
            interval = int(saved_entry.get('Delay', 5))

            self.operation_manager = OperationManager(
                percent=percent,
                avaiable_size=saldo,
                condition_limit=condition,
                interval=interval,
                symbol=symbol,
                side=side
            )
            self.operation_manager.start_operation()
            print("OperationManager inicializado com sucesso.")
        except Exception as e:
            print(f"Ocorreu um erro durante a execução de start_operation: {e}")
            raise

    def stop_operation(self):
        if hasattr(self, 'operation_manager'):
            self.operation_manager.stop_operation()  # Presumindo que existe um método para parar a operação
            print("OperationManager parado com sucesso.")
        else:
            print("Nenhuma operação está em execução para ser parada.")

    def run_action(self, symbol, side):
        try:
            key = f"{symbol}_{side}"
            if key not in self.saved_data:
                raise ValueError(f"Não existem dados salvos para o par {symbol} e {side}.")

            saved_entry = self.saved_data[key]
            symbol = saved_entry.get('symbol')
            percent = float(saved_entry.get('% Operações', 0.0))
            saldo = self.app_instance.obter_saldo('USDT')
            condition = int(saved_entry.get('Condicionantes', 1))
            interval = int(saved_entry.get('Delay', 5))
            side = saved_entry.get('side')

            if not symbol or not saldo:
                raise ValueError("As chaves 'URL', 'symbol' e 'saldo' são obrigatórias.")

            operation_manager = OperationManager(
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

    def delete_data_set(self):
        # Remover o conjunto de dados
        self.data_set_frame.pack_forget()
        self.data_set_frame.destroy()

    def disable_entries(self):
        for entry in self.entries.values():
            entry.configure(state="disabled")

    def enable_entries(self):
        for entry in self.entries.values():
            entry.configure(state="normal")


class DynamicForm(ctk.CTkFrame):
    def __init__(self, app_instance, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.saved_data = {}
        self.app_instance = app_instance
        self.data_entries = []

        # Estrutura da área de rolagem
        self.scroll_frame = ctk.CTkFrame(self)
        self.scroll_frame.pack(side="top", fill="both", expand=True)

        # Configuração do Canvas e Scrollbar
        self.canvas = ctk.CTkCanvas(self.scroll_frame)
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.scrollbar = Scrollbar(self.scroll_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y", padx=5)
        
        self.scrollable_frame = ctk.CTkFrame(self.canvas)
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configuração de rolagem no Canvas
        self.canvas.configure(yscrollcommand=self.scrollbar.set, width=1000)
        
        # Atualização da área de rolagem
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Eventos de rolagem do mouse para Windows e macOS
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)       # Windows
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)         # Linux Scroll Up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)         # Linux Scroll Down
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

        # Botão para adicionar novos conjuntos de dados
        self.add_button = ctk.CTkButton(self, text="Adicionar", command=self.add_new_data_set)
        self.add_button.pack(padx=10, pady=10)

    def _on_mousewheel(self, event):
        if event.num == 5 or event.delta < 0:  # Para Linux e scroll para baixo no Windows
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:  # Para Linux e scroll para cima no Windows
            self.canvas.yview_scroll(-1, "units")

    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(-1 * int(event.delta / 120), "units")

    # Funções para adicionar campos e entradas do conjunto de dados
    def add_new_data_set(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_path, "img")

        data_set_frame = ctk.CTkFrame(self.scrollable_frame)
        data_set_frame.pack(pady=5, padx=5, fill="x")

        field_rows = [["symbol", "side", "Condicionantes", "Delay"], ["% Operações", "TP", "SL", "OP Simul"]]
        entries = self.create_data_entries(data_set_frame, field_rows)

        ButtonManager(entries, img_path, self.saved_data, self.app_instance, data_set_frame)
        self.data_entries.append({"entries": entries, "frame": data_set_frame})

    def create_data_entries(self, data_set_frame, field_rows):
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