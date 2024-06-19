from typing import Any
import flet as ft
import sqlite3
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
    Dropdown,
    dropdown,
)
import urllib.parse
import os
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from models import Oficina, Peca, Carro, Cliente, Usuario
from database import (
    criar_conexao,
    obter_carros_por_cliente,
    obter_clientes,
    obter_pecas,
    inserir_ordem_servico,
    atualizar_estoque_peca,
    quantidade_em_estoque_suficiente,
    inserir_movimentacao_peca,
    nome_banco_de_dados,
)


class OrdemServicoFormulario(UserControl):
    """Formulário para criar uma nova ordem de serviço."""

    def __init__(self, page, oficina_app, pecas, clientes):
        super().__init__()
        self.page = page
        self.oficina_app = oficina_app
        self.pecas = pecas
        self.clientes = clientes

        # Inicializa os atributos diretamente
        self.cliente_dropdown = ft.Dropdown(width=300)
        self.carro_dropdown = ft.Dropdown(width=300)
        self.peca_dropdown = ft.Dropdown(width=200)
        self.preco_unitario_field = ft.TextField(
            label="Preço Unitário", width=100, value="0.00"
        )
        self.total_pecas_text = ft.Text("Total de Peças: R$ 0.00")
        self.mao_de_obra_text = ft.Text("l58Mão de Obra: R$ 0.00")
        self.total_com_mao_de_obra_text = ft.Text("Total com mão de obra: R$ 0.00")
        self.pagamento_avista_text = ft.Text("Pagamento à Vista:")
        self.pagamento_cartao_text = ft.Text("Pagamento No Cartão: Consultar Valores")

        self.quantidade_field = ft.TextField(label="Quantidade", width=100, value="")
        self.adicionar_peca_button = ft.ElevatedButton(
            "Adicionar Peça", on_click=self.adicionar_peca
        )
        
        self.pecas_list_view = ft.ListView(expand=True, height=200)
        self.valor_total_text = ft.Text("l71Valor Total: R$ 0.00")
        self.pecas_selecionadas = []
        self.link_whatsapp = None

        self.preco_mao_de_obra_field = ft.TextField(
            label="Mão de Obra (R$)", width=100, value="0.00"
        )

        # Carrega os dados iniciais
        self.carregar_dados()
        self.carregar_clientes_no_dropdown()

        # Define o modal da ordem de serviço
        self.modal_ordem_servico = self.criar_modal_ordem_servico()

    def criar_modal_ordem_servico(self):
        return ft.AlertDialog(
            modal=True,
            title=ft.Text("l87Criar Ordem de Serviço"),
            content=ft.Column(
                [
                    ft.Text("1Cliente:", width=100),
                    self.cliente_dropdown,
                    ft.Text("2Carro:", width=100),
                    self.carro_dropdown,
                    ft.Text("3Peça:", width=100),
                    self.peca_dropdown,
                    ft.Text("4Preço Unitário:", width=100),
                    self.preco_unitario_field,
                    ft.Text("5Quantidade:", width=100),
                    self.quantidade_field,
                    self.adicionar_peca_button,
                    ft.Text("6Mão de Obra (R$):", width=120),
                    self.preco_mao_de_obra_field,
                    
                    # ... (outros campos)
                    self.pecas_list_view,  # Lista de peças com mais espaço
                    self.valor_total_text,
                    self.total_pecas_text,
                    self.mao_de_obra_text,
                    self.total_com_mao_de_obra_text,
                    self.pagamento_avista_text,
                    self.pagamento_cartao_text,
                    ft.Row(
                        [
                            
                            ft.ElevatedButton(
                                "7Criar OS", on_click=self.criar_ordem_servico
                            ),
                        ]
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,  # Habilitar rolagem se necessário
            ),
            actions=[
                ft.ElevatedButton(
                                "8Visualizar OS", on_click=self.visualizar_os
                            ),
                ft.TextButton("9Cancelar", on_click=self.fechar_modal_os),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def atualizar_lista_pecas(self):
        self.pecas_list_view.controls = []
        for i, peca in enumerate(self.pecas_selecionadas):
            self.pecas_list_view.controls.append(
                ft.Row(
                    [
                        ft.Text(
                            f"{peca['nome']} - Preço Unitário: R$ {peca['preco_unitario']:.2f} - Quantidade: {peca['quantidade']} - Total: R$ {peca['valor_total']:.2f}"
                        ),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            on_click=lambda e, index=i: self.remover_peca(index),
                        ),
                    ]
                )
            )
        self.page.update()

    def visualizar_os(self, e):
        """Exibe uma prévia da OS em um novo modal."""
        if not all([self.cliente_dropdown.value, self.carro_dropdown.value]):
            ft.snack_bar = ft.SnackBar(ft.Text("Preencha os campos Cliente e Carro!"))
            self.page.show_snack_bar(ft.snack_bar)
            return

        # Obter os dados da OS
        cliente_nome = self.cliente_dropdown.value.split(" (ID: ")[0]
        carro_descricao = self.carro_dropdown.value
        mao_de_obra = float(self.preco_mao_de_obra_field.value)

        # Criar o conteúdo da pré-visualização
        conteudo_preview = ft.Column(
            [
                ft.Text(f"Cliente: {cliente_nome}"),
                ft.Text(f"Carro: {carro_descricao}"),
                ft.Divider(),
                # Exibir a lista de peças formatada
                *[
                    ft.Text(
                        f"{peca['nome']} - Preço Unitário: R$ {peca['preco_unitario']:.2f} - Quantidade: {peca['quantidade']} - Total: R$ {peca['valor_total']:.2f}"
                    )
                    for peca in self.pecas_selecionadas
                ],
                ft.Divider(),
                ft.Text(self.mao_de_obra_text.value),  # Mão de obra
                ft.Text(self.total_pecas_text.value),
                ft.Text(self.total_com_mao_de_obra_text.value),
                ft.Text(self.pagamento_avista_text.value),  # Pagamento à vista
            ]
        )

        # Criar o modal de pré-visualização
        modal_preview = ft.AlertDialog(
            modal=False,  # Permite editar apos visualizar
            title=ft.Text("Pré-visualização da OS"),
            content=conteudo_preview,
            actions=[ft.TextButton("Fechar", on_click=self.fechar_modal_preview)],
        )

        # Exibir o modal de pré-visualização
        self.page.dialog = self.modal_ordem_servico
        modal_preview.open = True
        self.page.update()

    def fechar_modal_preview(self, e):
        """Fecha o modal de pré-visualização."""
        self.page.dialog.open = False
        self.page.update()

    def remover_peca(self, index):
        """Remove uma peça da lista de peças selecionadas."""
        del self.pecas_selecionadas[index]
        self.atualizar_lista_pecas()
        self.calcular_valor_total()

    def carregar_clientes_no_dropdown(self):
        """Carrega a lista de clientes no dropdown."""
        try:
            with criar_conexao(nome_banco_de_dados) as conexao:
                clientes = obter_clientes(conexao)
                self.cliente_dropdown.options = [
                    ft.dropdown.Option(f"{cliente[1]} (ID: {cliente[0]})")
                    for cliente in clientes
                ]
                self.cliente_dropdown.on_change = self.cliente_alterado
                self.page.update()
        except Exception as e:
            print(f"Erro ao carregar clientes no dropdown: {e}")
            # TODO: Exibir mensagem de erro para o usuário

    def carregar_carros_no_dropdown(self, cliente_id):
        """Carrega a lista de carros no dropdown,
        baseado no cliente selecionado.
        """
        try:
            with criar_conexao(nome_banco_de_dados) as conexao:
                if cliente_id:
                    carros = obter_carros_por_cliente(conexao, cliente_id)
                    self.carro_dropdown.options = [
                        ft.dropdown.Option(
                            f"{carro[1]} (ID: {carro[0]}, Placa: {carro[4]})"
                        )
                        for carro in carros
                    ]
                else:
                    self.carro_dropdown.options = []
                self.page.update()
        except Exception as e:
            print(f"Erro ao carregar carros no dropdown: {e}")
            # TODO: Exibir mensagem de erro para o usuário

    def carregar_dados(self):
        """Carrega os dados iniciais do formulário."""
        with criar_conexao(nome_banco_de_dados) as conexao:
            self.clientes = obter_clientes(conexao)
            self.pecas = obter_pecas(conexao)
        # Define as opções do dropdown de peças
        self.peca_dropdown.options = [
            ft.dropdown.Option(f"{peca[1]}") for peca in self.pecas
        ]
        self.page.update()

    def cliente_alterado(self, e):
        """Atualiza o dropdown de carros quando o cliente é alterado."""
        self.cliente_selecionado = self.cliente_dropdown.value
        if self.cliente_selecionado:
            cliente_id = int(self.cliente_selecionado.split(" (ID: ")[1][:-1])
            self.carregar_carros_no_dropdown(cliente_id)
        else:
            self.carregar_carros_no_dropdown(None)

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
        self.calcular_valor_total()  # atuazando brancjh

    def calcular_valor_total(self):
        valor_total = sum(peca["valor_total"] for peca in self.pecas_selecionadas)
        self.valor_total_text.value = f"Valor Total: R$ {valor_total:.2f}"
        self.page.update()

    def fechar_modal_os(self, e):
        """Fecha o modal de ordem de serviço."""
        self.modal_ordem_servico.open = False
        self.page.update()

    def criar_ordem_servico(self):
        """Cria a ordem de serviço no banco de dados."""
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
            carro_id = int(self.carro_dropdown.value.split(" (ID: ")[1].split(",")[0])

            for peca_selecionada in self.pecas_selecionadas:
                for peca in self.pecas:
                    if peca[1] == peca_selecionada["nome"]:
                        peca_id = peca[0]
                        pecas_quantidades[peca_id] = peca_selecionada["quantidade"]
                        break

            mao_de_obra = float(self.preco_mao_de_obra_field.value)
            valor_total_os = (
                sum(peca["valor_total"] for peca in self.pecas_selecionadas)
                + mao_de_obra
            )

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
                    conexao,
                    cliente_id,
                    carro_id,
                    pecas_quantidades,
                    valor_total_os,
                    mao_de_obra,
                )

                # Atualizar estoque e registrar movimentação após criar a OS
                if ordem_servico_id is not None:
                    for peca_id, quantidade in pecas_quantidades.items():
                        atualizar_estoque_peca(conexao, peca_id, -quantidade)
                        inserir_movimentacao_peca(
                            conexao,
                            peca_id,
                            "saida",
                            quantidade,
                            ordem_servico_id,
                        )

            self.gerar_pdf_os(ordem_servico_id)
            self.gerar_link_whatsapp(ordem_servico_id)
            self.abrir_link_whatsapp()
            self.fechar_modal_os(e)
            self.limpar_campos_os()
            ft.snack_bar = ft.SnackBar(ft.Text("Ordem de Serviço criada com sucesso!"))
            self.page.show_snack_bar(ft.snack_bar)
            self.page.update()

        except ValueError as e:
            # Exibe a mensagem de erro específica para erros de validação
            print(f"Erro de validação: {e}")
            ft.snack_bar = ft.SnackBar(ft.Text(str(e)))
            self.page.show_snack_bar(ft.snack_bar)
        except Exception as e:
            print(f"Erro ao criar ordem de serviço: {e}")
            ft.snack_bar = ft.SnackBar(ft.Text("Erro ao criar ordem de serviço!"))
            self.page.show_snack_bar(ft.snack_bar)

    def gerar_texto_os(self, ordem_servico_id):
        """Gera o texto da ordem de serviço para ser usado na mensagem do WhatsApp."""

        cliente_nome = self.cliente_dropdown.value.split(" (ID: ")[0]
        placa_carro = self.carro_dropdown.value.replace(":", "").replace(",", "")
        data_hora_criacao = datetime.now().strftime("%Y%m%d_%H%M%S")

        texto_os = f"Ordem de Serviço - Nº {ordem_servico_id}\n\n"
        texto_os += f"Cliente: {cliente_nome}\n"
        texto_os += f"Placa do Carro: {placa_carro}\n"
        texto_os += f"Data de Criação: {data_hora_criacao}\n\n"

        for peca in self.pecas_selecionadas:
            texto_os += f"- Peça Utilizada: {peca['nome']} - Preço Unitário: R$ {peca['preco_unitario']:.2f} - Quantidade: {peca['quantidade']} - Total: R$ {peca['valor_total']:.2f}\n"

        texto_os += f"\nValor Total: R$ {sum(peca['valor_total'] for peca in self.pecas_selecionadas):.2f}"

        return texto_os

    def gerar_link_whatsapp(self, ordem_servico_id):
        try:

            cliente_nome = self.cliente_dropdown.value.split(" (ID: ")[0]
            placa_carro = self.carro_dropdown.value.replace(":", "").replace(",", "")

            # Buscar o número de telefone do cliente (você precisa implementar buscar_numero_cliente)
            if self.cliente_dropdown.value:
                cliente_nome = self.cliente_dropdown.value.split(" (ID: ")[0]
                numero_telefone = self.buscar_numero_cliente(cliente_nome)

            # Buscar o número de telefone do cliente
            if self.cliente_dropdown.value:
                cliente_nome = self.cliente_dropdown.value.split(" (ID: ")[0]
                numero_telefone = self.buscar_numero_cliente(cliente_nome)
            else:
                print("Erro: Nenhum cliente selecionado no dropdown.")
                return None

            if numero_telefone:
                mensagem = self.gerar_texto_os(ordem_servico_id)
                texto_codificado = urllib.parse.quote(mensagem)
                link_whatsapp = f"https://web.whatsapp.com/send?phone={numero_telefone}&text={texto_codificado}"
                print(f"Link do WhatsApp: {link_whatsapp}")
                self.link_whatsapp = link_whatsapp
                return link_whatsapp

                # Habilita o botão de enviar por WhatsApp
                # self.enviar_whatsapp_button.disabled = False

            else:
                print(
                    f"Número de telefone não encontrado para o cliente: {cliente_nome}"
                )
                return None
        except Exception as e:
            print(f"Erro ao gerar link do WhatsApp: {e}")
            return None

    def buscar_numero_cliente(self, cliente_nome):
        """
        Busca o número de telefone de um cliente pelo nome.

        Args:
            conexao: A conexão com o banco de dados SQLite.
            cliente_nome (str): O nome do cliente.

        Returns:
            str: O número de telefone do cliente ou None se não encontrado.
        """
        print(f"Nome do cliente sendo buscado: '{cliente_nome}'")
        try:
            with criar_conexao(nome_banco_de_dados) as conexao:
                cursor = conexao.cursor()

                # Nova linha para debugar
                consulta_sql = "SELECT telefone FROM clientes WHERE nome = ?"
                print(f"Consulta SQL: {consulta_sql}, Parâmetros: {cliente_nome}")
                cursor.execute(
                    "SELECT telefone FROM clientes WHERE nome = ?", (cliente_nome,)
                )
                resultado = cursor.fetchone()
                print(f"Resultado da consulta: {resultado}")
                if resultado:
                    print(f"Número de telefone encontrado: {resultado[0]}")
                    # link = self.gerar_link_whatsapp(ordem_servico_id) #certifique-se de ter passado o argumento ordem_servico_id
                    # print(link)  # Mova o print para dentro do bloco if

                    return resultado[0]
                else:
                    print(f"Nenhum número de telefone encontrado para {cliente_nome}")
                    ft.snack_bar = ft.SnackBar(
                        ft.Text(
                            f"Cliente {cliente_nome} não possui número de telefone cadastrado."
                        )
                    )
                    self.page.show_snack_bar(ft.snack_bar)
                    return None

        except sqlite3.Error as e:
            print(f"Erro ao buscar número do cliente: {e}")
            return None

    def gerar_pdf_os(self, ordem_servico_id):
        try:
            cliente_nome = self.cliente_dropdown.value.split(" (ID: ")[0]
            placa_carro = self.carro_dropdown.value.replace(":", "").replace(",", "")
            data_hora_criacao = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"OS{ordem_servico_id}_{cliente_nome}_{placa_carro}_{data_hora_criacao}.pdf"
            caminho_pasta = "c:/big/historico"
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

    def abrir_link_whatsapp(self, e=None):
        if self.link_whatsapp:
            try:
                print("Abir link!")
                self.page.launch_url(self.link_whatsapp)
            except Exception as e:
                print(f"Erro ao abrir o self.link_whatsapp: {e}")
