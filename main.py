
import flet as ft
import threading


from services import OficinaApp, processar_fila_db





def main(page: ft.Page):
    page.Title = "Oficina Guarulhos Teste cadastro carro"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    app = OficinaApp(page)
    page.add(app.build())

    # Inscreva-se para receber mensagens da thread do banco de dados
    page.pubsub.subscribe(app._on_message)

    # Inicie a thread para processar a fila
    thread_db = threading.Thread(target=processar_fila_db, args=(page,), daemon=True)
    thread_db.start()

    page.update()


ft.app(target=main)