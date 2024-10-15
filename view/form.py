import customtkinter as ctk
from PIL import Image
from tkinter import messagebox, Scrollbar
import os

# Configuração inicial do CustomTkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class DynamicForm(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

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

        # Lista de descrições para os novos campos
        descriptions_row1 = ["symbol", "side", "TP", "SL"]

        # Frame para a primeira linha de campos (novos campos)
        row1_frame = ctk.CTkFrame(data_set_frame)
        row1_frame.pack(pady=5, padx=5, fill="x")

        # Cria os campos de entrada de dados da primeira linha (novos)
        entries = {}
        for description in descriptions_row1:
            label = ctk.CTkLabel(row1_frame, text=description)
            label.pack(side="left", padx=5, pady=5)
            
            entry = ctk.CTkEntry(row1_frame, width=80, height=30)
            entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)
            
            entries[description] = entry

        # Lista de descrições para os campos antigos
        descriptions_row2 = ["% Operações", "OP Simul", "Condicionantes", "Delay"]

        # Frame para a segunda linha de campos (antigos)
        row2_frame = ctk.CTkFrame(data_set_frame)
        row2_frame.pack(pady=5, padx=5, fill="x")

        # Cria os campos de entrada de dados da segunda linha (antigos)
        for description in descriptions_row2:
            label = ctk.CTkLabel(row2_frame, text=description)
            label.pack(side="left", padx=5, pady=5)
            
            entry = ctk.CTkEntry(row2_frame, width=80, height=30)
            entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)
            
            entries[description] = entry

        save_icon_path = os.path.join(img_path, "save_icon.png")
        delete_icon_path = os.path.join(img_path, "delete_icon.png")
        run_icon_path = os.path.join(img_path, "run_icon.png")
        
        save_icon = ctk.CTkImage(Image.open(save_icon_path), size=(20, 20))
        delete_icon = ctk.CTkImage(Image.open(delete_icon_path), size=(20, 20))
        run_icon = ctk.CTkImage(Image.open(run_icon_path), size=(20, 20))

        # Botão de execução com ícone, desabilitado inicialmente
        run_button = ctk.CTkButton(data_set_frame, image=run_icon, text="", width=40, height=30, state="disabled",
                                command=self.run_action)  # Implementar a função run_action
        run_button.pack(side="right", padx=5, pady=5)

        # Botão de salvar/editar com ícone
        save_button = ctk.CTkButton(data_set_frame, image=save_icon, text="", width=40, height=30,
                                    command=lambda: self.toggle_edit(entries, save_button,run_button))
        save_button.pack(side="right", padx=5, pady=5)

        # Botão de excluir com ícone
        delete_button = ctk.CTkButton(data_set_frame, image=delete_icon, text="", width=40, height=30,
                                    command=lambda: self.delete_data_set(data_set_frame))
        delete_button.pack(side="right", padx=5, pady=5)

        

        # Adiciona o novo conjunto ao array
        self.data_entries.append({"entries": entries, "frame": data_set_frame})

    def run_action(self):
        pass

    def toggle_edit(self, entries, save_button,run_button):
        run_button.configure(state="normal")
        # Defina os caminhos para os ícones de Salvar e Editar
        base_path = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(base_path, "img")
        
        save_icon_path = os.path.join(img_path, "save_icon.png")
        edit_icon_path = os.path.join(img_path, "edit_icon.png")

        save_icon = ctk.CTkImage(Image.open(save_icon_path), size=(20, 20))
        edit_icon = ctk.CTkImage(Image.open(edit_icon_path), size=(20, 20))

        # Pega o estado do primeiro campo de entrada (todos têm o mesmo estado)
        first_entry = next(iter(entries.values()))  # Pega a primeira entrada do dicionário
        if first_entry.cget("state") == "normal":
            # Desabilitar todos os campos de entrada após salvar
            for entry in entries.values():
                entry.configure(state="disabled")
            # Alterar para o ícone de Editar
            save_button.configure(image=edit_icon)

            # Exemplo de como acessar os valores salvos
            saved_values = {desc: entry.get() for desc, entry in entries.items()}
            messagebox.showinfo("Dados Salvos", f"Valores: {saved_values}")
        else:
            # Habilitar todos os campos de entrada para edição
            for entry in entries.values():
                entry.configure(state="normal")
            # Alterar para o ícone de Salvar
            save_button.configure(image=save_icon)

    def delete_data_set(self, frame):
        # Remover o conjunto de dados
        frame.pack_forget()
        frame.destroy()
