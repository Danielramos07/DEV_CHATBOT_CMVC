from flask import Flask
from flask_cors import CORS
import logging
from .config import Config
from .db import init_pool, close_conn
from .auth import app as auth
from .admin import app as admin
from .api import app as api

def create_app():
    logging.basicConfig(level=logging.DEBUG)
    app = Flask(__name__)   
    app.config.from_object(Config)

    #Cookies and Cors

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=True
    )

    CORS(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}})

    init_pool(app)

    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(api)

    @app.teardown_appcontext
    def close_db(error):
        close_conn()
    
    return app