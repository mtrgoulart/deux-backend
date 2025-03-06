import psycopg
import os
from log.log import general_logger 

def load_query(filename):
    """
    Carrega o conteúdo de um arquivo SQL localizado no diretório 'queries' na raiz do projeto.
    """
    # Caminho absoluto para o diretório 'queries' na raiz do projeto
    queries_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'queries')
    filepath = os.path.join(queries_dir, filename)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Query file not found: {filepath}")

    with open(filepath, 'r') as file:
        return file.read()

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
        except Exception as e:
            general_logger.error("Erro ao conectar ao banco de dados:", e)

    def close(self):
        """
        Fecha a conexão com o banco de dados.
        """
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

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
            general_logger.error("Erro ao buscar dados:", e)
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
        except Exception as e:
            general_logger.error("Erro ao inserir dados:", e)
        finally:
            self.close()

    def delete_data(self, query, params):
            """
            Executa uma operação DELETE no banco de dados.
            """
            try:
                self.connect()
                self.cursor.execute(query, params)
                self.conn.commit()
                rows_affected = self.cursor.rowcount  # Retorna o número de linhas afetadas
                return rows_affected
            except Exception as e:
                general_logger.error("Erro ao deletar dados:", e)
                raise
            finally:
                self.close()

    def update_data(self, query, params):
        """
        Executa uma atualização no banco de dados.
        """
        try:
            self.connect()
            self.cursor.execute(query, params)
            self.conn.commit()
        except Exception as e:
            general_logger.error("Erro ao atualizar dados:", e)
        finally:
            self.close()

    def insert_data_returning(self, query, params):
        """
        Executa uma inserção no banco de dados com a cláusula RETURNING e retorna o valor.
        """
        try:
            self.connect()
            self.cursor.execute(query, params)
            result = self.cursor.fetchone()  # Obtém o primeiro valor retornado pelo RETURNING
            self.conn.commit()
            return result[0] if result else None
        except Exception as e:
            general_logger.error("Erro ao inserir dados com retorno:", e)
            raise
        finally:
            self.close()
    