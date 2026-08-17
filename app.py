from flask import Flask
from config import Config
from routes.main import main_bp


def create_app():
    """Application factory for FaceAttend."""
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(main_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=app.config["DEBUG"],
    )
