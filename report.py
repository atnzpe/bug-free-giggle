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

from os_formulario import OrdemServicoFormulario
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


from fpdf import FPDF





    
def gerar_relatorio_os(self, e):
    """Gera um relatório com todas as OSs criadas, incluindo valor total e quantidade de peças."""

    # Consultar o banco de dados para obter as OSs
    cursor = criar_conexao(nome_banco_de_dados)
    cursor.execute("SELECT * FROM OrdensDeServico")
    os_data = cursor.fetchall()

    # Consultar o banco de dados para obter os detalhes das peças usadas em cada OS
    cursor.execute("""
        SELECT od.os_id, SUM(p.valor * od.quantidade) AS valor_total_pecas, SUM(od.quantidade) AS quantidade_total_pecas
        FROM OrdensDeServico_Pecas od
        JOIN Pecas p ON od.peca_id = p.id
        GROUP BY od.os_id
    """)
    pecas_data = cursor.fetchall()

    # Criar um dicionário para armazenar as informações das peças por OS
    pecas_por_os = {}
    for os_id, valor_total_pecas, quantidade_total_pecas in pecas_data:
        pecas_por_os[os_id] = {
            "valor_total_pecas": valor_total_pecas,
            "quantidade_total_pecas": quantidade_total_pecas,
        }

    # Formatar os dados para o relatório
    headers = ["ID", "Cliente", "Data", "Descrição", "Valor", "Valor Peças", "Quantidade Peças"]
    data = []
    valor_total_os = 0
    quantidade_total_pecas = 0

    for row in os_data:
        os_id = row[0]  # Obtém o ID da OS
        valor_os = row[4]  # Obtém o valor da OS
        valor_total_os += valor_os

        # Obter informações de peças para a OS atual
        pecas_info = pecas_por_os.get(os_id, {"valor_total_pecas": 0, "quantidade_total_pecas": 0})

        # Adicionar informações de peças à linha da OS
        row = list(row) + [pecas_info["valor_total_pecas"], pecas_info["quantidade_total_pecas"]]

        data.append(row)
        quantidade_total_pecas += pecas_info["quantidade_total_pecas"]

    # Criar o relatório em PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Adicionar cabeçalho
    for header in headers:
        pdf.cell(30, 10, txt=header, border=1)
    pdf.ln()

    # Adicionar dados das OSs
    for row in data:
        for item in row:
            pdf.cell(30, 10, txt=str(item), border=1)
        pdf.ln()

    # Adicionar valor total das OSs e quantidade total de peças
    pdf.cell(30, 10, txt="Valor Total:", border=1)
    pdf.cell(30, 10, txt=str(valor_total_os), border=1)
    pdf.ln()
    pdf.cell(30, 10, txt="Qtd. Total Peças:", border=1)
    pdf.cell(30, 10, txt=str(quantidade_total_pecas), border=1)
    pdf.ln()

    # Salvar o relatório
    pdf.output("relatorio_os.pdf")

    # Exibir mensagem de sucesso
    self.snackbar = ft.SnackBar(ft.Text("Relatório de OSs gerado com sucesso!"))
    self.snackbar.open = True
    self.page.update()

    self.fechar_modal(e)

def gerar_relatorio_estoque(self, e):
        """Gera um PDF do estoque."""
        # Implementar lógica para gerar relatório de estoque aqui
        print("Gerar relatório de estoque...")
        self.fechar_modal(e)

def abrir_modal_os_por_cliente(self, e):
        """Abre o modal para selecionar as OSs por cliente."""
        # Implementar lógica para exibir e selecionar OSs por cliente aqui
        print("Abrir modal de OSs por cliente...")
        self.fechar_modal(e)    
