import customtkinter as ctk
from tkinter import messagebox, Scrollbar

# Configuração inicial do CustomTkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class DynamicFormApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Dynamic Data Entry")
        self.geometry("600x400")

        # Lista para armazenar os dados dos conjuntos
        self.data_entries = []

        # Frame para organizar os conjuntos dinamicamente com rolagem
        self.canvas = ctk.CTkCanvas(self, height=300)
        self.scrollbar = Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ctk.CTkFrame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Botão de adicionar novo conjunto de dados
        self.add_button = ctk.CTkButton(self, text="Adicionar", command=self.add_new_data_set)
        self.add_button.pack(pady=10)

    def add_new_data_set(self):
        # Frame para o novo conjunto de dados
        data_set_frame = ctk.CTkFrame(self.scrollable_frame)
        data_set_frame.pack(pady=5, padx=5, fill="x")

        # Caixa de texto 1
        entry1 = ctk.CTkEntry(data_set_frame)
        entry1.pack(side="left", padx=5, pady=5, fill="x", expand=True)

        # Caixa de texto 2
        entry2 = ctk.CTkEntry(data_set_frame)
        entry2.pack(side="left", padx=5, pady=5, fill="x", expand=True)

        # Botão de salvar/editar para o conjunto de dados
        save_button = ctk.CTkButton(data_set_frame, text="Salvar", 
                                    command=lambda: self.toggle_edit(entry1, entry2, save_button))
        save_button.pack(side="right", padx=5, pady=5)

        # Botão de excluir para o conjunto de dados
        delete_button = ctk.CTkButton(data_set_frame, text="Excluir", 
                                      command=lambda: self.delete_data_set(data_set_frame))
        delete_button.pack(side="right", padx=5, pady=5)

        # Adiciona o novo conjunto ao array
        self.data_entries.append({"entry1": entry1, "entry2": entry2, "frame": data_set_frame})

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


# Execução da aplicação
if __name__ == "__main__":
    app = DynamicFormApp()
    app.mainloop()
