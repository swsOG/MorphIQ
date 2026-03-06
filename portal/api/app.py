from flask import Flask

from .routes import api_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
