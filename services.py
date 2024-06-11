import flet as ft
import threading
import sqlite3
import bcrypt
import queue


from utils import mostrar_alerta, fechar_modal
from models import Oficina, Peca, Cliente, Usuario, Carro
from database import criar_conexao, criar_usuario_admin, nome_banco_de_dados, fila_db


class OficinaApp:

    def __init__(self, page: ft.Page):
        self.page = page
        self.oficina = Oficina()
        self.usuario_atual = None
        self.cliente_selecionado = None
        self.clientes_dropdown = []
        self.evento_clientes_carregados = threading.Event()
        page.pubsub.subscribe(self._on_message)
        conexao_db = criar_conexao(nome_banco_de_dados)
        conexao = conexao_db

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
                            ft.ElevatedButton("Cadastrar", on_click=self.cadastrar_carro),
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
            "cadastrar_carro": ft.ElevatedButton(# Botão Cadastrar Carro
                "Cadastrar Carro",
                on_click=self.abrir_modal_cadastro_carro,
                disabled=True,
            ),
            "cadastrar_pecas": ft.ElevatedButton( # Botão Cadastrar Peças
                "Cadastrar Peças",
                on_click=self.abrir_modal_cadastrar_peca,
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
