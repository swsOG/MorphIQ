from flask import Flask

from .routes import api_bp, ui_bp


def create_app():
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )
    app.register_blueprint(api_bp)
    app.register_blueprint(ui_bp)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
