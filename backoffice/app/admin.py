from flask import Blueprint, render_template
from .auth import login_required

app = Blueprint('admin', __name__)

@app.route("/")
@login_required
def index():
    return render_template("recursos.html")

@app.route("/contexto")
@login_required
def contexto():
    return render_template("contexto.html")

@app.route("/landing")
def landing():
    return render_template("landing.html")

@app.route("/landing-2")
def landing_2():
    return render_template("landing-2.html")

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
