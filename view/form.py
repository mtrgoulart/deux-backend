import customtkinter as ctk
from tkinter import messagebox, Scrollbar

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
        # Frame para o novo conjunto de dados
        data_set_frame = ctk.CTkFrame(self.scrollable_frame)
        data_set_frame.pack(pady=5, padx=5, fill="x")

        # Lista de descrições para as entradas de dados
        descriptions = ["% Operações", "OP Simul", "Condicionantes", "Delay"]

        # Cria os campos de entrada de dados com suas descrições
        entries = {}
        for description in descriptions:
            label = ctk.CTkLabel(data_set_frame, text=description, width=80, height=30)
            label.pack(side="left", padx=5, pady=5)
            
            entry = ctk.CTkEntry(data_set_frame, width=80, height=30)
            entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)
            
            entries[description] = entry

        # Botão de salvar/editar para o conjunto de dados
        save_button = ctk.CTkButton(data_set_frame, text="Salvar", width=80, height=30,
                                    command=lambda: self.toggle_edit(entries, save_button))
        save_button.pack(side="right", padx=5, pady=5)

        # Botão de excluir para o conjunto de dados
        delete_button = ctk.CTkButton(data_set_frame, text="Excluir", width=80, height=30,
                                    command=lambda: self.delete_data_set(data_set_frame))
        delete_button.pack(side="right", padx=5, pady=5)

        # Adiciona o novo conjunto ao array
        self.data_entries.append({"entries": entries, "frame": data_set_frame})

    def toggle_edit(self, entry1, entry2, save_button):
        if entry1.cget("state") == "normal":
            # Desabilitar os campos de texto após salvar
            entry1.configure(state="disabled")
            entry2.configure(state="disabled")
            save_button.configure(text="Editar")

            # Exemplo de como você pode acessar os valores salvos
            value1 = entry1.get()
            value2 = entry2.get()
            messagebox.showinfo("Dados Salvos", f"Valores: {value1}, {value2}")
        else:
            # Habilitar os campos de texto para edição
            entry1.configure(state="normal")
            entry2.configure(state="normal")
            save_button.configure(text="Salvar")

    def delete_data_set(self, frame):
        # Remover o conjunto de dados
        frame.pack_forget()
        frame.destroy()
