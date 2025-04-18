from flask import Flask, send_from_directory
import os
from view.routes import main_bp

def create_app():
    # Caminho até a pasta 'dist' fora da pasta backend
    dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist'))

    app = Flask(
        __name__,
        static_folder=dist_dir,
        static_url_path=''
    )

    app.secret_key = 'sua_chave_super_secreta_aqui'
    app.register_blueprint(main_bp)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react(path):
        file_path = os.path.join(app.static_folder, path)
        if path != "" and os.path.exists(file_path):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    @app.errorhandler(404)
    def not_found(e):
        return send_from_directory(app.static_folder, 'index.html')

    return app
