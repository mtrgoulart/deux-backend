from flask import Flask


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = 'sua_chave_secreta'

    # Registra os blueprints
    from view.routes import main_bp
    app.register_blueprint(main_bp)

    

    return app
