import flet as ft
import threading
import sqlite3
import bcrypt
import queue
import datetime
import threading
import asyncio
import sqlite3
from collections import deque

from models import Oficina, Peca, Cliente, Usuario, Carro
from database import (
    criar_conexao,
    criar_usuario_admin,
    buscar_usuario_por_nome,
    nome_banco_de_dados,
    fila_db,
)
from utils import mostrar_alerta, fechar_modal
from auth import autenticar_usuario


# versao1.0
class OficinaApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.clientes_dropdown = ft.Dropdown(
            width=200,
            hint_text="Selecione o Cliente",
        )
        self.carregar_clientes_dropdown()

        self.clientes_dropdown = []
        self.oficina = Oficina()
        self.usuario_atual = None
        self.cliente_selecionado = None
        self.pecas_no_servico = []
        self.evento_clientes_carregados = threading.Event()
        page.pubsub.subscribe(self._on_message)

        self.page.pubsub.subscribe(self._on_message)
        threading.Thread(target=processar_fila_db, args=(self,), daemon=True).start()

    def iniciar_thread_db(self):
        threading.Thread(target=processar_fila_db, args=(self,)).start()

    def atualizar_estado_botoes(self):
        """Atualiza o estado dos botões com base no login."""
        logado = bool(self.usuario_atual)  # True se usuario_atual não for None

        # Habilita/desabilita botões (exceto "login" e "sair")
        for nome_botao, botao in self.botoes.items():
            if nome_botao not in ("login", "sair"):
                botao.disabled = not logado

        # Controle do botão de login
        self.botoes["login"].disabled = logado

        # Atualiza a view para refletir as mudanças
        self.view.update()

    def abrir_modal_login(self, e):
        self.dlg_login = ft.AlertDialog(
            modal=True,
            title=ft.Text("Login do Usuario"),
            content=ft.Column(
                [
                    ft.TextField(label="Digite seu Nome", ref=ft.Ref[str]()),
                    ft.TextField(label="Digite sua Senha", ref=ft.Ref[str]()),
                    ft.Row(
                        [
                            ft.ElevatedButton("Entrar", on_click=self.fazer_login),
                            ft.TextButton("Cadastrar", on_click=self.abrir_cadastro),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    ),
                ]
            ),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = self.dlg_login
        self.dlg_login.open = True
        self.page.update()

    def fazer_login(self, e):
        dlg = self.page.dialog
        nome = dlg.content.controls[0].value
        senha = dlg.content.controls[1].value

        try:
            fila_db.put(("fazer_login", (nome, senha)))
            self.mostrar_alerta("Processando...")
        except Exception as e:
            self.mostrar_alerta(f"Erro ao processar : {e}")

    def _on_message(self, e):
        """
        Recebe mensagens da thread do banco de dados através do pubsub.
        As mensagens devem ser dicionários com a chave 'topic' para indicar o tipo de mensagem.
        """
        if e["topic"] == "login_bem_sucedido":
            usuario = e["usuario"]
            self.usuario_atual = usuario
            self.fechar_modal(None)
            self.atualizar_estado_botoes()
            self.page.snack_bar = ft.SnackBar(ft.Text("Login realizado com sucesso!"))
            self.page.snack_bar.open = True

        elif e["topic"] == "login_falhou":
            mensagem_erro = e["mensagem_erro"]
            self.mostrar_alerta(mensagem_erro)

        elif e["topic"] == "usuario_cadastrado":
            self.mostrar_alerta(e["mensagem_erro"])

        elif e["topic"] == "erro_cadastro_usuario":
            self.mostrar_alerta(e["mensagem_erro"])

        elif e["topic"] == "cliente_cadastrado":
            self.mostrar_alerta(e["mensagem_erro"])

        elif e["topic"] == "erro_cadastro_cliente":
            self.mostrar_alerta(e["mensagem_erro"])

        elif e["topic"] == "carro_cadastrado":
            self.mostrar_alerta(e["mensagem_erro"])

        elif e["topic"] == "erro_cadastro_carro":
            self.mostrar_alerta(e["mensagem_erro"])

        elif e["topic"] == "clientes_dropdown":
            # Atualizar o Dropdown do modal de cadastro de carro
            if self.page.dialog and self.page.dialog.title.value == "Cadastrar Carro":
                # Atualizar o Dropdown do modal de cadastro de carro
                self.clientes_dropdown = e["clientes"]
                self.evento_clientes_carregados.set()
        self.page.update()

    def abrir_cadastro(self, e):
        """Abre o modal para cadastro de novo usuário."""
        self.dlg_cadastro = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cadastro de Usuário"),
            content=ft.Column(
                [
                    ft.TextField(label="Nome de Usuário", ref=ft.Ref[str]()),
                    ft.TextField(label="Senha", password=True, ref=ft.Ref[str]()),
                    ft.TextField(
                        label="Confirmar Senha", password=True, ref=ft.Ref[str]()
                    ),
                ]
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self.fechar_modal),
                ft.ElevatedButton("Cadastrar", on_click=self.cadastrar_usuario),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = self.dlg_cadastro
        self.dlg_cadastro.open = True
        self.page.update()

    def cadastrar_usuario(self, e):
        dlg = self.page.dialog
        nome = dlg.content.controls[0].value
        senha = dlg.content.controls[1].value
        confirmar_senha = dlg.content.controls[2].value

        if senha != confirmar_senha:
            self.mostrar_alerta("As senhas não coincidem!")
            return

        try:
            fila_db.put(
                (
                    "cadastrar_usuario",
                    (nome, bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()),
                )
            )
            self.mostrar_alerta("Solicitação de cadastro enviada. Aguarde...")
            self.fechar_modal(e)
        except Exception as e:
            self.mostrar_alerta(f"Erro ao enviar solicitação de cadastro: {e}")

    def abrir_modal_cadastrar_cliente(self, e):
        self.cadastrar_cliente(e)

    def cadastrar_cliente(self, e):
        """Coleta dados do cliente e tenta cadastrá-lo."""

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cadastrar Cliente"),
            content=ft.Column(
                [
                    ft.TextField(label="Nome", ref=ft.Ref[str]()),
                    ft.TextField(label="Telefone", ref=ft.Ref[str]()),
                    ft.TextField(label="Endereço", ref=ft.Ref[str]()),
                    ft.TextField(label="Email", ref=ft.Ref[str]()),
                ]
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self.fechar_modal),
                ft.ElevatedButton("Salvar", on_click=self.salvar_cliente),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def salvar_cliente(self, e):
        """Salva os dados do novo cliente no banco de dados."""
        dlg = self.page.dialog
        nome = dlg.content.controls[0].value
        telefone = dlg.content.controls[1].value
        endereco = dlg.content.controls[2].value
        email = dlg.content.controls[3].value

        if self.oficina.cadastrar_cliente(nome, telefone, endereco, email):
            print("mostra a mesanagm")
            self.mostrar_alerta("Cliente cadastrado com sucesso!")

        else:
            cliente_existente = self.oficina.obter_cliente_por_nome(nome)
            if cliente_existente:
                self.dlg_confirmacao = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Cliente já cadastrado"),
                    content=ft.Text(
                        "Já existe um cliente com este nome. Deseja editar os dados?"
                    ),
                    actions=[
                        ft.TextButton("Não", on_click=self.fechar_modal),
                        ft.ElevatedButton("Sim", on_click=self.abrir_edicao_cliente),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                self.page.dialog = self.dlg_confirmacao
                self.dlg_confirmacao.open = True
            else:
                self.mostrar_alerta("Erro ao cadastrar o cliente!")
        self.page.update()

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
                        value=self.dlg_confirmacao.content.value,
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

    def abrir_modal_editar_cliente(self, e, cliente):
        """Abre o modal para editar os dados do cliente e seus carros."""
        self.cliente_selecionado = cliente
        self.fechar_modal(e)  # Fecha o modal de pesquisa

        # Crie as referências para os campos TextField
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

    def salvar_edicao_cliente(self, e):
        """Salva as edições do cliente no banco de dados."""
        if not self.cliente_selecionado:
            self.mostrar_alerta("Nenhum cliente selecionado para edição.")
            return

        # Obtém os valores dos campos de texto
        nome = self.campo_nome.value
        telefone = self.campo_telefone.value
        endereco = self.campo_endereco.value
        email = self.campo_email.value

        try:
            with sqlite3.connect(nome_banco_de_dados) as conexao:
                cursor = conexao.cursor()

                # Atualiza os dados do cliente no banco de dados
                cursor.execute(
                    "UPDATE clientes SET nome=?, telefone=?, endereco=?, email=? WHERE id=?",
                    (
                        nome,
                        telefone,
                        endereco,
                        email,
                        self.cliente_selecionado.id,
                    ),
                )
                conexao.commit()

            self.fechar_modal(e)
            self.page.update()
            self.mostrar_alerta("Cliente atualizado com sucesso!")

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

    # Abre o modal para cadastrar um novo carro.
    def abrir_modal_cadastrar_carro(self, e):
        """Abre o modal para cadastrar um novo carro."""
        if not self.clientes_dropdown:
            self.carregar_clientes_dropdown()
            self.evento_clientes_carregados.wait()
        self.cadastrar_carro(e)
            

    # Solicita a busca de clientes.
    def carregar_clientes_dropdown(self):
        """Solicita a busca de clientes."""
        try:
            fila_db.put(("obter_clientes_dropdown", None))
        except Exception as e:
            print(f"Erro ao solicitar clientes para o dropdown: {e}")

    # Define o cliente selecionado com base no Dropdown.
    def selecionar_cliente(self, e):
        """Define o cliente selecionado com base no Dropdown."""
        cliente_id = int(e.control.value.split("(ID: ")[1].split(")")[0])
        self.cliente_selecionado = cliente_id

        
    # Busca todos os clientes no banco de dados.
    def buscar_clientes(self):
        """Busca todos os clientes no banco de dados."""
        with sqlite3.connect(nome_banco_de_dados) as conexao:
            cursor = conexao.cursor()
            cursor.execute("SELECT id, nome FROM clientes")
            resultados = cursor.fetchall()
        return [
            ft.dropdown.Option(
                text=f"{nome} (ID: {id})",  # Use 'text' em vez de 'value'
                key=str(id),  # Use 'key' se precisar de uma chave única (opcional)
            )
            for id, nome in resultados
        ]

    def cadastrar_carro(self, e):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cadastrar Carro"),
            content=ft.Column(
                [
                    ft.TextField(label="Modelo", ref=ft.Ref[str]()),
                    ft.TextField(label="Ano", ref=ft.Ref[str]()),
                    ft.TextField(label="Cor", ref=ft.Ref[str]()),
                    ft.TextField(label="Placa", ref=ft.Ref[str]()),
                    ft.Dropdown(
                        width=200,
                        options=self.clientes_dropdown,  # Utilize a lista carregada
                        on_change=self.selecionar_cliente,  # Chame o método da classe
                        hint_text="Selecione o Cliente",
                    ),
                ]
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self.fechar_modal),
                ft.ElevatedButton(
                    "Salvar", on_click=self.salvar_carro
                ),  # Chame o método da classe
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg  # Atribui o diálogo à página
        dlg.open = True
        self.page.update()

    def salvar_carro(self, e, dlg, modelo, ano, cor, placa):
        """"Envia a solicitação de cadastro de carro para a thread do banco de dados."""
        dlg = self.page.dialog
        modelo = dlg.content.controls[0].value
        ano = (
            int(dlg.content.controls[1].value)
            if dlg.content.controls[1].value
            else None
        )
        cor = dlg.content.controls[2].value
        placa = dlg.content.controls[3].value
        cliente_id = self.cliente_selecionado

        if not all([modelo, ano, cor, placa, cliente_id]):
            self.mostrar_alerta("Por favor, preencha todos os campos.")
            return

        try:
            fila_db.put(("cadastrar_carro", (modelo, ano, cor, placa, cliente_id)))
            self.mostrar_alerta("Processando cadastro de carro. Aguarde...")
            dlg.content.controls[0].value = ""
            dlg.content.controls[1].value = ""
            dlg.content.controls[2].value = ""
            dlg.content.controls[3].value = ""
            dlg.content.controls[4].value = None
            self.fechar_modal(e)
        except Exception as e:
            self.mostrar_alerta(f"Erro ao processar cadastro de carro: {e}")

        self.page.update()

    def abrir_modal_pesquisar_carro(self, e):
        self.pesquisar_carro(e)

    def pesquisar_carro(self, e):
        self.mostrar_alerta("Pesquisa o carro em implementação")
        self.fechar_modal(e)
        self.page.update()

    def abrir_modal_editar_carro(self, e):
        self.editar_carro()

    def editar_carro(self, e):
        self.mostrar_alerta("Editar o carro em implementação")
        self.fechar_modal(e)
        self.page.update()

    def abrir_modal_registrar_servico(self, e):
        self.registrar_servico()

    def registrar_servico(self, e):
        self.mostrar_alerta("Registrar o serviço em implementação")
        self.fechar_modal(e)
        self.page.update()

    def abrir_modal_historico_servico(self, e):
        self.registrar_servico()

    def historico_servico(self, e):
        self.mostrar_alerta("Historico do serviço em implementação")
        self.fechar_modal(e)
        self.page.update()

    def abrir_modal_enviar_ordem_servico(self, e):
        self.enviar_ordem_servico()

    def enviar_ordem_servico(self, e):
        self.mostrar_alerta("Enviar Ordem do serviço em implementação")
        self.fechar_modal(e)
        self.page.update()

    def abrir_modal_gerar_pdf_ordem_servico(self, e):
        self.gerar_pdf_ordem_servico()

    def gerar_pdf_ordem_servico(self, e):
        self.mostrar_alerta("gerar_pdf_ordem_servico em implementação")
        self.fechar_modal(e)
        self.page.update()

    def abrir_modal_atualizar_estoque(self, e):
        self.gerar_pdf_ordem_servico()

    def atualizar_estoque(self, e):
        self.mostrar_alerta("atualizar_estoque em implementação")
        self.fechar_modal(e)
        self.page.update()

    def sair_do_app(self, e):
        self.page.window_destroy()

    def fechar_modal(self, e):
        """Fecha qualquer modal aberto."""
        self.page.dialog.open = False
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

    def build(self):

        threading.Thread(target=processar_fila_db, args=(self,)).start()
        self.botoes = {
            "login": ft.ElevatedButton("Efetue Login", on_click=self.abrir_modal_login),
            "cadastrar_cliente": ft.ElevatedButton(
                "Cadastrar Cliente",
                on_click=self.abrir_modal_cadastrar_cliente,
                disabled=True,
            ),
            
            "pesquisar_cliente": ft.ElevatedButton(
                "Pesquisar Cliente",
                on_click=self.abrir_modal_pesquisar_cliente,
                disabled=True,
            ),
            "cadastrar_carro": ft.ElevatedButton(
                "Cadastrar Carro",
                on_click=self.abrir_modal_cadastrar_carro,
                disabled=True,
            ),
            "pesquisar_carro": ft.ElevatedButton(
                "Pesquisar  Carro",
                on_click=self.abrir_modal_pesquisar_carro,
                disabled=True,
            ),
            "editar_carro": ft.ElevatedButton(
                "Editar Carro",
                on_click=self.abrir_modal_editar_carro,
                disabled=True,
            ),
            "registrar_servico": ft.ElevatedButton(
                "Registrar Serviço",
                on_click=self.abrir_modal_registrar_servico,
                disabled=True,
            ),
            "historico_servico": ft.ElevatedButton(
                "Histórico de Serviço",
                on_click=self.abrir_modal_historico_servico,
                disabled=True,
            ),
            "enviar_ordem_servico": ft.ElevatedButton(
                "Enviar Ordem de Serviço",
                on_click=self.abrir_modal_enviar_ordem_servico,
                disabled=True,
            ),
            "gerar_pdf_servico": ft.ElevatedButton(
                "Gerar PDF do Serviço",
                on_click=self.abrir_modal_gerar_pdf_ordem_servico,
                disabled=True,
            ),
            "atualizar_estoque": ft.ElevatedButton(
                "Atualizar Estoque", on_click=self.atualizar_estoque, disabled=True
            ),
            "sair": ft.ElevatedButton("Sair", on_click=self.sair_do_app),
        }

        self.view = ft.Column(
            [
                ft.Text("Bem-vindo à oficina Guarulhos!", size=30),  # Titulo
                *self.botoes.values(),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )

        self.page.add(self.view)

        return self.view


def processar_fila_db(app):
    """
    Processa as operações do banco de dados em uma thread separada.
    Envia mensagens para a thread principal usando pubsub com informações sobre o resultado das operações.
    """

    while True:
        conexao_db = None

        try:
            conexao_db = criar_conexao(nome_banco_de_dados)
            print(f"Conteúdo da fila antes de processar: {fila_db.queue}")
            operacao, dados = fila_db.get(block=True, timeout=1)
            if operacao == "cadastrar_usuario":
                nome, senha_hash = dados
                cursor = conexao_db.cursor()
                try:
                    cursor.execute(
                        "INSERT INTO usuarios (nome, senha) VALUES (?, ?)",
                        (nome, senha_hash),
                    )
                    conexao_db.commit()
                    app.page.pubsub.send_all(
                        {
                            "topic": "usuario_cadastrado",
                            "usuario": None,
                            "mensagem_erro": "Usuário cadastrado com sucesso!",
                        }
                    )
                except sqlite3.IntegrityError:
                    app.page.pubsub.send_all(
                        {
                            "topic": "erro_cadastro_usuario",
                            "mensagem_erro": "Nome de usuário já existe!",
                        }
                    )
                except Exception as e:
                    app.page.pubsub.send_all(
                        {"topic": "erro_cadastro_usuario", "mensagem_erro": str(e)}
                    )

            elif operacao == "fazer_login":
                nome, senha = dados
                cursor = conexao_db.cursor()
                cursor.execute("SELECT * FROM usuarios WHERE nome=?", (nome,))
                usuario_data = cursor.fetchone()

                if usuario_data:
                    senha_armazenada = usuario_data[2]
                    if bcrypt.checkpw(senha.encode(), senha_armazenada.encode()):
                        usuario = Usuario(usuario_data[1], usuario_data[2])
                        app.page.pubsub.send_all(
                            {"topic": "login_bem_sucedido", "usuario": usuario}
                        )
                    else:
                        app.page.pubsub.send_all(
                            {
                                "topic": "login_falhou",
                                "mensagem_erro": "Credenciais inválidas!",
                            }
                        )
                else:
                    # Tentar cadastrar o usuário se não existir
                    try:
                        senha_hash = bcrypt.hashpw(
                            senha.encode(), bcrypt.gensalt()
                        ).decode()
                        cursor.execute(
                            "INSERT INTO usuarios (nome, senha) VALUES (?, ?)",
                            (nome, senha_hash),
                        )
                        conexao_db.commit()
                        app.page.pubsub.send_all(
                            {
                                "topic": "usuario_cadastrado",
                                "mensagem_erro": f"Usuário '{nome}' cadastrado com sucesso! Faça o login.",
                            }
                        )
                    except Exception as e:
                        app.page.pubsub.send_all(
                            {
                                "topic": "login_falhou",
                                "mensagem_erro": f"Erro ao cadastrar usuário: {e}",
                            }
                        )

            elif operacao == "cadastrar_carro":
                modelo, ano, cor, placa, cliente_id = dados
                cursor = conexao_db.cursor()

                try:
                    cursor.execute(
                        "INSERT INTO carros (modelo, ano, cor, placa, cliente_id) VALUES (?, ?, ?, ?, ?)",
                        (modelo, ano, cor, placa, cliente_id),
                    )
                    conexao_db.commit()
                    app.page.pubsub.send_all(
                        {
                            "topic": "carro_cadastrado",
                            "mensagem_erro": "Carro cadastrado com sucesso!",
                        }
                    )

                except sqlite3.IntegrityError:
                    app.page.pubsub.send_all(
                        {
                            "topic": "erro_cadastro_carro",
                            "mensagem_erro": "Já existe um carro com essa placa.",
                        }
                    )

                except Exception as e:
                    app.page.pubsub.send_all(
                        {"topic": "erro_cadastro_carro", "mensagem_erro": str(e)}
                    )

            elif operacao == "obter_clientes_dropdown":

                try:
                    print("Teste obter_clientes_dropdown")
                    cursor = conexao_db.cursor()
                    cursor.execute("SELECT id, nome FROM clientes")
                    clientes = cursor.fetchall()
                    opcoes_dropdown = [
                        ft.dropdown.Option(f"{cliente[1]} (ID: {cliente[0]})")
                        for cliente in clientes
                    ]
                    app.page.pubsub.send_all(
                        {"topic": "clientes_dropdown", "clientes": opcoes_dropdown}
                    )
                    app.evento_clientes_carregados.set()
                except Exception as e:
                    print(f"Erro ao buscar clientes: {e}")

        except queue.Empty:
            pass
        except Exception as e:
            print(f"Erro ao processar operação da fila: {e}")
        finally:
            if conexao_db:
                conexao_db.close()
