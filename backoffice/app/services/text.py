import re
from unidecode import unidecode
from rapidfuzz import fuzz
from ..db import get_conn


SAUDACOES_PT = ["olá", "ola", "oi", "bom dia", "boa tarde", "boa noite"]
SAUDACOES_EN = ["hello", "hi", "good morning", "good afternoon", "good evening", "good night"]
SAUDACOES_PERGUNTAS_PT = ["tudo bem", "como estás", "como está", "está tudo bem", "como vais", "tá bem"]
SAUDACOES_PERGUNTAS_EN = ["how are you", "how's it going", "everything ok", "are you ok", "how are you doing"]
RESPOSTA_SAUDACAO_PT = "Olá! 👋 Como posso ajudar? Se tiver alguma dúvida, basta perguntar!"
RESPOSTA_SAUDACAO_EN = "Hello! 👋 How can I help you? If you have any question, just ask!"
RESPOSTA_TUDO_BEM_PT = "Estou sempre pronto a ajudar! 😊 Em que posso ser útil?"
RESPOSTA_TUDO_BEM_EN = "I'm always ready to help! 😊 How can I assist you?"
NEGATIVE_FEEDBACK = ["não", "nao", "não está certo", "nao esta certo", "errado", "não é isso", "nao e isso"]

def preprocess_text_for_matching(text):
    stop_words = {'a', 'o', 'e', 'de', 'para', 'com', 'em', 'que', 'quem', 'como', 'do', 'da', 'os', 'as', 'dos', 'das'}
    text = unidecode(text.lower())
    text = re.sub(r'[^\w\s]', '', text)
    text = ' '.join(word for word in text.split() if word not in stop_words)
    return text.strip()

def preprocess_text(text):
    text = unidecode(text.lower())
    text = re.sub(r'[^\w\s]', '', text)
    stop_words = {'a', 'o', 'e', 'de', 'para', 'com', 'em', 'que', 'quem', 'como'}
    text = ' '.join(word for word in text.split() if word not in stop_words)
    return text

def detectar_saudacao(pergunta):
    texto = pergunta.strip().lower()
    palavras = set(texto.replace("?", "").replace("!", "").replace(".", "").split())
    for saud in SAUDACOES_PT:
        for palavra in palavras:
            if saud == palavra:
                return RESPOSTA_SAUDACAO_PT
    for p in SAUDACOES_PERGUNTAS_PT:
        if p == texto:
            return RESPOSTA_TUDO_BEM_PT
    for saud in SAUDACOES_EN:
        if saud in texto:
            return RESPOSTA_SAUDACAO_EN
    for p in SAUDACOES_PERGUNTAS_EN:
        if p in texto:
            return RESPOSTA_TUDO_BEM_EN
    return None


def detectar_feedback_negativo(pergunta):
    texto = preprocess_text(pergunta.strip().lower())
    for feedback in NEGATIVE_FEEDBACK:
        if fuzz.ratio(texto, preprocess_text(feedback)) > 80:
            return True
    return False


def normalizar_idioma(valor):
    if not valor:
        return "pt"
    valor = valor.strip().lower()
    if valor.startswith("port"):
        return "pt"
    if valor.startswith("ingl"):
        return "en"
    return valor[:2]


def registar_pergunta_nao_respondida(chatbot_id, pergunta, fonte=None , max_score=None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO perguntanaorespondida (chatbot_id, pergunta, fonte, max_score) VALUES (%s, %s, %s, %s)", (chatbot_id, pergunta, fonte, max_score))
        conn.commit()
    except Exception as e:
        print(f"Erro ao registar pergunta nao respondida: {e}")
    finally:
        cur.close()
        
