from flask import Flask
from flask_cors import CORS
import logging
import os
from .config import Config
from .db import init_pool, close_conn, ensure_schema
from .auth import app as auth
from .admin import app as admin
from .api import api

def create_app():
    logging.basicConfig(level=logging.DEBUG)
    app = Flask(__name__)   
    app.config.from_object(Config)

    # Optional: path to the Vosk model used by the STT service.
    # By default we expect the model under backoffice/app/extras/models.
    default_vosk_path = os.path.join("extras", "models", "vosk-model-small-pt-0.3")
    app.config.setdefault("VOSK_MODEL_PATH", default_vosk_path)

    # Cookies and CORS
    # NOTE: SESSION_COOKIE_SECURE=True breaks login over plain http://localhost.
    # Default to secure cookies only in non-dev environments, or allow override via env.
    secure_env = os.getenv("SESSION_COOKIE_SECURE", "").strip().lower()
    if secure_env:
        cookie_secure = secure_env in {"1", "true", "yes", "on"}
    else:
        # flask run --debug sets FLASK_DEBUG=1 (and app.debug may still be False at create_app time)
        is_debug = (
            os.getenv("FLASK_DEBUG", "").strip() == "1"
            or os.getenv("DEBUG", "").strip() == "1"
            or os.getenv("FLASK_ENV", "").lower() in {"development", "dev"}
            or bool(app.debug)
        )
        cookie_secure = not is_debug

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,
    )

    CORS(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}})

    init_pool(app)
    # Best-effort schema updates for runtime features (safe to run repeatedly)
    ensure_schema()

    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(api)

    @app.teardown_appcontext
    def close_db(error):
        close_conn()
    
    return app