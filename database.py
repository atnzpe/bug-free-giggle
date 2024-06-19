import bcrypt
import sqlite3
import os
import flet as ft
import queue
from datetime import datetime

# BANCO DE DADOS E FILA
nome_banco_de_dados = "c:/big/data/oficina_guarulhos.db"
# nome_banco_de_dados = "./data/oficina_guarulhosTeste.db"
# nome_banco_de_dados = "./data/oficina_guarulhosProdução.db"

# Fila para operações do banco de dados
fila_db = queue.Queue()

# Versão do banco de dados
VERSAO_BANCO_DE_DADOS = "1.0"  # Defina a versão do banco de dados aqui

# FUNÇÕES DE BANCO DE DADOS


def criar_conexao(banco_de_dados):
    """
    Cria uma conexão com o banco de dados SQLite.
    Se o banco de dados não existir, ele será criado.
    """

    banco_existe = os.path.exists(banco_de_dados)
    conexao = None
    try:
        conexao = sqlite3.connect(banco_de_dados)
        if not banco_existe:
            criar_tabelas(conexao)
            print("Banco de dados e tabelas criados com sucesso!")
        else:
            print("Conexão com o banco de dados estabelecida com sucesso!")
    except sqlite3.Error as erro:
        print(f"Erro ao conectar ao banco de dados: {erro}")
    return conexao


def executar_sql(conexao, sql, parametros=None):
    """Executa uma consulta SQL na conexão fornecida."""
    try:
        cursor = conexao.cursor()
        if parametros:
            cursor.execute(sql, parametros)
        else:
            cursor.execute(sql)
        conexao.commit()
        print("Consulta SQL executada com sucesso!")
    except sqlite3.Error as e:
        print(f"Erro ao executar consulta SQL: {e}")


def criar_usuario_admin(conexao):
    """Cria o usuário administrador 'admin' se ele não existir."""
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE nome = 'admin'")
    usuario_admin_existe = cursor.fetchone()

    if not usuario_admin_existe:
        senha_hash = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()
        cursor.execute(
            "INSERT INTO usuarios (nome, senha) VALUES (?, ?)", ("admin", senha_hash)
        )
        conexao.commit()
        print('Usuário "admin" criado com sucesso!')


def criar_tabelas(conexao):
    """Cria as tabelas do banco de dados."""
    cursor = conexao.cursor()

    # --- USUARIOS ---
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        )
        """
    )
    print("Tabela 'usuarios' criada!")

    # --- CLIENTES ---
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            telefone TEXT,
            endereco TEXT,
            email TEXT
        )
        """
    )
    print("Tabela 'clientes' criada!")

    # --- CARROS ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS carros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        modelo TEXT NOT NULL,
        ano INTEGER,
        cor TEXT,
        placa TEXT NOT NULL UNIQUE,
        cliente_id INTEGER,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)            
        )
        """
    )
    print("Tabela 'carros' criada!")

    # --- CLIENTES_CARROS ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS clientes_carros (
        cliente_id INTEGER,
        carro_id INTEGER,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id),
        FOREIGN KEY (carro_id) REFERENCES carros(id),
        PRIMARY KEY (cliente_id, carro_id)
        )
        """
    )
    print("Tabela 'clientes_carros' criada!")

    # --- MOVIMENTACAO_PECAS ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS movimentacao_pecas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peca_id INTEGER NOT NULL,
        data_movimentacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        tipo_movimentacao TEXT NOT NULL CHECK (tipo_movimentacao IN ('entrada', 'saida')),
        quantidade INTEGER NOT NULL,
        ordem_servico_id INTEGER, 
        FOREIGN KEY (peca_id) REFERENCES pecas(id),
        FOREIGN KEY (ordem_servico_id) REFERENCES ordem_servico(id)
    )
    """
    )
    print("Tabela 'movimentacao_pecas' criada!")

    # --- SERVICOS ---
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
        carro_id INTEGER NOT NULL,
        valor_total REAL,
        FOREIGN KEY (carro_id) REFERENCES carros(id)
        )
        """
    )
    print("Tabela 'servicos' criada!")

    # --- PECAS_UTILIZADAS ---
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pecas_utilizadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servico_id INTEGER NOT NULL,
            peca_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            valor_unitario REAL NOT NULL,
            FOREIGN KEY (servico_id) REFERENCES servicos(id),
            FOREIGN KEY (peca_id) REFERENCES pecas(id)
);
        """
    )
    print("Tabela 'pecas_utilizadas' criada!")

    # --- PECAS ---
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pecas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            referencia TEXT NOT NULL,
            fabricante TEXT,
            descricao TEXT,
            preco_compra REAL NOT NULL,
            preco_venda REAL NOT NULL,
            quantidade_em_estoque INTEGER NOT NULL CHECK (quantidade_em_estoque >= 0)
        )
        """
    )
    print("Tabela 'pecas' criada!")

    # --- ORDEM_SERVICO ---
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ordem_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            carro_id INTEGER NOT NULL,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            valor_total REAL NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (carro_id) REFERENCES carros(id)
        )
        """
    )
    print("Tabela 'ordem_servico' criada!")

    # --- PecasOrdemServico ---
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS PecasOrdemServico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ordem_servico_id INTEGER,
            peca_id INTEGER,
            quantidade INTEGER NOT NULL,
            FOREIGN KEY (ordem_servico_id) REFERENCES OrdensDeServico (id),
            FOREIGN KEY (peca_id) REFERENCES Pecas (id)
        )
        """
    )
    print("Tabela 'PecasOrdemServico' criada!")

    criar_usuario_admin(conexao)
    print("Tabelas criadas com sucesso!")


def inserir_dados_iniciais(conexao):
    cursor = conexao.cursor()

    # Inserir clientes
    cursor.execute("INSERT INTO clientes (nome) VALUES ('João Silva')")
    cursor.execute("INSERT INTO clientes (nome) VALUES ('Maria Oliveira')")

    # Inserir carros
    cursor.execute("INSERT INTO carros (cliente_id, modelo, placa) VALUES (1, 'Carro do batman' 'ABC-1234')")
    cursor.execute("INSERT INTO carros (cliente_id, modelo, placa) VALUES (2, 'Motoloca','DEF-5678')")

    # Inserir peças
    cursor.execute(
        "INSERT INTO pecas (nome, preco_compra, preco_venda, quantidade_em_estoque) VALUES ('Teste 1r', 50.00, 60.00, 100)"
    )
    cursor.execute(
        "INSERT INTO pecas (nome, preco_compra, preco_venda, quantidade_em_estoque) VALUES ('Teste 2', 20.00, 30.00, 50)"
    )
    cursor.execute(
        "INSERT INTO pecas (nome, preco_compra, preco_venda, quantidade_em_estoque) VALUES ('Teste3', 80.00, 90.00, 30)"
    )

    conexao.commit()
    print("Dados iniciais inseridos com sucesso!")


def obter_clientes(conexao):
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM clientes")
    return cursor.fetchall()


def obter_carros_por_cliente(conexao, cliente_id):
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM carros WHERE cliente_id = ?", (cliente_id,))
    return cursor.fetchall()


def obter_pecas(conexao):
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM pecas")
    return cursor.fetchall()


def inserir_ordem_servico(
    conexao, cliente_id, carro_id, pecas_quantidades, valor_total, mao_de_obra=0.00
):
    """
    Insere uma nova ordem de serviço no banco de dados.

    Args:
        conexao: A conexão com o banco de dados SQLite.
        cliente_id (int): O ID do cliente.
        carro_id (int): O ID do carro.
        pecas_quantidades (dict): Um dicionário com o ID da peça como chave
                                e a quantidade como valor.
        valor_total (float):  O valor total da ordem de serviço.
        mao_de_obra (float, optional): O valor da mão de obra. Defaults to 0.00.
    """
    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            INSERT INTO OrdensDeServico (cliente_id, carro_id, data_criacao, valor_total, mao_de_obra)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                cliente_id,
                carro_id,
                datetime.now(),
                valor_total,
                mao_de_obra,
            ),
        )
        conexao.commit()

        ordem_servico_id = cursor.lastrowid

        for peca_id, quantidade in pecas_quantidades.items():
            cursor.execute(
                """
                INSERT INTO OrdensDeServico_Pecas (os_id, peca_id, quantidade)
                VALUES (?, ?, ?)
                """,
                (ordem_servico_id, peca_id, quantidade),
            )
        conexao.commit()
        return ordem_servico_id
    except sqlite3.Error as e:
        print(f"Erro ao inserir ordem de serviço: {e}")
        conexao.rollback()
        return None


# Atualiza o estoque da peça.
def atualizar_estoque_peca(conexao, peca_id, quantidade_utilizada):
    """Atualiza o estoque da peça."""
    try:
        print(
            f"Atualizando estoque da peça {peca_id}. Quantidade utilizada: {quantidade_utilizada}"
        )
        cursor = conexao.cursor()
        cursor.execute(
            """
            UPDATE pecas
            SET quantidade_em_estoque = quantidade_em_estoque - ? 
            WHERE id = ?
            """,
            (quantidade_utilizada, peca_id),
        )
        conexao.commit()
    except Exception as e:
        print(f"Erro em atualizar_estoque_peca: {e}")


def atualizar_carro(carro_id, cliente_id, conexao=None):
    """
    Atualiza o dono de um carro no banco de dados.

    Args:
        carro_id (int): O ID do carro a ser atualizado.
        cliente_id (int): O ID do novo dono do carro.
        conexao (opcional): Uma conexão existente com o banco de dados.
        Se None, uma nova conexão será criada e fechada dentro da função.

    Returns:
        bool: True se a atualização for bem-sucedida, False caso contrário.
    """
    fechar_conexao = False
    if conexao is None:
        conexao = criar_conexao(nome_banco_de_dados)
        fechar_conexao = True

    try:
        cursor = conexao.cursor()
        cursor.execute(
            "UPDATE carros SET cliente_id = ? WHERE id = ?", (cliente_id, carro_id)
        )
        conexao.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar o carro no banco de dados: {e}")
        return False
    finally:
        if fechar_conexao:
            conexao.close()


def quantidade_em_estoque_suficiente(conexao, peca_id, quantidade_necessaria):
    """Verifica se a quantidade em estoque é suficiente para a peça."""
    try:
        print(
            f"Verificando estoque da peça {peca_id}. Quantidade necessária: {quantidade_necessaria}"
        )
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT quantidade_em_estoque FROM pecas WHERE id = ?", (peca_id,)
        )
        resultado = cursor.fetchone()

        if resultado is None:
            print(f"ERRO: Peça com ID {peca_id} não encontrada na tabela 'pecas'.")
            return False

        quantidade_em_estoque = resultado[0]
        print(f"Quantidade em estoque: {quantidade_em_estoque}")
        return quantidade_em_estoque >= quantidade_necessaria

    except Exception as e:
        print(f"Erro em quantidade_em_estoque_suficiente: {e}")
        return False


def inserir_movimentacao_peca(
    conexao, peca_id, tipo_movimentacao, quantidade, ordem_servico_id
):
    """Insere uma nova movimentação de peça no banco de dados."""
    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            INSERT INTO movimentacao_pecas (peca_id, tipo_movimentacao, quantidade, ordem_servico_id)
            VALUES (?, ?, ?, ?)
            """,
            (peca_id, tipo_movimentacao, quantidade, ordem_servico_id),
        )
        conexao.commit()
    except Exception as e:
        print(f"Erro em inserir_movimentacao_peca: {e}")


if __name__ == "__main__":
    conexao = criar_conexao(nome_banco_de_dados)
    if conexao is not None:
        criar_tabelas(conexao)
        inserir_dados_iniciais(conexao)
        conexao.close()
