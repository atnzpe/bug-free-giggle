import bcrypt
import sqlite3
import os
import flet as ft
import queue

# BANCO DE DADAS E FILA
# nome_banco_de_dados = "./data/oficina_guarulhos.db"
# nome_banco_de_dados = "./data/oficina_guarulhosTeste.db"
# nome_banco_de_dados = "./data/oficina_guarulhosProdução.db"


# Fila para operações do banco de dados
fila_db = queue.Queue()
# versao1.0


# Cria conexão com o Banco de Dados Sqlite3 e cria as tabelas
def criar_conexao(banco_de_dados):
    """
    Cria uma conexão com o banco de dados SQLite.
    Se o banco de dados não existir, ele será criado.
    """

    banco_existe = os.path.exists(
        banco_de_dados
    )  # Verifica se o arquivo do banco existe

    conexao = None
    try:
        conexao = sqlite3.connect(banco_de_dados)
        if not banco_existe:
            criar_tabelas(conexao)  # Cria as tabelas se o banco for novo
            print("Banco de dados e tabelas criados com sucesso!")
        # else:
        # print("Amor com o banco de dados estabelecida com sucesso!")
    except sqlite3.Error as erro:
        print(f"Erro ao conectar ao banco de dados: {erro}")
    return conexao


# conexao_db = criar_conexao(nome_banco_de_dados)
# conexao = criar_conexao(nome_banco_de_dados)
# Fila para operações do banco de dados
fila_db = queue.Queue()
# versao1.0


# Executa uma consulta SQL na conexão fornecida
def executar_sql(conexao, sql, parametros=None):
    """Executa uma consulta SQL na conexão fornecida.

    Args:
        conexao (sqlite3.Connection): Objeto de conexão com o banco de dados.
        sql (str): A instrução SQL a ser executada.
        parametros (tuple, optional): Uma tupla contendo os parâmetros para a consulta SQL (se houver).
    """
    try:
        cursor = conexao.cursor()
        if parametros:
            cursor.execute(sql, parametros)
        else:
            cursor.execute(sql)
        conexao.commit()  # Confirma (commit) as alterações no banco de dados
        print("Consulta SQL executada com sucesso!")
    except sqlite3.Error as e:
        print(f"Erro ao executar consulta SQL: {e}")


# Cria conexão com o Banco de Dados Sqlite3 e cria as tabelas


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

    # Criar tabela de usuários
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,  -- Nome de usuário deve ser único
            senha TEXT NOT NULL
        )
        """
    )
    print("Usuarios criada!")

    # Cria a tabela clientes
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE, -- Nome do cliente deve ser único
            telefone TEXT,
            endereco TEXT,
            email TEXT
        )
        """
    )
    print("Tabela cliente criada com sucesso!")

    # Cria a tabela carros com cliente_id como chave estrangeira
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS carros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        modelo TEXT NOT NULL,
        ano INTEGER,
        cor TEXT,
        placa TEXT NOT NULL UNIQUE, -- Placa do veículo deve ser única
        cliente_id INTEGER,         -- Define a relação com a tabela 'clientes'
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)            
        )
        """
    )
    print("Tabela carros criada com sucesso!")
    # Crie as outras tabelas (carros, peças, usuários, etc.) aqui

    # Cria a tabela clientes_carros
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
    print("Tabela clientes_carros criada com sucesso!")

    # movimentacao_pecas
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS movimentacao_pecas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peca_id INTEGER NOT NULL,
        data_movimentacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        tipo_movimentacao TEXT NOT NULL CHECK (tipo_movimentacao IN ('entrada', 'saida')),
        quantidade INTEGER NOT NULL,
        ordem_servico_id INTEGER, -- Agora é opcional (pode ser NULL) 
        FOREIGN KEY (peca_id) REFERENCES pecas(id),
        FOREIGN KEY (ordem_servico_id) REFERENCES ordem_servico(id) -- Esta restrição ainda é válida
    )
    """
    )
    print("movimentacao_pecas criada!")

    # Cria a Tabela Serviços
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
    print("Cria Tabela Seriços!")

    # Cria Tabela Peças Utilizadas
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pecas_utilizadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servico_id INTEGER NOT NULL,
            peca_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            valor_unitario REAL NOT NULL,  -- Valor unitário da peça no momento do serviço
            FOREIGN KEY (servico_id) REFERENCES servicos(id),
            FOREIGN KEY (peca_id) REFERENCES pecas(id)
);
        """
    )

    # Cria a tabela peças
    cursor = conexao.cursor()
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
    print("Tabela pecas criada com sucesso!")

    # Cria a Tabela Ordem de Serviço
    cursor = conexao.cursor()
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
    print("Tabela ordem_servico criada com sucesso!")

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
    print("Tabelas criadas com sucesso!")

    criar_usuario_admin(conexao)

    # Verificar se o usuário "admin" já existe
    cursor.execute("SELECT * FROM usuarios WHERE nome = 'admin'")
    usuario_admin_existe = cursor.fetchone()

    # ================================


def inserir_dados_iniciais(conexao):
    cursor = conexao.cursor()

    # Inserir clientes
    cursor.execute("INSERT INTO clientes (nome) VALUES ('João Silva')")
    cursor.execute("INSERT INTO clientes (nome) VALUES ('Maria Oliveira')")

    # Inserir carros
    cursor.execute("INSERT INTO carros (cliente_id, placa) VALUES (1, 'ABC-1234')")
    cursor.execute("INSERT INTO carros (cliente_id, placa) VALUES (2, 'DEF-5678')")

    # Inserir peças
    cursor.execute(
        "INSERT INTO pecas (nome, preco_unitario, quantidade_em_estoque) VALUES ('Teste 1r', 50.00, 100)"
    )
    cursor.execute(
        "INSERT INTO pecas (nome, preco_unitario, quantidade_em_estoque) VALUES ('Teste 2', 20.00, 50)"
    )
    cursor.execute(
        "INSERT INTO pecas (nome, preco_unitario, quantidade_em_estoque) VALUES ('Teste3', 80.00, 30)"
    )

    conexao.commit()
    print("Dados iniciais inseridos com sucesso!")


def obter_clientes(conexao):
    conexao = criar_conexao(nome_banco_de_dados)
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


def inserir_ordem_servico(conexao, cliente_id, carro_id, pecas_quantidades):
    """
    Insere uma nova ordem de serviço no banco de dados.

    Args:
        conexao: A conexão com o banco de dados.
        cliente_id: O ID do cliente.
        carro_id: O ID do carro.
        pecas_quantidades: Um dicionário onde as chaves são os IDs das peças
        e os valores são as quantidades.
    """
    try:
        print(
            "Peças e quantidades recebidas em inserir_ordem_servico:", pecas_quantidades
        )
        cursor = conexao.cursor()
        cursor.execute(
            """
            INSERT INTO ordem_servico (cliente_id, carro_id)
            VALUES (?, ?)
            """,
            (cliente_id, carro_id),
        )
        ordem_servico_id = cursor.lastrowid

        # Inserir peças na tabela PecasOrdemServico
        for peca_id, quantidade in pecas_quantidades.items():
            print(
                f"Inserindo peça {peca_id} com quantidade {quantidade} na OS {ordem_servico_id}"
            )
            cursor.execute(
                """
                INSERT INTO PecasOrdemServico (ordem_servico_id, peca_id, quantidade)
                VALUES (?, ?, ?)
                """,
                (ordem_servico_id, peca_id, quantidade),
            )
        conexao.commit()
        return ordem_servico_id

    except Exception as e:
        print(f"Erro em inserir_ordem_servico: {e}")
        return None

#Atualiza o estoque da peça.
def atualizar_estoque_peca(conexao, peca_id, quantidade_utilizada):
    try:
        print(f"Atualizando estoque da peça {peca_id}. Quantidade utilizada: {quantidade_utilizada}")
        cursor = conexao.cursor()
        cursor.execute(
            """
            UPDATE pecas
            SET quantidade_em_estoque = quantidade_em_estoque + ?
            WHERE id = ?
            """,
            (quantidade_utilizada, peca_id),
        )
        conexao.commit()
    except Exception as e:
        print(f"Erro em atualizar_estoque_peca: {e}")


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


if __name__ == "__main__":
    conexao = criar_conexao("./data/oficina_guarulhos.db")
    if conexao is not None:
        criar_tabelas(conexao)
        inserir_dados_iniciais(conexao)
        conexao.close()

# BANCO DE DADAS E FILA
nome_banco_de_dados = "./data/oficina_guarulhos.db"
# nome_banco_de_dados = "./data/oficina_guarulhosTeste.db"
# nome_banco_de_dados = "./data/oficina_guarulhosProdução.db"

conexao_db = criar_conexao(nome_banco_de_dados)
# Fila para operações do banco de dados
fila_db = queue.Queue()
# versao1.0
