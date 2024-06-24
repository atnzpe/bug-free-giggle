
import flet as ft #inclui
import threading
from flet import Dropdown, dropdown  # Importa Dropdown e dropdown

from oficina_app import OficinaApp, processar_fila_db
from utils import criar_pastas


def main(page: ft.Page):
    page.Title = "Oficina Guarulhos Teste cadastro carro"
    page.theme_mode = ft.ThemeMode.DARK
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    app = OficinaApp(page)
    
    page.add(app.build())

    # Inscreva-se para receber mensagens da thread do banco de dados
    page.pubsub.subscribe(app._on_message)

    # Criar as pastas necessárias
    criar_pastas("./big/")
    
    # Inicie a thread para processar a fila
    thread_db = threading.Thread(target=processar_fila_db, args=(page,), daemon=True)
    thread_db.start()

    page.update()


ft.app(target=main)