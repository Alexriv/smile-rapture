from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from flask_htmx import HTMX

from config import Config

socketio = SocketIO()
htmx = HTMX()


def create_app(config_class=Config):
    app = Flask(__name__, template_folder='templates/', static_folder='static/')
    app.config.from_object(config_class)

    # Initialize bcrypt for authentication
    from app.services.auth import bcrypt
    bcrypt.init_app(app)

    # Initialize SocketIO and HTMX
    socketio.init_app(app)
    htmx.init_app(app)

    # Register API blueprint
    from app.routes.api.experiment import exp_delete
    from app.routes.api import bp as api_bp
    app.register_blueprint(api_bp)

    # Register auth blueprint
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    # Register main blueprint
    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)

    # Register admin blueprint
    from app.routes.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    # Add context processors
    from app.context_processor import utility_processor, inject_current_app
    app.context_processor(utility_processor)
    app.context_processor(inject_current_app)

    # Ensure admin user exists
    from app.services.auth import check_and_create_admin
    check_and_create_admin()

    # Load nodes from the database
    from app.services.node import load_nodes_from_db
    try:
        load_nodes_from_db()
    except Exception as E:
        print(f"Failed to load nodes from db: {E}")

    # Load experiment queue from the database
    from app.services.experiments import load_experiment_queue_from_db
    try:
        load_experiment_queue_from_db()
    except Exception as E:
        print(f"Failed to load experiment queue from db: {E}")

    # Add a route to serve assignments from external path
    @app.route('/assignments/<path:filename>')
    def serve_assignments(filename):
        assignments_directory = r"C:\Users\alexr\OneDrive\Documents\GitHub\smile-rapture\assignments"
        return send_from_directory(assignments_directory, filename)

    # SocketIO imports
    from app.routes.api.node import update_node_type, exp_status_request, start_exp_press

    return app


from app import models
