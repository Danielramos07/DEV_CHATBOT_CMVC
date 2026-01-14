from flask import Blueprint, render_template
from .auth import login_required

app = Blueprint('admin', __name__)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/recursos")
@login_required
def index():
    return render_template("recursos.html")

@app.route("/contexto")
@login_required
def contexto():
    return render_template("contexto.html")

@app.route("/projeto")
def projeto():
    return render_template("projeto.html")

@app.route("/embed/chatbot/<int:chatbot_id>")
def embed_chatbot(chatbot_id):
    return render_template("embed_chatbot.html", chatbot_id=chatbot_id)

@app.route("/respostas")
@login_required
def respostas():
    return render_template("respostas.html")

@app.route("/nao-respondidas")
@login_required
def nao_respondidas():
    return render_template("nao-respondidas.html")

@app.route("/metricas")
@login_required
def metricas():
    return render_template("metricas.html")
