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
import threading
import sqlite3
import bcrypt
import queue
from datetime import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from flet import UserControl  # Certifique-se de importar os componentes necessários

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

    def __init__(self, page, oficina_app, pecas,  clientes):
        super().__init__()
        self.page = page
        self.oficina_app = oficina_app
        self.pecas = pecas
        self.clientes = clientes
        self.oficina = Oficina()
        
        # Inicializa os atributos no construtor
        self.carro_dropdown_os = ft.Dropdown(width=300)
        self.clientes_dropdown = ft.Dropdown(width=150)
        self.evento_clientes_carregados = threading.Event()

        # Define a conexão como atributo da instancia
        self.conexao = criar_conexao(nome_banco_de_dados)
        
        self.clientes_dropdown = ft.Dropdown(
            width=300,
            options=[],
        )
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

        self.clientes_dropdown = ft.Dropdown(width=300)
        self.evento_clientes_carregados = threading.Event()
        
        self.cliente_dropdown = ft.Dropdown(
            width=150,
            options=[
                ft.dropdown.Option(f"{cliente[1]} (ID: {cliente[0]})")
                for cliente in self.clientes
            ],
            on_change=self.cliente_alterado,
        )
        self.carro_dropdown = ft.Dropdown(width=300)
        self.peca_dropdown = ft.Dropdown(
            width=150,
            options=[ft.dropdown.Option(f"{peca[1]}") for peca in self.pecas],
        )
        self.preco_unitario_field = ft.TextField(
            label="Digite o Preço", width=100, value="0.00"
        )
        self.quantidade_field = ft.TextField(label="Digite a QTD", width=100, value="1")
        self.adicionar_peca_button = ft.ElevatedButton(
            "Adicionar Peça", on_click=self.adicionar_peca
        )
        self.pecas_list_view = ft.ListView(expand=True, height=200)
        self.valor_total_text = ft.Text("Valor Total: R$ 0.00")

        
        
    def build(self):
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
        self.quantidade_field = ft.TextField(label="OficinaQuantidade", width=100, value="1")
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
        
        return self.modal_ordem_servico # Retornar o modal
        
    def abrir_modal_os(self, e):
            """Abre o modal para criar uma nova ordem de serviço."""
            self.limpar_campos_os()
            
            # Criar o AlertDialog diretamente dentro do método abrir_modal_os
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
        
            
            
            self.page.dialog = self.modal_ordem_servico
            self.modal_ordem_servico.open = True
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

    def carregar_carros_no_dropdown_os(self, e):
        """Carrega a lista de carros no dropdown,
        baseado no cliente selecionado.
        """
        cliente_id = None
        if self.oficina_app.cliente_dropdown_os.current.value:
            cliente_id = int(
                self.oficina_app.cliente_dropdown_os.current.value.split(" (ID: ")[1][
                    :-1
                ]
            )

        try:
            with criar_conexao(nome_banco_de_dados) as conexao:
                if cliente_id:
                    carros = self.oficina_app.obter_carros_por_cliente(
                        conexao, cliente_id
                    )
                    self.oficina_app.carro_dropdown_os.current.options = [
                        ft.dropdown.Option(f"{carro[1]} (ID: {carro[0]})")
                        for carro in carros
                    ]
                else:
                    self.oficina_app.carro_dropdown_os.current.options = []
                self.page.update()
        except Exception as e:
            print(f"Erro ao carregar carros no dropdown: {e}")

    def carregar_clientes_no_dropdown_os(self, e):
        """Carrega a lista de clientes no dropdown."""
        try:
            with criar_conexao(nome_banco_de_dados) as conexao:
                clientes = obter_clientes(conexao)  # Consulte o banco de dados
                self.oficina_app.cliente_dropdown_os.options = [
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

    def cliente_alterado(self, e):
        self.cliente_selecionado = self.cliente_dropdown.value
        self.carro_dropdown.options = []
        if self.cliente_selecionado:
            cliente_id = int(self.cliente_selecionado.split(" (ID: ")[1][:-1])
            with criar_conexao(nome_banco_de_dados) as conexao:
                self.carros = obter_carros_por_cliente(conexao, cliente_id)
            self.carro_dropdown.options = [
                ft.dropdown.Option(f"{carro[1]} (ID: {carro[0]}, Placa: {carro[4]})") for carro in self.carros
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

    def fechar_modal_os(self, e):
        """Fecha o modal de ordem de serviço."""
        self.modal_ordem_servico.open = False
        self.page.update()

    def criar_ordem_servico(self, e):
        if not all(
            [
                self.cliente_dropdown.value,
                self.carro_dropdown.value,
                self.pecas_selecionadas,  # self.pecas_selecionadas continua em OficinaApp
            ]
        ):
            ft.snack_bar = ft.SnackBar(ft.Text("Preencha todos os campos!"))
            self.page.show_snack_bar(ft.snack_bar)
            return

        pecas_quantidades = {}

        try:
            cliente_id = int(
                self.cliente_dropdown.value.split(" (ID: ")[1][:-1]
            )
            # Extrair o ID do carro do valor do dropdown (ajustado para a nova formatação)
            carro_id = int(self.carro_dropdown.value.split(" (ID: ")[1].split(",")[0])

            # Imprime o conteúdo das listas antes do loop (apenas para debug)
            print("self.pecas_selecionadas:", self.pecas_selecionadas)
            print("self.pecas:", self.pecas)

            # Preencher o dicionário pecas_quantidades
            for peca_selecionada in self.pecas_selecionadas:
                print("peca_selecionada:", peca_selecionada)
                peca_id = None

                # Utiliza enumerate para obter o índice e o valor de self.pecas
                for indice, peca in enumerate(self.pecas):
                    # CORREÇÃO: Compara com peca_selecionada['nome'], não com peca[0]
                    print(
                        f"Comparando peca_selecionada['nome'] ({peca_selecionada['nome']}) com peca[{indice}][1] ({peca[1]})"
                    )
                    if peca[1] == peca_selecionada["nome"]:
                        peca_id = peca[0]
                        pecas_quantidades[peca_id] = peca_selecionada["quantidade"]
                        print(
                            f"Peça encontrada! peca_id: {peca_id}, quantidade: {peca_selecionada['quantidade']}"
                        )
                        break  # Sai do loop interno após encontrar a peça

                if peca_id is None:
                    print(
                        f"ERRO: Peça com ID {peca_selecionada['id']} não encontrada em self.pecas"
                    )

            print("Conteúdo de pecas_quantidades:", pecas_quantidades)
            valor_total_os = sum(peca['valor_total'] for peca in self.pecas_selecionadas)
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
                    conexao, cliente_id, carro_id, pecas_quantidades, valor_total_os
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
            print(f"Erro ao criar ordem de serviço: {e}")
            ft.snack_bar = ft.SnackBar(ft.Text("Erro ao criar ordem de serviço!"))
            self.page.show_snack_bar(ft.snack_bar)

    def gerar_pdf_os(self, ordem_servico_id):
        try:
            cliente_nome = self.cliente_dropdown.value.split(" (ID: ")[0]
            placa_carro = self.carro_dropdown.value.replace(":","").replace(",","")
            data_hora_criacao = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"OS{ordem_servico_id}_{cliente_nome}_{placa_carro}_{data_hora_criacao}.pdf"
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
                        f"- Peça Utilizada: {peca['nome']} - Preço Unitário: R$ {peca['preco_unitario']:.2f} - Quantidade: {peca['quantidade']} - Total: R$ {peca['valor_total']:.2f}",
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
