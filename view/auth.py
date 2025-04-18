import jwt
import os
from flask import session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from source.dbmanager import DatabaseClient
from source.pp import ConfigLoader
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from log.log import general_logger

class AuthService:
    def __init__(self):
        # Carrega as configurações do arquivo config.ini
        self.config = ConfigLoader()
        
        # Inicializa os parâmetros do DatabaseClient
        self.db_params = {
            "dbname": self.config.get('database', 'dbname'),
            "user": self.config.get('database', 'user'),
            "password": self.config.get('database', 'password'),
            "host": self.config.get('database', 'host'),
            "port": int(self.config.get('database', 'port'))
        }
        
        # Chave secreta para JWT
        self.jwt_secret = os.environ.get('JWT_SECRET', 'secret_key')  # Alterar em produção
        self.jwt_algorithm = 'HS256'
        self.token_expiry_minutes = 30

    @contextmanager
    def get_db_connection(self):
        """
        Gerenciador de contexto para conexões com o banco.
        Garante que as conexões sejam abertas e fechadas corretamente.
        """
        db_client = DatabaseClient(**self.db_params)
        try:
            db_client.connect()
            yield db_client
        finally:
            db_client.close()

    def login_user(self, username, password):
        """
        Autentica um usuário e retorna um token JWT se o login for bem-sucedido.
        """
        try:
            with self.get_db_connection() as db_client:
                query = 'SELECT id, password_hash FROM neouser WHERE username = %s'
                db_client.cursor.execute(query, (username,))
                user = db_client.cursor.fetchone()

            if user and check_password_hash(user[1], password):
                user_id = user[0]
                token = self._generate_jwt(user_id)

                # Armazena o token na sessão
                session['user_token'] = token

                flash("Login successful!", "success")
                return {"token": token}

            # Retorno em caso de falha
            return {"error": "Usuário ou senha incorretos"}

        except Exception as e:
            # Loga o erro e retorna um erro padrão
            print(f"Erro no login_user: {e}")
            return {"error": "Erro no login"}

    def register_user(self, username, password):
        """
        Registra um novo usuário no banco de dados.
        """
        password_hash = generate_password_hash(password)

        try:
            with self.get_db_connection() as db_client:
                query = "INSERT INTO neouser (username, password_hash) VALUES (%s, %s)"
                db_client.cursor.execute(query, (username, password_hash))
                db_client.conn.commit()
                flash("User registered successfully!", "success")
                return True

        except Exception as e:
            print(f"Registration Error: {e}")  # Log do erro para depuração
            flash(f"Error registering user: {str(e)}", "error")
            return False

    def _generate_jwt(self, user_id):
        now = datetime.now(timezone.utc)  # Garante que o horário é UTC
        expiry = now + timedelta(minutes=self.token_expiry_minutes)

        payload = {
            "user_id": user_id,
            "exp": expiry,
            "iat": now
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token

    def validate_token(self, token):
        """
        Valida um token JWT e retorna o user_id se válido.
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm], options={"require": ["exp", "iat"]})
            return payload["user_id"]

        except jwt.ExpiredSignatureError:
            print("Token has expired.")  # Log para depuração
            return None

        except jwt.InvalidTokenError as e:
            print(f"Invalid token: {str(e)}")  # Log para depuração
            return None
