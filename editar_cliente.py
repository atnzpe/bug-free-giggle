# editar_cliente.py

from typing import Any
from flet import Dropdown, dropdown  # Importa Dropdown e dropdown
import flet as ft
from flet import (
    Column,
    Container,
    ElevatedButton,
    Page,
    Row,
    Text,
    TextField,
    UserControl,
    colors,
    ListView,
)
import urllib.parse
import os
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import threading
import sqlite3

# ... (Outras importações) ...

from models import Oficina, Peca, Carro, Cliente, Usuario

from database import (
    criar_conexao,
    criar_usuario_admin,
    obter_carros_por_cliente,
    criar_conexao,
    obter_clientes,
    obter_carros_por_cliente,
    obter_pecas,
    inserir_ordem_servico,
    atualizar_estoque_peca,
    quantidade_em_estoque_suficiente,
    inserir_movimentacao_peca,
    nome_banco_de_dados,
    fila_db,
    atualizar_carro,
)


class EditarCliente(UserControl):
    """
    Classe criada poara editar cliente
    """

    def __init__(self, page, oficina_app):
        super().__init__()
        self.page = page
        self.oficina_app = oficina_app
        self.oficina = Oficina()
        # self.page.pubsub.subscribe(self.oficina._on_message)
        # Inicializa os atributos no construtor
        self.clientes_dropdown = ft.Dropdown(width=150)
        self.evento_clientes_carregados = threading.Event()

        self.conexao = criar_conexao(nome_banco_de_dados)
        self.carregar_clientes_no_dropdown(self)
        try:
            with criar_conexao(nome_banco_de_dados) as conexao:
                cursor = conexao.cursor()
                cursor.execute("SELECT id, nome FROM clientes")
                clientes = cursor.fetchall()

                self.clientes_dropdown.options = [
                    ft.dropdown.Option(f"{cliente[1]} (ID: {cliente[0]})")
                    for cliente in clientes
                ]

                self.evento_clientes_carregados.set()
                self.page.update()
        except Exception as e:
            print(f"Erro ao carregar clientes no dropdown: {e}")
        # Carregue os dados primeiro

        self.clientes_dropdown = []

    def build(self):
        # ... outros controles ...
        botao_pesquisar = ft.ElevatedButton(
            "Pesquisar Cliente", on_click=self.abrir_modal_pesquisar_cliente
        )

    # ==================
    # UTILIDADES
    # ==================

    def fechar_modal(self, e):
        """Fecha qualquer modal aberto."""
        print(self.page.dialog)  # Adicione este print para debugar
        if self.page.dialog:  # Verifica se o diálogo existe
            self.page.update()

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

    # Abre o modal de pesquisa e prepara para exibir os resultados.
    def abrir_modal_pesquisar_cliente(self, e):
        self.pesquisar_cliente(e)

    def pesquisar_cliente(self, e):
        """Abre o modal de pesquisa e prepara para exibir os resultados."""

        self.dlg_pesquisa = ft.AlertDialog(
            modal=True,
            title=ft.Text("Pesquisar Cliente para Edição"),
            content=ft.Column(
                [
                    ft.TextField(
                        label="Termo de Pesquisa",
                        ref=ft.Ref[str](),
                        on_submit=self.realizar_pesquisa_cliente,
                    ),
                    ft.Column(ref=ft.Ref[ft.Column](), scroll=ft.ScrollMode.AUTO),
                ]
            ),
            actions=[
                ft.TextButton("Fechar", on_click=self.fechar_modal),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = self.dlg_pesquisa
        self.dlg_pesquisa.open = True
        self.page.update()

    # Realiza a pesquisa do cliente no banco de dados e exibe os resultados.
    def realizar_pesquisa_cliente(self, e):
        """Realiza a pesquisa do cliente no banco de dados e exibe os resultados."""
        termo_pesquisa = self.page.dialog.content.controls[0].value

        # Utiliza a função obter_clientes_por_termo (você precisa implementá-la)
        clientes_encontrados = self.obter_clientes_por_termo(termo_pesquisa)

        resultados_view = self.page.dialog.content.controls[1]
        resultados_view.controls.clear()

        if clientes_encontrados:
            for cliente in clientes_encontrados:
                resultados_view.controls.append(
                    ft.ListTile(
                        title=ft.Text(cliente.nome),
                        subtitle=ft.Text(
                            f"Telefone: {cliente.telefone}, Email: {cliente.email}"
                        ),
                        on_click=lambda e, c=cliente: self.abrir_modal_editar_cliente(
                            e, c
                        ),
                    )
                )
        else:
            resultados_view.controls.append(ft.Text("Nenhum cliente encontrado."))

        self.page.update()

    # Função para buscar clientes no banco de dados por nome, telefone ou placa.
    def obter_clientes_por_termo(self, termo):
        """
        Função para buscar clientes no banco de dados por nome, telefone ou placa.

        Args:
            termo (str): O termo a ser pesquisado.

        Returns:
            list: Uma lista de objetos Cliente que correspondem à pesquisa.
        """
        with sqlite3.connect(nome_banco_de_dados) as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                """
                SELECT DISTINCT c.id, c.nome, c.telefone, c.endereco, c.email
                FROM clientes c
                LEFT JOIN carros car ON c.id = car.cliente_id
                WHERE
                    c.nome LIKE ?
                    OR c.telefone LIKE ?
                    OR car.placa LIKE ?
                """,
                (f"%{termo}%", f"%{termo}%", f"%{termo}%"),
            )
            resultados = cursor.fetchall()

        clientes = []
        for resultado in resultados:
            cliente = Cliente(*resultado)  # Assuming Cliente class is defined
            clientes.append(cliente)
        return clientes

    # Função para buscar carros de um cliente específico pelo ID.
    def obter_carros_por_cliente_id(self, cliente_id):
        """
        Função para buscar carros de um cliente específico pelo ID.
        """
        with sqlite3.connect(nome_banco_de_dados) as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                """
                SELECT modelo, ano, cor, placa
                FROM carros
                WHERE cliente_id = ?
                """,
                (cliente_id,),
            )
            resultados = cursor.fetchall()
        return resultados  # Retorna uma lista de tuplas (modelo, ano, cor, placa)

    def abrir_edicao_cliente(self, e):
        """Abre um modal para editar os dados do cliente."""
        self.fechar_modal(e)  # Fecha o diálogo de confirmação

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar Cliente"),
            content=ft.Column(
                [
                    ft.TextField(
                        label="Nome",
                        value=self.cliente_selecionado.content.value,
                        read_only=True,
                    ),
                    ft.TextField(label="Telefone", ref=ft.Ref[str]()),
                    ft.TextField(label="Email", ref=ft.Ref[str]()),
                ]
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self.fechar_modal),
                ft.ElevatedButton("Salvar", on_click=self.confirmar_edicao_cliente),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # Abre o modal de pesquisa e prepara para exibir os resultados.

    # Abre o modal para editar os dados do cliente e seus carros.
    

    def carregar_clientes_no_dropdown(self,e):
        """Carrega os clientes no Dropdown."""
        try:
            with self.conexao as conexao:
                cursor = conexao.cursor()
                cursor.execute("SELECT id, nome FROM clientes")
                clientes = cursor.fetchall()

                self.clientes_dropdown.options = [
                    ft.dropdown.Option(f"{cliente[1]} (ID: {cliente[0]})")
                    for cliente in clientes
                ]
                self.page.update()  # Atualiza a página após carregar as opções
        except Exception as e:
            print(f"Erro ao carregar clientes no dropdown: {e}")

        # ... (Resto do seu código) ...

        
        self.fechar_modal(e)  # Fecha o modal de pesquisa

        # Crie as referências para os campos TextField
        

    def abrir_modal_editar_cliente(self, e, cliente):
        """Abre o modal para editar os dados do cliente e seus carros."""
        # Crie o Dropdown de clientes
        # Movendo carregar_clientes_no_dropdown para dentro da classe EditarCliente
        self.cliente_selecionado = cliente

        # 1. Carregar o dropdown de clientes
        #self.carregar_clientes_no_dropdown()
        
        self.campo_nome = ft.TextField(label="Nome", value=cliente.nome)
        self.campo_telefone = ft.TextField(label="Telefone", value=cliente.telefone)
        self.campo_endereco = ft.TextField(label="Endereço", value=cliente.endereco)
        self.campo_email = ft.TextField(label="Email", value=cliente.email)

        # Carrega os carros associados ao cliente (implemente a função carregar_carros_cliente)
        carros_cliente = self.carregar_carros_cliente(cliente.id)
        self.carros_dropdown = ft.Dropdown(
            width=200,
            options=(
                [
                    ft.dropdown.Option(f"Placa: {carro.placa}, Modelo: {carro.modelo}")
                    for carro in carros_cliente
                ]
                if carros_cliente
                else [ft.dropdown.Option("Nenhum carro encontrado")]
            ),
            hint_text="Carros do Cliente",
        )

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar Cliente"),
            content=ft.Column(
                [
                    self.campo_nome,
                    self.campo_telefone,
                    self.campo_endereco,
                    self.campo_email,
                    self.carros_dropdown,
                ]
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self.fechar_modal),
                ft.ElevatedButton("Salvar", on_click=self.salvar_edicao_cliente),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        # ... (Resto do seu código) ...
        # Adicione o Dropdown ao conteúdo do modal
        dlg.content.controls.append(self.clientes_dropdown)

        self.page.dialog = dlg
        dlg.open = True
        self.page.update()
        
    # Função para carregar os carros associados a um cliente do banco de dados.
    def carregar_carros_cliente(self, cliente_id):
        """
        Função para carregar os carros associados a um cliente do banco de dados.
        """
        with sqlite3.connect(nome_banco_de_dados) as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                """
                SELECT id, modelo, ano, cor, placa  -- Inclua 'id' aqui
                FROM carros
                WHERE cliente_id = ?
                """,
                (cliente_id,),
            )
            carros_data = cursor.fetchall()

        # Assuming you have a Carro class to represent car objects
        carros = []
        for carro_data in carros_data:
            carro = Carro(*carro_data)
            carros.append(carro)
        return carros

    # Salva as edições do cliente no banco de dados.
    def salvar_edicao_cliente(self, e):
        """Salva as edições do cliente no banco de dados."""

        # Obtenha o ID do novo dono do carro a partir do Dropdown
        novo_dono_id = None
        if self.clientes_dropdown.value:
            novo_dono_id = int(self.clientes_dropdown.value.split(" (ID: ")[1][:-1])

        if not self.cliente_selecionado:
            self.mostrar_alerta("Nenhum cliente selecionado para edição.")
            return

        # Obtém os valores dos campos de texto
        nome = self.campo_nome.value
        telefone = self.campo_telefone.value
        endereco = self.campo_endereco.value
        email = self.campo_email.value

        try:
            if self.oficina_app.oficina.atualizar_cliente(
                self.cliente_selecionado.id, nome, telefone, email
            ):
                self.fechar_modal(e)
                self.page.update()
                self.mostrar_alerta("Cliente atualizado com sucesso!")
            else:
                self.mostrar_alerta("Erro ao atualizar os dados do cliente!")

        except sqlite3.IntegrityError as e:
            print(f"Erro de integridade do banco de dados: {e}")
            self.mostrar_alerta(
                f"Erro ao atualizar cliente: Verifique se os dados são válidos. Detalhes: {e}"
            )

        except sqlite3.OperationalError as e:
            print(f"Erro operacional do banco de dados: {e}")
            self.mostrar_alerta(f"Erro ao conectar ao banco de dados. Detalhes: {e}")

        except Exception as e:  # Captura exceções gerais apenas como último recurso
            print(f"Erro inesperado: {e}")
            self.mostrar_alerta(f"Ocorreu um erro inesperado. Detalhes: {e}")

        self.page.update()

    def confirmar_edicao_cliente(self, e):
        """Confirma a edição dos dados do cliente."""
        dlg = self.page.dialog
        nome = dlg.content.controls[0].value
        telefone = dlg.content.controls[1].value
        email = dlg.content.controls[2].value

        if self.oficina.atualizar_cliente(nome, telefone, email):
            self.mostrar_alerta("Dados do cliente atualizados com sucesso!")
            self.fechar_modal(e)
        else:
            self.mostrar_alerta("Erro ao atualizar os dados do cliente!")

        self.page.update()
