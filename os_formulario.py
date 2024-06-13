import flet as ft
from flet import (
    Column,
    Row,
    Text,
    Dropdown,
    dropdown,
    TextField,
    ElevatedButton,
    ListView,
)



class OrdemServicoFormulario(ft.UserControl):
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
            options=[
                dropdown.Option(f"{peca[1]}")
                for peca in self.oficina_app.pecas
            ],
        )
        self.quantidade_field = TextField(
            label="Quantidade", width=100, value="1"
        )
        self.adicionar_peca_button = ElevatedButton(
            "Adicionar Peça", on_click=self.adicionar_peca
        )
        self.pecas_list_view = ListView(expand=True, height=200)
        self.valor_total_text = Text("Valor Total: R$ 0.00")

    def build(self):
        return Column(
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
            )

    def cliente_alterado(self, e):
        self.carro_dropdown.options = []
        cliente_selecionado = self.cliente_dropdown.value
        if cliente_selecionado:
            cliente_id = int(
                cliente_selecionado.split(" (ID: ")[1][:-1]
            )
            with self.oficina_app.criar_conexao(
                self.oficina_app.nome_banco_de_dados
            ) as conexao:
                carros = self.oficina_app.obter_carros_por_cliente(
                    conexao, cliente_id
                )
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
            (
                peca[5]
                for peca in self.oficina_app.pecas
                if peca[1] == peca_nome
            ),
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
            peca["valor_total"]
            for peca in self.oficina_app.pecas_selecionadas
        )
        self.valor_total_text.value = (
            f"Valor Total: R$ {valor_total:.2f}"
        )
        self.page.update()