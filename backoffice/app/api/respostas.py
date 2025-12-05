from flask import Blueprint, request, jsonify
from ..db import get_conn
from ..services.text import detectar_saudacao, registar_pergunta_nao_respondida
from ..services.retreival import obter_faq_mais_semelhante, pesquisar_faiss, build_faiss_index
from ..services.rag import pesquisar_pdf_ollama, get_pdfs_from_db, obter_mensagem_sem_resposta
import traceback

app = Blueprint('respostas', __name__)


@app.route("/obter-resposta", methods=["POST"])
def obter_resposta():
    conn = get_conn()
    cur = conn.cursor()
    dados = request.get_json()
    pergunta = dados.get("pergunta", "").strip()
    chatbot_id = dados.get("chatbot_id")
    fonte = dados.get("fonte", "faq")
    idioma = dados.get("idioma", "pt")
    feedback = dados.get("feedback", None)
    print("DEBUG /obter-resposta:", {
        "pergunta": pergunta,
        "chatbot_id": chatbot_id,
        "fonte": fonte,
        "feedback": feedback,
        "type_feedback": type(feedback)
    })
    try:
        chatbot_id = int(chatbot_id)
    except Exception:
        return jsonify({"success": False, "erro": "Chatbot ID inválido."}), 400
    saudacao = detectar_saudacao(pergunta)
    if saudacao:
        return jsonify({
            "success": True,
            "fonte": "SAUDACAO",
            "resposta": saudacao,
            "faq_id": None,
            "categoria_id": None,
            "pergunta_faq": None,
            "documentos": []
        })
    if not pergunta or (len(pergunta) < 4 and not any(char.isalpha() for char in pergunta)):
        return jsonify({
            "success": False,
            "erro": "Pergunta demasiado curta ou não reconhecida como válida."
        })
    if fonte == "faq+raga" and (feedback is None or feedback == "") and pergunta.lower() in ["sim", "yes"]:
        return jsonify({
            "success": False,
            "erro": "Por favor utilize os botões abaixo para confirmar.",
            "prompt_rag": True
        })
    try:
        if fonte == "faq":
            resultado = obter_faq_mais_semelhante(pergunta, chatbot_id)
            if resultado:
                cur.execute("""
                    SELECT faq_id, categoria_id FROM faq
                    WHERE LOWER(pergunta) = LOWER(%s) AND chatbot_id = %s
                """, (resultado["pergunta"], chatbot_id))
                row = cur.fetchone()
                faq_id, categoria_id = row if row else (None, None)
                cur.execute("SELECT link FROM faq_documento WHERE faq_id = %s", (faq_id,))
                docs = [r[0] for r in cur.fetchall()]
                return jsonify({
                    "success": True,
                    "fonte": "FAQ",
                    "resposta": resultado["resposta"],
                    "faq_id": faq_id,
                    "categoria_id": categoria_id,
                    "score": resultado["score"],
                    "pergunta_faq": resultado["pergunta"],
                    "documentos": docs
                })
            registar_pergunta_nao_respondida(chatbot_id, pergunta, "faq")
            return jsonify({
                "success": False,
                "erro": obter_mensagem_sem_resposta(chatbot_id)
            })
        elif fonte == "faiss":
            faiss_resultados = pesquisar_faiss(pergunta, chatbot_id=chatbot_id, k=1, min_sim=0.7)
            if faiss_resultados:
                faq_id = faiss_resultados[0]['faq_id']
                cur.execute("SELECT link FROM FAQ_Documento WHERE faq_id = %s", (faq_id,))
                docs = [r[0] for r in cur.fetchall()]
                return jsonify({
                    "success": True,
                    "fonte": "FAISS",
                    "resposta": faiss_resultados[0]['resposta'],
                    "faq_id": faq_id,
                    "score": faiss_resultados[0]['score'],
                    "pergunta_faq": faiss_resultados[0]['pergunta'],
                    "documentos": docs
                })
            else:
                resultado = obter_faq_mais_semelhante(pergunta, chatbot_id, threshold=80)
                if resultado:
                    cur.execute("""
                        SELECT faq_id, categoria_id FROM faq
                        WHERE LOWER(pergunta) = LOWER(%s) AND chatbot_id = %s
                    """, (resultado["pergunta"], chatbot_id))
                    row = cur.fetchone()
                    faq_id, categoria_id = row if row else (None, None)
                    cur.execute("SELECT link FROM faq_documento WHERE faq_id = %s", (faq_id,))
                    docs = [r[0] for r in cur.fetchall()]
                    return jsonify({
                        "success": True,
                        "fonte": "FUZZY",
                        "resposta": resultado["resposta"],
                        "faq_id": faq_id,
                        "categoria_id": categoria_id,
                        "score": resultado["score"],
                        "pergunta_faq": resultado["pergunta"],
                        "documentos": docs
                    })
                return jsonify({
                    "success": False,
                    "erro": "Não encontrei nenhuma resposta suficientemente semelhante na base de dados."
                })
        elif fonte == "faq+raga":
            resultado = obter_faq_mais_semelhante(pergunta, chatbot_id)
            if resultado:
                cur.execute("""
                    SELECT faq_id, categoria_id FROM faq
                    WHERE LOWER(pergunta) = LOWER(%s) AND chatbot_id = %s
                """, (resultado["pergunta"], chatbot_id))
                row = cur.fetchone()
                faq_id, categoria_id = row if row else (None, None)
                cur.execute("SELECT link FROM faq_documento WHERE faq_id = %s", (faq_id,))
                docs = [r[0] for r in cur.fetchall()]
                return jsonify({
                    "success": True,
                    "fonte": "FAQ",
                    "resposta": resultado["resposta"],
                    "faq_id": faq_id,
                    "categoria_id": categoria_id,
                    "score": resultado["score"],
                    "pergunta_faq": resultado["pergunta"],
                    "documentos": docs
                })
            elif feedback and feedback.strip().lower() == "try_rag":
                print("DEBUG: A tentar responder via RAG (PDF) via Ollama")
                resposta_ollama = pesquisar_pdf_ollama(pergunta, chatbot_id=chatbot_id)
                if resposta_ollama:
                    pdfs = get_pdfs_from_db(chatbot_id)
                    file_path = pdfs[0][1] if pdfs else None
                    return jsonify({
                        "success": True,
                        "fonte": "RAG-OLLAMA",
                        "resposta": resposta_ollama,
                        "faq_id": None,
                        "categoria_id": None,
                        "score": None,
                        "pergunta_faq": None,
                        "documentos": [file_path] if file_path else []
                    })
                else:
                    return jsonify({
                        "success": False,
                        "erro": "Não foi possível encontrar uma resposta nos documentos PDF usando Ollama."
                    })
            else:
                print("DEBUG: feedback != 'try_rag' -> devolve prompt_rag")
                return jsonify({
                    "success": False,
                    "erro": "Pergunta não encontrada nas FAQs. Deseja tentar encontrar uma resposta nos documentos PDF? Isso pode levar alguns segundos.",
                    "prompt_rag": True
                })
        else:
            return jsonify({"success": False, "erro": "Fonte inválida."}), 400
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"success": False, "erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/perguntas-semelhantes", methods=["POST"])
def perguntas_semelhantes():
    conn = get_conn()
    cur = conn.cursor()
    dados = request.get_json()
    pergunta_atual = dados.get("pergunta", "")
    chatbot_id = dados.get("chatbot_id")
    idioma = dados.get("idioma", "pt")
    try:
        cur.execute("""
            SELECT categoria_id
            FROM faq
            WHERE LOWER(pergunta) = LOWER(%s) AND chatbot_id = %s AND idioma = %s
        """, (pergunta_atual.strip().lower(), chatbot_id, idioma))
        categoria_row = cur.fetchone()
        if not categoria_row or categoria_row[0] is None:
            return jsonify({"success": True, "sugestoes": []})
        categoria_id = categoria_row[0]
        cur.execute("""
            SELECT pergunta
            FROM faq
            WHERE categoria_id = %s
              AND recomendado = TRUE
              AND LOWER(pergunta) != LOWER(%s)
              AND chatbot_id = %s
              AND idioma = %s
            ORDER BY RANDOM()
            LIMIT 2
        """, (categoria_id, pergunta_atual.strip().lower(), chatbot_id, idioma))
        sugestoes = [row[0] for row in cur.fetchall()]
        return jsonify({"success": True, "sugestoes": sugestoes})
    except Exception as e:
        return jsonify({"success": False, "erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/faqs-aleatorias", methods=["POST"])
def faqs_aleatorias():
    conn = get_conn()
    cur = conn.cursor()
    dados = request.get_json()
    idioma = dados.get("idioma", "pt")
    n = int(dados.get("n", 3))
    chatbot_id = dados.get("chatbot_id")
    try:
        if chatbot_id:
            cur.execute("""
                SELECT pergunta
                FROM faq
                WHERE idioma = %s AND chatbot_id = %s
                ORDER BY RANDOM()
                LIMIT %s
            """, (idioma, chatbot_id, n))
        else:
            cur.execute("""
                SELECT pergunta
                FROM faq
                WHERE idioma = %s
                ORDER BY RANDOM()
                LIMIT %s
            """, (idioma, n))
        faqs = [row[0] for row in cur.fetchall()]
        return jsonify({"success": True, "faqs": [{"pergunta": p} for p in faqs]})
    except Exception as e:
        return jsonify({"success": False, "erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/rebuild-faiss", methods=["POST"])
def rebuild_faiss():
    build_faiss_index()
    return jsonify({"success": True, "msg": "FAISS index rebuilt."})

@app.route("/faq-categoria/<categoria>", methods=["GET"])
def obter_faq_por_categoria(categoria):
    conn = get_conn()
    cur = conn.cursor()
    try:
        chatbot_id = request.args.get("chatbot_id")
        if not chatbot_id:
            return jsonify({"success": False, "erro": "chatbot_id não fornecido."}), 400
        cur.execute("""
            SELECT f.faq_id, f.pergunta, f.resposta
            FROM faq f
            INNER JOIN categoria c ON f.categoria_id = c.categoria_id
            WHERE LOWER(c.nome) = LOWER(%s) AND f.chatbot_id = %s
            ORDER BY RANDOM()
            LIMIT 1
        """, (categoria, chatbot_id))
        resultado = cur.fetchone()
        if resultado:
            return jsonify({
                "success": True,
                "faq_id": resultado[0],
                "pergunta": resultado[1],
                "resposta": resultado[2]
            })
        else:
            return jsonify({
                "success": False,
                "erro": f"Nenhuma FAQ encontrada para a categoria '{categoria}'."
            }), 404
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/perguntas-nao-respondidas", methods=["GET"])
def nao_respondidas():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id,
                   chatbot_id,
                   pergunta,
                   fonte,
                   max_score,
                   estado,
                   criado_em
            FROM perguntanaorespondida
            ORDER BY criado_em DESC
        """)
        rows = cur.fetchall()

        data = [
            {
                "id": row[0],
                "chatbot_id": row[1],
                "pergunta": row[2],
                "fonte": row[3],
                "max_score": row[4],
                "estado": row[5],
                "criado_em": row[6],  
            }
            for row in rows
        ]

        return jsonify(data)
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/perguntas-nao-respondidas/metricas", methods=["GET"])
def metricas_nao_respondidas():
    """
    Devolve contagens agregadas de perguntas não respondidas por chatbot,
    separadas por estado e incluindo o último registo.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                c.chatbot_id,
                c.nome,
                COALESCE(p.total, 0) AS total,
                COALESCE(p.pendentes, 0) AS pendentes,
                COALESCE(p.tratadas, 0) AS tratadas,
                COALESCE(p.ignoradas, 0) AS ignoradas,
                p.ultimo_registo
            FROM Chatbot c
            LEFT JOIN (
                SELECT
                    chatbot_id,
                    COUNT(*) AS total,
                    SUM(CASE WHEN LOWER(estado) = 'pendente' THEN 1 ELSE 0 END) AS pendentes,
                    SUM(CASE WHEN LOWER(estado) = 'tratada' THEN 1 ELSE 0 END) AS tratadas,
                    SUM(CASE WHEN LOWER(estado) = 'ignorada' THEN 1 ELSE 0 END) AS ignoradas,
                    MAX(criado_em) AS ultimo_registo
                FROM perguntanaorespondida
                GROUP BY chatbot_id
            ) p ON p.chatbot_id = c.chatbot_id
            ORDER BY total DESC, c.nome ASC
        """)
        rows = cur.fetchall()
        data = [
            {
                "chatbot_id": row[0],
                "nome": row[1],
                "total": row[2],
                "pendentes": row[3],
                "tratadas": row[4],
                "ignoradas": row[5],
                "ultimo_registo": row[6],
            }
            for row in rows
        ]
        return jsonify({"success": True, "metricas": data})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/perguntas-nao-respondidas/<int:pergunta_id>", methods=["DELETE"]) 
def delete_pergunta_nao_respondida(pergunta_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM perguntanaorespondida WHERE id = %s", (pergunta_id,))
        if cur.rowcount == 0:
            conn.rollback()
            return jsonify({"success": False, "error": "Pergunta nao encontrada."}), 404
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/perguntas-nao-respondidas/<int:pergunta_id>", methods=["PUT"])
def update_pergunta_nao_respondida(pergunta_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        dados = request.get_json(silent=True) or {}
        novo_estado = (dados.get("estado") or "tratada").strip().lower()

        estados_validos = {"pendente", "tratada", "ignorada"}
        if novo_estado not in estados_validos:
            return jsonify({"success": False, "error": "Estado invalido."}), 400

        cur.execute(
            "UPDATE perguntanaorespondida SET estado = %s WHERE id = %s",
            (novo_estado, pergunta_id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            return jsonify({"success": False, "error": "Pergunta nao encontrada."}), 404
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()                
