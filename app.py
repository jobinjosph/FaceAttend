from flask import Flask, render_template
import mysql.connector
from config import Config
from extensions import csrf
from routes.admin_students import admin_students_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.main import main_bp
from services.auth_service import register_auth_commands


def create_app(test_config=None):
    """Application factory for FaceAttend."""
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config is not None:
        app.config.update(test_config)

    csrf.init_app(app)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_students_bp)
    register_auth_commands(app)

    @app.errorhandler(mysql.connector.Error)
    def handle_database_error(error):
        app.logger.error("Unhandled database error: %s", error)
        return render_template("errors/database.html"), 503

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=app.config["DEBUG"],
    )
