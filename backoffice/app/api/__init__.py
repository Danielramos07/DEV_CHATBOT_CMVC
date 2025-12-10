from flask import Blueprint
from .respostas import app as respostas_bp
from .chatbots import app as chatbots_bp
from .faqs import app as faqs_bp
from .categorias import app as categorias_bp
from .uploads import app as uploads_bp
from .stt_vosk_api import app as stt_vosk_bp

# Criar um blueprint principal para a API
api = Blueprint('api', __name__)

# Registar todos os sub-blueprints
api.register_blueprint(respostas_bp)
api.register_blueprint(chatbots_bp)
api.register_blueprint(faqs_bp)
api.register_blueprint(categorias_bp)
api.register_blueprint(uploads_bp)
api.register_blueprint(stt_vosk_bp)

