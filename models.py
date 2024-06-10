import bcrypt
import sqlite3

from database import criar_conexao, nome_banco_de_dados






class Oficina:
    """
    Representa uma oficina mecânica,
    gerenciando clientes, carros e peças.

    Atributos:
        usuarios (list): Uma lista de objetos Usuario o usuario que esta logado na aplicação.
        clientes (list): Uma lista de objetos Cliente representando os clientes da oficina.
        carros (list): Uma lista de objetos Carro representando os carros associados aos clientes.
        pecas (list): Uma lista de objetos Peça representando as peças do estoque
    """

    def __init__(self):
        self.usuarios = []
        self.clientes = []
        self.carros = []
        self.pecas = []
        
        

    def criar_usuario(self, nome, senha):
        """ "
        Cria um novo usuário e o adiciona à lista de usuários da Aplicação.

        Args:
            nome (str): Nome do usuário.
            senha (str): Senha do usuário.

        Returns:
            usuario: O objeto usuario representando o usuário criado.

        Raises:
            ValueError: Se já existir um cliente com o mesmo Nome e Senha.
        """
        if self.obter_usuario_por_nome_e_senha(nome, senha):
            raise ValueError("Usuário já cadastrado com este Nome e Senha.")
        usuario = Usuario(nome, senha)
        self.usuarios.append(usuario)
        return usuario, senha

    def obter_usuario_por_nome_e_senha(self, nome, senha):
        """
        Busca um usuário pelo nome e senha.

        Args:
            nome (str): O Nome do usuário.
            senha (str): A senha do usuario

        Returns:
            Usuario: O objeto Usuario se encontrado, None caso contrário.
        """
        for usuario in self.usuarios:
            if usuario.nome == nome and bcrypt.checkpw(senha.encode(), usuario.senha):
                return usuario
        return None

    def cadastrar_cliente(self, nome, telefone, endereco, email):
        """
        Cadastra um novo cliente na oficina.

        Args:
            nome (str): Nome do cliente.
            telefone (str): Telefone do cliente.
            endereco (str): Endereço do cliente.
            email (str): Endereço de email do cliente.

        Returns:
            bool: True se o cadastro for realizado com sucesso, False caso contrário.
        """
        try:
            conexao_db = criar_conexao(nome_banco_de_dados)
            cursor = conexao_db.cursor()
            cursor.execute(
                "INSERT INTO clientes (nome, telefone, endereco, email) VALUES (?, ?, ?, ?)",
                (nome, telefone, endereco, email),
            )
            conexao_db.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def obter_cliente_por_nome(self, nome):
        """
        Busca um cliente pelo nome.

        Args:
            nome (str): O nome do cliente.

        Returns:
            Cliente: O objeto Cliente se encontrado, None caso contrário.
        """
        conexao_db = criar_conexao(nome_banco_de_dados)
        cursor = conexao_db.cursor()
        cursor.execute("SELECT * FROM clientes WHERE nome=?", (nome,))
        cliente_data = cursor.fetchone()
        if cliente_data:
            return Cliente(*cliente_data[1:])  # Cria um objeto Cliente com os dados
        return None

    def atualizar_cliente(self, nome, telefone, email):
        """
        Atualiza os dados de um cliente existente.

        Args:
            nome (str): Nome do cliente.
            telefone (str): Novo telefone do cliente.
            email (str): Novo email do cliente.

        Returns:
            bool: True se a atualização for realizada com sucesso, False caso contrário.
        """
        try:
            conexao_db = criar_conexao(nome_banco_de_dados)
            cursor = conexao_db.cursor()
            cursor.execute(
                "UPDATE clientes SET telefone=?, email=? WHERE nome=?",
                (telefone, email, nome),
            )
            conexao_db.commit()
            return True
        except Exception as e:
            print(f"Erro ao atualizar cliente: {e}")
            return False

    def cadastrar_carro(self, modelo, ano, cor, placa, cliente_id):
        """
        Cadastra um novo carro na oficina, associado a um cliente.

        Args:
            modelo (str): Modelo do carro.
            ano (int): Ano de fabricação do carro.
            cor (str): Cor do carro.
            placa (str): Placa do carro.
            cliente_id (int): ID do cliente ao qual o carro pertence.

        Returns:
            bool: True se o cadastro for realizado com sucesso, False caso contrário.
        """
        try:
            conexao_db = criar_conexao(nome_banco_de_dados)
            cursor = conexao_db.cursor()
            cursor.execute(
                "INSERT INTO carros (modelo, ano, cor, placa, cliente_id) VALUES (?, ?, ?, ?, ?)",
                (modelo, ano, cor, placa, cliente_id),
            )
            conexao_db.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def pesquisar_clientes(self, termo):
        """
        Busca clientes por nome, telefone ou placa do carro.

        Args:
            termo (str): O termo a ser pesquisado.

        Returns:
            list: Uma lista de objetos Cliente que correspondem à pesquisa.
        """
        conexao_db = criar_conexao(nome_banco_de_dados)
        cursor = conexao_db.cursor()
        cursor.execute(
            """
            SELECT DISTINCT c.* 
            FROM clientes c
            LEFT JOIN clientes_carros cc ON c.id = cc.cliente_id
            LEFT JOIN carros car ON cc.carro_id = car.id
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
            cliente = Cliente(*resultado)
            clientes.append(cliente)
        return clientes

class Cliente:
    """
    Representa um Cliente com seus dados pessoais.

    Atributos:
        nome (str): Nome do Cliente.
        telefone (str): Telefone do Cliente.
        endereco (str): Endereço do Cliente.
        email (str): Endereço de email do cliente.
    """

    def __init__(self, id, nome: str, telefone: str, endereco: str, email: str):
        self.id = id
        self.nome = nome
        self.telefone = telefone
        self.endereco = endereco
        self.email = email

        self.carros = []  # lista para armazenar os carros do cliente

    def adicionar_carro(self, carro):
        """Adiciona um carro à lista de carros do cliente."""
        if carro not in self.carros:
            self.carros.append(carro)

    


class Carro:
    """
    Representa o Carro de um Cliente e suas caracteristicas.

    Atributos:
        modelo (str)`: Ex: "Gol", "Uno", "HB20"...
        ano (int)`: Ano de fabricação.
        cor (str): Cor do Veículo.
        placa (str)`: Placa do veículo.
        cliente (Cliente)`: Referência ao objeto Cliente dono do carro.
    """

    def __init__(self, modelo: str, ano: int, cor: str, placa: str, cliente):
        self.modelo = modelo
        self.ano = ano
        self.cor = cor
        self.placa = placa
        self.cliente = cliente


class Peca:
    """
    Representa a Peças usada no Carro e suas caracteristicas.

    Atributos:
    Nome (str)`: Ex: "Pastilha de Freio", "Filtro de Óleo"...
    referencia (str): Referencia ex: SH 6058
    Fabricante (str): Fabricante da Peça
    descricao (str)`: Descrição detalhada da peça (opcional).
    preco_compra (float)`: Preço unitário da peça.
    preco_revenda (float): Preço de Venda
    quantidade_em_estoque (int)`: Quantidade disponível.
    """

    def __init__(
        self,
        nome: str,
        referencia: str,
        fabricante: str,
        descricao: str,
        preco_compra: float,
        preco_revenda: float,
        quantidade_em_estoque: int,
    ):
        self.nome = nome
        self.referencia = referencia
        self.fabricante = fabricante
        self.descricao = descricao
        self.preco_compra = preco_compra
        self.preco_revenda = preco_revenda
        self.quantidade_em_estoque = quantidade_em_estoque


class Usuario:
    """
    Representa o Usuário da Aplicação  e suas caracteristicas.

    Atributos:
    Nome (str)`: Nome do usuário
    senha (str): Senha de Login
    Tipo (str): Adm ou funcionário
    """

    def __init__(self, nome: str, senha: str):
        self.nome = nome
        self.senha = self.gerar_hash_senha(senha)

    def autenticar(self, nome_de_usuario, senha_fornecida):
        """
        Verifica se as credenciais fornecidas são válidas.

        Args:
            nome_de_usuario (str): Nome de usuário para login.
            senha_fornecida (str): Senha fornecida pelo usuário.

        Returns:
            bool: True se as credenciais forem válidas, False caso contrário.
        """
        usuario = self.obter_usuario_por_nome(nome_de_usuario)
        if usuario and bcrypt.checkpw(senha_fornecida.encode(), usuario.senha):
            return True
        return False

    def gerar_hash_senha(self, senha):
        """
        Gera um hash da senha usando bcrypt.

        Args:
            senha (str): A senha a ser criptografada.

        Returns:
            bytes: O hash da senha.
        """
        salt = bcrypt.gensalt()
        hash_senha = bcrypt.hashpw(senha.encode(), salt)
        return hash_senha