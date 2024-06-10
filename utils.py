import flet as ft


#Implementar em Breve

def mostrar_alerta(self, mensagem):
    """Exibe um alerta em um Modal (AlertDialog)."""
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("ATENÇÃO"),
        content=ft.Text(mensagem),
        actions=[
            # usa a mesma função fechar_modal
            ft.TextButton("OK", on_click=self.fechar_modal)
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    self.page.dialog = dlg  # Atribui o diálogo diretamente
    dlg.open = True
    self.page.update()


def fechar_modal(self, e):
    """Fecha qualquer modal aberto."""
    self.page.dialog.open = False
    self.page.update()


# versao1.0