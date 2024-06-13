from typing import Any

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
)
import threading
import sqlite3
import bcrypt
import queue
from datetime import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


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
    nome_banco_de_dados,
    fila_db,
)


class OrdemServicoFormulario(UserControl):
    """Formulário para criar uma nova ordem de serviço."""

    def __init__(self, page, oficina_app):
        super().__init__()
        self.page = page
        self.oficina_app = oficina_app

        self.cliente_dropdown = Dropdown(
            width=300,
            options=[
                dropdown.Option(f"{cliente[1]} (ID: {cliente[0]})")
                for cliente in self.oficina_app.clientes
            ],
            on_change=self.cliente_alterado,
        )
        self.carro_dropdown = Dropdown(width=300)
        self.peca_dropdown = Dropdown(
            width=200,
            options=[dropdown.Option(f"{peca[1]}") for peca in self.oficina_app.pecas],
        )
        self.preco_unitario_field = TextField(
            label="Preço Unitário",
            width=100,
            value="0.00",
            disabled=True,  # Desabilitado inicialmente
        )
        self.quantidade_field = TextField(label="Quantidade", width=100, value="1")
        self.adicionar_peca_button = ElevatedButton(
            "Adicionar Peça", on_click=self.adicionar_peca
        )
        self.pecas_list_view = ListView(expand=True, height=200)
        self.valor_total_text = Text("Valor Total: R$ 0.00")

    def build(self):
        return Column(
            [
                Row(
                    [
                        Text("Cliente:", width=100),
                        self.cliente_dropdown,
                    ],
                ),
                Row(
                    [
                        Text("Carro:", width=100),
                        self.carro_dropdown,
                    ],
                ),
                Row(
                    [
                        Text("Peça:", width=100),
                        self.peca_dropdown,
                        self.quantidade_field,
                        self.adicionar_peca_button,
                    ],
                ),
                self.pecas_list_view,
                self.valor_total_text,
            ]
        )

    def cliente_alterado(self, e):
        self.carro_dropdown.options = []
        cliente_selecionado = self.cliente_dropdown.value
        if cliente_selecionado:
            cliente_id = int(cliente_selecionado.split(" (ID: ")[1][:-1])
            with criar_conexao(nome_banco_de_dados) as conexao:
                carros = obter_carros_por_cliente(conexao, cliente_id)
                self.carro_dropdown.options = [
                    ft.dropdown.Option(f"{carro[1]} (ID: {carro[0]})")
                    for carro in carros
                ]
        self.carro_dropdown.value = None
        self.page.update()

    def adicionar_peca(self, e):
        peca_nome = self.peca_dropdown.value
        quantidade = float(self.quantidade_field.value)

        # Obter o preço unitário da peça selecionada
        preco_unitario = next(
            (peca[5] for peca in self.oficina_app.pecas if peca[1] == peca_nome),
            0.00,
        )  # Retorna 0.00 se a peça não for encontrada

        valor_total = preco_unitario * quantidade
        self.oficina_app.pecas_selecionadas.append(
            {
                "nome": peca_nome,
                "preco_unitario": preco_unitario,
                "quantidade": quantidade,
                "valor_total": valor_total,
            }
        )
        self.atualizar_lista_pecas()
        self.calcular_valor_total()

    def atualizar_lista_pecas(self):
        self.pecas_list_view.controls = []
        for peca in self.oficina_app.pecas_selecionadas:
            self.pecas_list_view.controls.append(
                ft.Text(
                    f"{peca['nome']} - Preço Unitário: R$ {peca['preco_unitario']:.2f} - Quantidade: {peca['quantidade']} - Total: R$ {peca['valor_total']:.2f}"
                )
            )
        self.page.update()

    def calcular_valor_total(self):
        valor_total = sum(
            peca["valor_total"] for peca in self.oficina_app.pecas_selecionadas
        )
        self.valor_total_text.value = f"Valor Total: R$ {valor_total:.2f}"
        self.page.update()


class OficinaApp:

    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.carro_dropdown_os = ft.Dropdown(width=300)
        self.cliente_selecionado = None
        self.carro_selecionado = None
        self.pecas_selecionadas = []
        self.carregar_dados()
        self.build_ui()

        self.oficina = Oficina()
        self.usuario_atual = None
        self.cliente_selecionado = None
        self.clientes_dropdown = []
        self.evento_clientes_carregados = threading.Event()
        page.pubsub.subscribe(self._on_message)
        conexao_db = criar_conexao(nome_banco_de_dados)
        conexao = conexao_db
        self.conexao = criar_conexao(nome_banco_de_dados)
        self.carro_dropdown_os = ft.Dropdown(width=300)
        self.clientes_dropdown = ft.Dropdown(width=300)  # Crie um objeto Dropdown

        self.cliente_dropdown_os = ft.Dropdown(
            width=300,
            on_change=self.carregar_clientes_no_dropdown_os,  # Referencie o método
        )
        self.carregar_clientes_no_dropdown_os(None)  # Inicializa o dropdown de clientes

        self.carro_dropdown_os = ft.Dropdown(width=300)

        # Carrega o Dropdown ao Iniciar
        self.carregar_clientes_no_dropdown()

        # Chama a Função de criar usuario Admin
        criar_usuario_admin(conexao)

        # Modal de cadastro de carro
        self.modal_cadastro_carro = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cadastrar Novo Carro"),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Cadastrar", on_click=self.cadastrar_carro
                            ),
                            ft.OutlinedButton(
                                "Cancelar", on_click=self.fechar_modal_cadastro_carro
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ]
            ),
        )

        # Inputs do formulário
        self.modelo_input = ft.TextField(label="Modelo")
        self.cor_input = ft.TextField(label="Cor")
        self.ano_input = ft.TextField(label="Ano")
        self.placa_input = ft.TextField(label="Placa")
        self.clientes_dropdown = ft.Dropdown(
            width=300,
            options=[],
        )

        # Adicione os inputs ao conteúdo do modal
        self.modal_cadastro_carro.content.controls.insert(0, self.placa_input)
        self.modal_cadastro_carro.content.controls.insert(0, self.ano_input)
        self.modal_cadastro_carro.content.controls.insert(0, self.cor_input)
        self.modal_cadastro_carro.content.controls.insert(0, self.modelo_input)
        self.modal_cadastro_carro.content.controls.insert(0, self.clientes_dropdown)

    # Botões da Tela Inicial
    def build(self):
        self.botoes = {
            # Botão de Login
            "login": ft.ElevatedButton("Efetue Login", on_click=self.abrir_modal_login),
            # Botão Cadastrar Cliente
            "cadastrar_cliente": ft.ElevatedButton(
                "Cadastrar Cliente",
                on_click=self.abrir_modal_cadastrar_cliente,
                disabled=True,
            ),
            # Botão Cadastrar Carro
            "cadastrar_carro": ft.ElevatedButton(
                "Cadastrar Carro",
                on_click=self.abrir_modal_cadastro_carro,
                disabled=True,
            ),
            # Botão Cadastrar Peças
            "cadastrar_pecas": ft.ElevatedButton(
                "Cadastrar / Atualizar Peças",
                on_click=self.abrir_modal_cadastrar_peca,
                disabled=True,
            ),
            # Visualiza o Saldo de Estoque
            "saldo_estoque": ft.ElevatedButton(
                "Visualiza o Saldo de Estoque",
                on_click=self.abrir_modal_saldo_estoque,
                disabled=True,
            ),
            # Visualiza o Saldo de Estoque
            "ordem_servico": ft.ElevatedButton(
                "Criar Ordem de Serviço",
                on_click=self.abrir_modal_os,
                disabled=True,
            ),
            # Sair do App
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

    #     ==================================
    #     FUNÇÕES GERAIS
    #     ==================================

    # Recebe mensagens da thread do banco de dados através do pubsub.
    # As mensagens devem ser dicionários com a chave 'topic' para indicar o tipo de mensagem.
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

        # Manipula as mensagens recebidas do pubsub."""
        elif e["topic"] == "clientes_dropdown":
            # Atualizar o Dropdown do modal de cadastro de carro
            self.clientes_dropdown = e["clientes"]
            self.evento_clientes_carregados.set()

        elif e["topic"] == "peca_cadastrada":
            self.mostrar_alerta(e["mensagem_erro"])

        elif e["topic"] == "peca_atualizada":
            self.mostrar_alerta(e["mensagem_erro"])

        elif e["topic"] == "erro_ao_salvar_peca":
            self.mostrar_alerta(e["mensagem_erro"])

        elif e["topic"] == "erro_db":
            self.mostrar_alerta(e["mensagem_erro"])

        self.page.update()

    # Atualiza o Estado Dos Botoes
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

    # ==================================
    # MOSTRA ALERTAS / FECHAR MODAL
    # ==================================

    def mostrar_alerta(self, mensagem):
        # O código acima está criando e exibindo uma caixa de diálogo de alerta (AlertDialog) com o título "ATENÇÃO"
        # e uma mensagem especificada pela variável "mensagem". A caixa de diálogo contém um único botão rotulado
        # "OK" que, ao ser clicado, chamará o método "fechar_modal" para fechar a caixa de diálogo. O diálogo é
        # definido como modal, o que significa que bloqueará a interação com o resto da página até que ela seja fechada.
        # A caixa de diálogo é então exibida na página e a página é atualizada para refletir as alterações.
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

    # """Fecha qualquer modal aberto."""
    def fechar_modal(self, e):
        """Fecha qualquer modal aberto."""
        self.page.dialog.open = False
        self.page.update()

    # ==================================
    # LOGIN / CADASTRO USUÁRIO
    # ==================================

    # Abre o Modal de Login
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

    # Funçõa para fazer no login
    def fazer_login(self, e):
        dlg = self.page.dialog
        nome = dlg.content.controls[0].value
        senha = dlg.content.controls[1].value

        try:
            fila_db.put(("fazer_login", (nome, senha)))
            self.mostrar_alerta("Processando...")
        except Exception as e:
            self.mostrar_alerta(f"Erro ao processar : {e}")

    # Abre o modal para cadastro de novo usuário.
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

    # Cadastra Usuario do Sistema
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

    # ==================================
    # CADASTRO DE CLIENTES
    # ==================================

    # ABRE O MODAL PARA CADASTRO DE CLIENTES
    def abrir_modal_cadastrar_cliente(self, e):
        self.cadastrar_cliente(e)

    # Coleta dados do cliente e tenta cadastrá-lo.
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

    # Função para Salvar o Cadastro do Cliente
    def salvar_cliente(self, e):
        """Envia a solicitação de cadastro de cliente para a thread do banco de dados."""
        dlg = self.page.dialog
        nome = dlg.content.controls[0].value
        telefone = dlg.content.controls[1].value
        endereco = dlg.content.controls[2].value
        email = dlg.content.controls[3].value

        try:
            fila_db.put(("cadastrar_cliente", (nome, telefone, endereco, email)))
            self.mostrar_alerta("Processando cadastro de cliente. Aguarde...")
            self.fechar_modal(e)
        except Exception as e:
            self.mostrar_alerta(f"Erro ao processar cadastro de cliente: {e}")

        self.page.update()

    # ==================================
    # CADASTRO DE CARROS
    # ==================================

    # aBRE O mODAL PARA REALIZAR O CADASTRO DE CARROS
    def abrir_modal_cadastro_carro(self, e):
        self.carregar_clientes_no_dropdown()
        self.page.dialog = self.modal_cadastro_carro
        self.modal_cadastro_carro.open = True
        self.page.update()

    def fechar_modal_cadastro_carro(self, e):
        self.modelo_input.value = ""
        self.cor_input.value = ""
        self.ano_input.value = ""
        self.placa_input.value = ""
        self.clientes_dropdown.value = None
        self.modal_cadastro_carro.open = False
        self.page.update()

    def cadastrar_carro(self, e):
        # Obter valores dos campos de entrada
        modelo = self.modelo_input.value
        cor = self.cor_input.value
        ano = self.ano_input.value
        placa = self.placa_input.value
        proprietario_id = (
            int(self.clientes_dropdown.value.split(" (ID: ")[1][:-1])
            if self.clientes_dropdown.value
            else None
        )

        # Validações
        if not all([modelo, cor, ano, placa, proprietario_id]):
            self.page.snack_bar = ft.SnackBar(
                ft.Text("Por favor, preencha todos os campos!"),
                bgcolor="red",
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        try:
            ano = int(ano)
            if ano <= 1900 or ano > 2100:  # Validação simples do ano
                raise ValueError("Ano inválido")
        except ValueError:
            self.page.snack_bar = ft.SnackBar(
                ft.Text("Ano inválido. Digite um ano entre 1900 e 2100."),
                bgcolor="red",
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        # Envia os dados para a fila do banco de dados
        fila_db.put(
            (
                "cadastrar_carro",
                (modelo, cor, ano, placa, proprietario_id),
            )
        )

        self.fechar_modal_cadastro_carro(e)  # Fecha o modal após enviar dados

    def carregar_clientes_no_dropdown(self):
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

    # -----------------------------------
    # INICIO FUNÇÕES CADASTRAR PEÇAS
    # ------------------------------------

    # FUNÇÃO ABRIR MODAL CADASTRAR PEÇAS
    def abrir_modal_cadastrar_peca(self, e):
        """Abre o modal para cadastrar uma nova peça."""

        # Define se é uma nova peça (padrão: True)
        self.nova_peca = True

        self.dlg_cadastrar_peca = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cadastrar/Atualizar Peça"),
            content=ft.Column(
                [
                    ft.TextField(label="Nome", ref=ft.Ref[str]()),
                    ft.TextField(label="Referência", ref=ft.Ref[str]()),
                    ft.TextField(label="Fabricante", ref=ft.Ref[str]()),
                    ft.TextField(label="Descrição", ref=ft.Ref[str]()),
                    ft.TextField(label="Preço de Compra", ref=ft.Ref[str]()),
                    ft.TextField(label="Preço de Venda", ref=ft.Ref[str]()),
                    ft.TextField(label="Quantidade em Estoque", ref=ft.Ref[str]()),
                ]
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self.fechar_modal),
                ft.ElevatedButton("Salvar", on_click=self.salvar_peca),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.dialog = self.dlg_cadastrar_peca
        self.dlg_cadastrar_peca.open = True

        # Adiciona evento on_change para os campos de nome e referência
        self.dlg_cadastrar_peca.content.controls[0].on_change = (
            self.verificar_peca_existente
        )
        self.dlg_cadastrar_peca.content.controls[1].on_change = (
            self.verificar_peca_existente
        )

        self.page.update()

    def obter_peca_por_nome_e_referencia(self, nome, referencia):
        """
        Busca uma peça pelo nome e referência.

        Args:
            nome (str): O nome da peça.
            referencia (str): A referência da peça.

        Returns:
            Peca: O objeto Peca se encontrado, None caso contrário.
        """
        with sqlite3.connect(nome_banco_de_dados) as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                "SELECT * FROM pecas WHERE nome=? AND referencia=?", (nome, referencia)
            )
            peca_data = cursor.fetchone()
            if peca_data:
                return Peca(*peca_data[1:])
        return None

    def verificar_peca_existente(self, e):
        """Verifica se a peça já existe no banco de dados."""
        dlg = self.dlg_cadastrar_peca  # Referência ao modal
        nome = dlg.content.controls[0].value
        referencia = dlg.content.controls[1].value

        with sqlite3.connect(nome_banco_de_dados) as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                "SELECT * FROM pecas WHERE nome=? AND referencia=?", (nome, referencia)
            )
            peca_existente = cursor.fetchone()

        # Habilita/desabilita campos com base na existência da peça
        if self.nova_peca:  # Só verifica se for uma nova peça
            peca_existente = self.obter_peca_por_nome_e_referencia(nome, referencia)
            if peca_existente:
                # Desabilita campos (exceto quantidade)
                for i in range(2, 4):  # Índices dos campos a desabilitar
                    dlg.content.controls[i].disabled = True
                self.nova_peca = False  # Indica que não é mais uma nova peça
            else:
                # Habilita os campos se a peça não for encontrada
                for i in range(2, 4):
                    dlg.content.controls[i].disabled = False

        self.page.update()

    # FUNÇÃO DO SALVAR PEÇA

    def salvar_peca(self, e):
        """Salva uma nova peça ou atualiza a quantidade de uma existente."""
        dlg = self.page.dialog
        nome = dlg.content.controls[0].value
        referencia = dlg.content.controls[1].value
        fabricante = dlg.content.controls[2].value
        descricao = dlg.content.controls[3].value
        preco_compra = dlg.content.controls[4].value
        preco_venda = dlg.content.controls[5].value
        quantidade = dlg.content.controls[6].value

        try:
            preco_compra = float(preco_compra)
            preco_venda = float(preco_venda)
            quantidade = int(quantidade)
        except ValueError:
            self.mostrar_alerta("Os campos de preço e quantidade devem ser numéricos.")
            return

        try:
            fila_db.put(
                (
                    "salvar_peca",
                    (
                        nome,
                        referencia,
                        fabricante,
                        descricao,
                        preco_compra,
                        preco_venda,
                        quantidade,
                    ),
                )
            )

            self.mostrar_alerta("Processando informações da peça. Aguarde...")
            self.fechar_modal(e)
        except Exception as e:
            self.mostrar_alerta(f"Erro ao processar informações da peça: {e}")

        self.page.update()

    # -----------------------------------
    # FINAL FUNÇÕES CADASTRAR PEÇAS
    # ------------------------------------

    # =====================================
    # FUNÇÃO ABRIR MODOAL SALDO DE ESTOQUE
    # =====================================

    # Abre o modal para exibir o saldo de estoque.
    def abrir_modal_saldo_estoque(self, e):
        """Abre o modal para exibir o saldo de estoque."""

        movimentacoes = self.carregar_dados_saldo_estoque()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Saldo de Estoque"),
            content=ft.Column(
                [
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Nome")),
                            ft.DataColumn(ft.Text("Referência")),
                            ft.DataColumn(ft.Text("Total de Entradas")),
                            ft.DataColumn(ft.Text("Total de Saídas")),
                            ft.DataColumn(ft.Text("Estoque Final")),
                        ],
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(m[1])),  # Nome da peça
                                    ft.DataCell(ft.Text(m[2])),  # Referência da peça
                                    ft.DataCell(ft.Text(m[3])),  # Total de Entradas
                                    ft.DataCell(ft.Text(m[4])),  # Total de Saídas
                                    ft.DataCell(ft.Text(m[3] - m[4])),  # Estoque Final
                                ]
                            )
                            for m in movimentacoes
                        ],
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton("Fechar", on_click=self.fechar_modal),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # Carrega os dados de movimentação de peças do banco de dados,
    # calculando o saldo final para cada peça
    def carregar_dados_saldo_estoque(self):
        """Carrega os dados de movimentação de peças do banco de dados,
        calculando o saldo final para cada peça.
        """
        with sqlite3.connect(nome_banco_de_dados) as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                """
                SELECT 
                    p.id,
                    p.nome, 
                    p.referencia,
                    COALESCE(SUM(CASE WHEN mp.tipo_movimentacao = 'entrada' THEN mp.quantidade ELSE 0 END), 0) AS total_entradas,
                    COALESCE(SUM(CASE WHEN mp.tipo_movimentacao = 'saida' THEN mp.quantidade ELSE 0 END), 0) AS total_saidas
                FROM 
                    pecas p
                LEFT JOIN 
                    movimentacao_pecas mp ON p.id = mp.peca_id
                GROUP BY
                    p.id, p.nome, p.referencia;
                """
            )
            movimentacoes = cursor.fetchall()

        return movimentacoes

    # ======================================
    # ORDEM DE SERVIÇO
    # ======================================

    def carregar_carros_no_dropdown_os(self, e):
        """Carrega a lista de carros no dropdown,
        baseado no cliente selecionado.
        """
        cliente_id = None
        if self.cliente_dropdown_os.current.value:
            cliente_id = int(
                self.cliente_dropdown_os.current.value.split(" (ID: ")[1][:-1]
            )

        try:
            with criar_conexao(nome_banco_de_dados) as conexao:
                if cliente_id:
                    carros = self.obter_carros_por_cliente(conexao, cliente_id)
                    self.carro_dropdown_os.current.options = [
                        ft.dropdown.Option(f"{carro[1]} (ID: {carro[0]})")
                        for carro in carros
                    ]
                else:
                    self.carro_dropdown_os.current.options = []
                self.page.update()
        except Exception as e:
            print(f"Erro ao carregar carros no dropdown: {e}")

    def carregar_clientes_no_dropdown_os(self, e):
        """Carrega a lista de clientes no dropdown."""
        try:
            with criar_conexao(nome_banco_de_dados) as conexao:
                clientes = obter_clientes(conexao)  # Consulte o banco de dados
                self.cliente_dropdown_os.options = [
                    ft.dropdown.Option(f"{cliente[1]} (ID: {cliente[0]})")
                    for cliente in clientes
                ]
                self.page.update()
        except Exception as e:
            print(f"Erro ao carregar clientes no dropdown: {e}")

    def carregar_dados(self):
        with criar_conexao(nome_banco_de_dados) as conexao:
            self.clientes = obter_clientes(conexao)
            self.carros = []  # Inicialmente vazio
            self.pecas = obter_pecas(conexao)

    def build_ui(self):
        self.cliente_dropdown = ft.Dropdown(
            width=300,
            options=[
                ft.dropdown.Option(f"{cliente[1]} (ID: {cliente[0]})")
                for cliente in self.clientes
            ],
            on_change=self.cliente_alterado,
        )
        self.carro_dropdown = ft.Dropdown(width=300)
        self.peca_dropdown = ft.Dropdown(
            width=200,
            options=[ft.dropdown.Option(f"{peca[1]}") for peca in self.pecas],
        )
        self.preco_unitario_field = ft.TextField(
            label="Preço Unitário", width=100, value="0.00"
        )
        self.quantidade_field = ft.TextField(label="Quantidade", width=100, value="1")
        self.adicionar_peca_button = ft.ElevatedButton(
            "Adicionar Peça", on_click=self.adicionar_peca
        )
        self.pecas_list_view = ft.ListView(expand=True, height=200)
        self.valor_total_text = ft.Text("Valor Total: R$ 0.00")

        self.modal_ordem_servico = ft.AlertDialog(
            modal=True,
            title=ft.Text("Criar Ordem de Serviço"),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Cliente:", width=100),
                            self.cliente_dropdown,
                        ],
                    ),
                    ft.Row(
                        [
                            ft.Text("Carro:", width=100),
                            self.carro_dropdown,
                        ],
                    ),
                    ft.Row(
                        [
                            ft.Text("Peça:", width=100),
                            self.peca_dropdown,
                        ],
                    ),
                    ft.Row(
                        [
                            ft.Text("Preço Unitário:", width=100),
                            self.preco_unitario_field,
                        ],
                    ),
                    ft.Row(
                        [
                            ft.Text("Quantidade:", width=100),
                            self.quantidade_field,
                        ],
                    ),
                    ft.Row(
                        [
                            self.adicionar_peca_button,
                        ],
                    ),
                    self.pecas_list_view,
                    self.valor_total_text,
                ]
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self.fechar_modal_os),
                ft.TextButton("Criar OS", on_click=self.criar_ordem_servico),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def cliente_alterado(self, e):
        self.cliente_selecionado = self.cliente_dropdown.value
        self.carro_dropdown.options = []
        if self.cliente_selecionado:
            cliente_id = int(self.cliente_selecionado.split(" (ID: ")[1][:-1])
            with criar_conexao(nome_banco_de_dados) as conexao:
                self.carros = obter_carros_por_cliente(conexao, cliente_id)
            self.carro_dropdown.options = [
                ft.dropdown.Option(f"{carro[1]}") for carro in self.carros
            ]
        self.carro_dropdown.value = None
        self.page.update()

    def adicionar_peca(self, e):
        peca_nome = self.peca_dropdown.value
        preco_unitario = float(self.preco_unitario_field.value)
        quantidade = float(self.quantidade_field.value)
        valor_total = preco_unitario * quantidade

        self.pecas_selecionadas.append(
            {
                "nome": peca_nome,
                "preco_unitario": preco_unitario,
                "quantidade": quantidade,
                "valor_total": valor_total,
            }
        )
        self.atualizar_lista_pecas()
        self.calcular_valor_total()

    def atualizar_lista_pecas(self):
        self.pecas_list_view.controls = []
        for peca in self.pecas_selecionadas:
            self.pecas_list_view.controls.append(
                ft.Text(
                    f"{peca['nome']} - Preço Unitário: R$ {peca['preco_unitario']:.2f} - Quantidade: {peca['quantidade']} - Total: R$ {peca['valor_total']:.2f}"
                )
            )
        self.page.update()

    def calcular_valor_total(self):
        valor_total = sum(peca["valor_total"] for peca in self.pecas_selecionadas)
        self.valor_total_text.value = f"Valor Total: R$ {valor_total:.2f}"
        self.page.update()

    def abrir_modal_os(self, e):
        """Abre o modal para criar uma nova ordem de serviço."""
        self.limpar_campos_os()
        self.page.dialog = self.modal_ordem_servico
        self.modal_ordem_servico.open = True
        self.page.update()

    def fechar_modal_os(self, e):
        """Fecha o modal de ordem de serviço."""
        self.modal_ordem_servico.open = False
        self.page.update()

    def limpar_campos_os(self):
        """Limpa os campos do modal de ordem de serviço."""
        self.cliente_dropdown.value = None
        self.carro_dropdown.options = []  # Limpa as opções de carros
        self.carro_dropdown.value = None
        self.peca_dropdown.value = None
        self.preco_unitario_field.value = "0.00"
        self.quantidade_field.value = "1"
        self.pecas_selecionadas = []
        self.pecas_list_view.controls = []
        self.valor_total_text.value = "Valor Total: R$ 0.00"
        self.page.update()

    def criar_ordem_servico(self, e):
        if not all(
            [
                self.cliente_dropdown.value,
                self.carro_dropdown.value,
                self.pecas_selecionadas,
            ]
        ):
            ft.snack_bar = ft.SnackBar(ft.Text("Preencha todos os campos!"))
            self.page.show_snack_bar(ft.snack_bar)
            return

        pecas_quantidades = {}

        try:
            cliente_id = int(self.cliente_dropdown.value.split(" (ID: ")[1][:-1])
            carro_id = int(self.carro_dropdown.value.split(" (ID: ")[1][:-1])

            # Imprime o conteúdo das listas antes do loop
            print("self.pecas_selecionadas:", self.pecas_selecionadas)
            print("self.pecas:", self.pecas)

            # Preencher o dicionário pecas_quantidades
            for peca_selecionada in self.pecas_selecionadas:
                print("peca_selecionada:", peca_selecionada)  # Novo print
                peca_id = None
                print("peca_id:", peca_id)  # Novo print
                
                # Utiliza enumerate para obter o índice e o valor de self.pecas
                for indice, peca in enumerate(self.pecas):
                    # CORREÇÃO: Compara com peca_selecionada['id'], não com o índice
                    print(f"Comparando peca_selecionada['id'] ({peca_selecionada['id']}) com peca[{indice}][0] ({peca[0]})")
                    print("Conteúdo de pecas_quantidades a cda inclusao:", pecas_quantidades)
                    if peca[0] == peca_selecionada['id']:
                        peca_id = peca[0]  # Define peca_id se a comparação for verdadeira
                        pecas_quantidades[peca_id] = peca_selecionada["quantidade"]
                        break # Sai do loop interno após encontrar a peça
                    
                # Verifica se peca_id foi encontrado
                if peca_id is not None:
                    print("peca_id:", peca_id)
                else:
                    print(f"peça com ID {peca_selecionada['id']} não encontrada em self.pecas")

            print("Conteúdo de pecas_quantidades:", pecas_quantidades)
                

            with criar_conexao(nome_banco_de_dados) as conexao:
                # Verificar a quantidade em estoque ANTES de criar a OS
                for peca_id, quantidade in pecas_quantidades.items():
                    if not quantidade_em_estoque_suficiente(
                        conexao, peca_id, quantidade
                    ):
                        raise ValueError(
                            f"Quantidade insuficiente em estoque para a peça {peca_id}"
                        )

                # Inserir a OS somente se houver estoque suficiente
                ordem_servico_id = inserir_ordem_servico(
                    conexao, cliente_id, carro_id, pecas_quantidades
                )

                # Atualizar o estoque APÓS criar a OS com sucesso
                if ordem_servico_id is not None:
                    for peca_id, quantidade in pecas_quantidades.items():
                        atualizar_estoque_peca(conexao, peca_id, -quantidade)

            self.gerar_pdf_os(ordem_servico_id)
            self.fechar_modal_os(e)
            self.limpar_campos_os()
            ft.snack_bar = ft.SnackBar(ft.Text("Ordem de Serviço criada com sucesso!"))
            self.page.show_snack_bar(ft.snack_bar)
        except ValueError as e:
            # Exibe a mensagem de erro específica para erros de validação
            print(f"Erro de validação: {e}")
            ft.snack_bar = ft.SnackBar(ft.Text(str(e)))
            self.page.show_snack_bar(ft.snack_bar)
        except Exception as e:
            print("IMprime se deu erro o Conteúdo de pecas_quantidades:", pecas_quantidades)
            # Imprime o conteúdo das listas antes do loop
            print("self.pecas_selecionadas:", self.pecas_selecionadas)
            print("self.pecas:", self.pecas)
            print(f"Aqui deu erro Erro ao criar ordem de serviço: {e}")
            ft.snack_bar = ft.SnackBar(ft.Text("Erro ao criar ordem de serviço!"))
            self.page.show_snack_bar(ft.snack_bar)

    def gerar_pdf_os(self, ordem_servico_id):
        try:
            cliente_nome = self.cliente_dropdown.value.split(" (ID: ")[0]
            placa_carro = self.carro_dropdown.value
            data_hora_criacao = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"{cliente_nome}_{placa_carro}_{data_hora_criacao}.pdf"
            caminho_pasta = "Histórico"
            os.makedirs(caminho_pasta, exist_ok=True)
            caminho_arquivo = os.path.join(caminho_pasta, nome_arquivo)

            doc = SimpleDocTemplate(
                caminho_arquivo,
                pagesize=letter,
                title=f"Ordem de Serviço - Nº {ordem_servico_id}",
            )
            conteudo = []
            estilos = getSampleStyleSheet()
            conteudo.append(
                Paragraph(
                    f"Ordem de Serviço - Nº {ordem_servico_id}",
                    estilos["Heading1"],
                )
            )
            conteudo.append(Spacer(1, 12))
            conteudo.append(Paragraph(f"Cliente: {cliente_nome}", estilos["Normal"]))
            conteudo.append(
                Paragraph(f"Placa do Carro: {placa_carro}", estilos["Normal"])
            )
            conteudo.append(
                Paragraph(
                    f"Data de Criação: {data_hora_criacao}",
                    estilos["Normal"],
                )
            )
            conteudo.append(Spacer(1, 12))
            for peca in self.pecas_selecionadas:
                conteudo.append(
                    Paragraph(
                        f"- {peca['nome']} - Preço Unitário: R$ {peca['preco_unitario']:.2f} - Quantidade: {peca['quantidade']} - Total: R$ {peca['valor_total']:.2f}",
                        estilos["Normal"],
                    )
                )
            conteudo.append(Spacer(1, 12))
            conteudo.append(
                Paragraph(
                    f"Valor Total: R$ {sum(peca['valor_total'] for peca in self.pecas_selecionadas):.2f}",
                    estilos["Heading3"],
                )
            )

            doc.build(conteudo)

            print(f"PDF da OS gerado com sucesso em: {caminho_arquivo}")
        except Exception as e:
            print(f"Erro ao gerar PDF da OS: {e}")

    # =============================
    # SAIR DO APLICATIVO
    # ============================

    # Função para Encerrar o Aplicativo usado no VBotão SAIR
    def sair_do_app(self, e):
        self.page.window_destroy()


# Processa as operações do banco de dados em uma thread separada.
# Envia mensagens para a thread principal usando pubsub com informações sobre o resultado das operações.
def processar_fila_db(page):
    """
    Processa as operações do banco de dados em uma thread separada.
    Envia mensagens para a thread principal usando pubsub com informações sobre o resultado das operações.
    """

    conexao_db = criar_conexao(nome_banco_de_dados)
    try:
        while True:

            try:

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
                        page.pubsub.send_all(
                            {
                                "topic": "usuario_cadastrado",
                                "usuario": None,
                                "mensagem_erro": "Usuário cadastrado com sucesso!",
                            }
                        )
                    except sqlite3.IntegrityError:
                        page.pubsub.send_all(
                            {
                                "topic": "erro_cadastro_usuario",
                                "mensagem_erro": "Nome de usuário já existe!",
                            }
                        )
                    except Exception as e:
                        page.pubsub.send_all(
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
                            page.pubsub.send_all(
                                {"topic": "login_bem_sucedido", "usuario": usuario}
                            )
                        else:
                            page.pubsub.send_all(
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
                            page.pubsub.send_all(
                                {
                                    "topic": "usuario_cadastrado",
                                    "mensagem_erro": f"Usuário '{nome}' cadastrado com sucesso! Faça o login.",
                                }
                            )
                        except Exception as e:
                            page.pubsub.send_all(
                                {
                                    "topic": "login_falhou",
                                    "mensagem_erro": f"Erro ao cadastrar usuário: {e}",
                                }
                            )

                elif operacao == "cadastrar_cliente":
                    # Nova operação
                    nome, telefone, endereco, email = dados
                    cursor = conexao_db.cursor()

                    try:
                        cursor.execute(
                            "INSERT INTO clientes (nome, telefone, endereco, email) VALUES (?, ?, ?, ?)",
                            (nome, telefone, endereco, email),
                        )
                        conexao_db.commit()
                        page.pubsub.send_all(
                            {
                                "topic": "cliente_cadastrado",
                                "mensagem_erro": "Cliente cadastrado com sucesso!",
                            }
                        )
                    except sqlite3.IntegrityError:
                        page.pubsub.send_all(
                            {
                                "topic": "erro_cadastro_cliente",
                                "mensagem_erro": "Já existe um cliente com este nome.",
                            }
                        )
                    except Exception as e:
                        page.pubsub.send_all(
                            {
                                "topic": "erro_cadastro_cliente",
                                "mensagem_erro": f"Erro ao cadastrar cliente: {str(e)}",
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
                        page.pubsub.send_all(
                            {
                                "topic": "carro_cadastrado",
                                "mensagem_erro": "Carro cadastrado com sucesso!",
                            }
                        )
                    except sqlite3.IntegrityError:
                        page.pubsub.send_all(
                            {
                                "topic": "erro_cadastro_carro",
                                "mensagem_erro": "Já existe um carro com essa placa.",
                            }
                        )
                    except Exception as e:
                        page.pubsub.send_all(
                            {
                                "topic": "erro_cadastro_carro",
                                "mensagem_erro": f"Erro ao cadastrar carro: {str(e)}",
                            }
                        )

                elif operacao == "obter_clientes_dropdown":  #  nova operação
                    cursor = conexao_db.cursor()
                    cursor.execute("SELECT id, nome FROM clientes")
                    clientes = cursor.fetchall()
                    opcoes_dropdown = [
                        ft.dropdown.Option(f"{cliente[1]} (ID: {cliente[0]})")
                        for cliente in clientes
                    ]
                    page.pubsub.send_all(
                        {"topic": "clientes_dropdown", "clientes": opcoes_dropdown}
                    )

                elif operacao == "salvar_peca":
                    (
                        nome,
                        referencia,
                        fabricante,
                        descricao,
                        preco_compra,
                        preco_venda,
                        quantidade,
                    ) = dados
                    cursor = conexao_db.cursor()
                    try:
                        cursor.execute(
                            "SELECT id, quantidade_em_estoque FROM pecas WHERE nome = ? AND referencia = ?",
                            (nome, referencia),
                        )
                        peca_existente = cursor.fetchone()

                        if peca_existente:
                            # Peça existente - atualizar quantidade
                            peca_id, quantidade_atual = peca_existente
                            nova_quantidade = quantidade_atual + quantidade
                            cursor.execute(
                                "UPDATE pecas SET quantidade_em_estoque = ? WHERE id = ?",
                                (nova_quantidade, peca_id),
                            )
                            conexao_db.commit()

                            # Registrar a movimentação de atualização da peça
                            cursor.execute(
                                """
                                INSERT INTO movimentacao_pecas (peca_id, tipo_movimentacao, quantidade)
                                VALUES (?, 'entrada', ?)
                                """,
                                (peca_id, quantidade),
                            )
                            conexao_db.commit()

                            page.pubsub.send_all(
                                {
                                    "topic": "peca_atualizada",
                                    "mensagem_erro": f"Quantidade da peça '{nome}' atualizada com sucesso!",
                                }
                            )
                        else:
                            # Nova peça - inserir na tabela
                            cursor.execute(
                                """
                                INSERT INTO pecas (nome, referencia, fabricante, descricao, preco_compra, preco_venda, quantidade_em_estoque) 
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    nome,
                                    referencia,
                                    fabricante,
                                    descricao,
                                    preco_compra,
                                    preco_venda,
                                    quantidade,
                                ),
                            )
                            peca_id = (
                                cursor.lastrowid
                            )  # Obter o ID da peça recém-inserida
                            conexao_db.commit()

                            # Registrar a entrada da peça na tabela de movimentação
                            cursor.execute(
                                """
                                INSERT INTO movimentacao_pecas (peca_id, tipo_movimentacao, quantidade)
                                VALUES (?, 'entrada', ?)
                                """,
                                (peca_id, quantidade),
                            )
                            conexao_db.commit()

                            page.pubsub.send_all(
                                {
                                    "topic": "peca_cadastrada",
                                    "mensagem_erro": f"Peça '{nome}' cadastrada com sucesso!",
                                }
                            )
                    except Exception as e:
                        page.pubsub.send_all(
                            {
                                "topic": "erro_ao_salvar_peca",
                                "mensagem_erro": f"Erro ao salvar peça: {str(e)}",
                            }
                        )

            except queue.Empty:
                pass

            except sqlite3.IntegrityError as e:
                page.pubsub.send_all(
                    {
                        "topic": "erro_db",
                        "mensagem_erro": f"Erro de integridade no banco de dados: {e}",
                        "dados": dados,
                        "operacao": operacao,
                    }
                )

            except sqlite3.Error as e:
                page.pubsub.send_all(
                    {
                        "topic": "erro_db",
                        "mensagem_erro": f"Erro no banco de dados: {e}",
                        "dados": dados,
                        "operacao": operacao,
                    }
                )

            except Exception as e:
                page.pubsub.send_all(
                    {
                        "topic": "erro_db",
                        "mensagem_erro": f"Erro inesperado: {e}",
                        "dados": dados,
                        "operacao": operacao,
                    }
                )

    except Exception as e:
        print(f"Erro ao processar operação da fila: {e}")

    finally:
        if conexao_db:
            conexao_db.close()
