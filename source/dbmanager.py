import psycopg
#from psycopg.extras import RealDictCursor

class DatabaseClient:
    def __init__(self, dbname, user, password, host, port=5432):
        """
        Inicializa a conexão com o banco de dados.
        """
        self.connection_params = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port
        }
        self.conn = None
        self.cursor = None

    def connect(self):
        """
        Conecta ao banco de dados usando os parâmetros fornecidos.
        """
        try:
            self.conn = psycopg.connect(**self.connection_params)
            self.cursor = self.conn.cursor()
            print("Conexão com o banco de dados estabelecida.")
        except Exception as e:
            print("Erro ao conectar ao banco de dados:", e)

    def close(self):
        """
        Fecha a conexão com o banco de dados.
        """
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("Conexão com o banco de dados fechada.")

    def fetch_data(self, query, params=None):
        """
        Executa uma consulta SQL e retorna os resultados.
        """
        try:
            self.connect()
            self.cursor.execute(query, params)
            results = self.cursor.fetchall()
            return results
        except Exception as e:
            print("Erro ao buscar dados:", e)
        finally:
            self.close()

    def insert_data(self, query, params):
        """
        Executa uma inserção ou atualização no banco de dados.
        """
        try:
            self.connect()
            self.cursor.execute(query, params)
            self.conn.commit()
            print("Dados inseridos/atualizados com sucesso.")
        except Exception as e:
            print("Erro ao inserir dados:", e)
        finally:
            self.close()
