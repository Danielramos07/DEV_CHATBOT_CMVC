-- Tabela: Categoria
CREATE TABLE IF NOT EXISTS Categoria (
    categoria_id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE
);

-- Tabela: Chatbot
CREATE TABLE IF NOT EXISTS Chatbot (
    chatbot_id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cor VARCHAR(16) NOT NULL DEFAULT '#d4af37',
    mensagem_sem_resposta TEXT
);

-- Tabela: ChatbotCategoria
CREATE TABLE IF NOT EXISTS ChatbotCategoria (
    chatbot_id INT REFERENCES Chatbot(chatbot_id) ON DELETE CASCADE,
    categoria_id INT REFERENCES Categoria(categoria_id) ON DELETE CASCADE,
    PRIMARY KEY (chatbot_id, categoria_id)
);

-- Tabela: FAQ
CREATE TABLE IF NOT EXISTS FAQ (
    faq_id SERIAL PRIMARY KEY,
    chatbot_id INT REFERENCES Chatbot(chatbot_id) ON DELETE CASCADE,
    categoria_id INT REFERENCES Categoria(categoria_id) ON DELETE SET NULL,
    designacao VARCHAR(255),
    pergunta TEXT NOT NULL,
    resposta TEXT NOT NULL,
    idioma VARCHAR(20) NOT NULL,
    links_documentos TEXT,
    recomendado BOOLEAN DEFAULT FALSE,
    UNIQUE (chatbot_id, designacao, pergunta, resposta, idioma)
);

-- Tabela: FAQ_Documento
CREATE TABLE IF NOT EXISTS FAQ_Documento (
    faq_id INT REFERENCES FAQ(faq_id) ON DELETE CASCADE,
    link TEXT NOT NULL,
    PRIMARY KEY (faq_id, link)
);

-- Tabela: FAQ_Relacionadas
CREATE TABLE IF NOT EXISTS FAQ_Relacionadas (
    faq_id INT REFERENCES FAQ(faq_id) ON DELETE CASCADE,
    faq_relacionada_id INT REFERENCES FAQ(faq_id) ON DELETE CASCADE,
    PRIMARY KEY (faq_id, faq_relacionada_id)
);

-- Tabela: Log
CREATE TABLE IF NOT EXISTS Log (
    log_id SERIAL PRIMARY KEY,
    chatbot_id INT REFERENCES Chatbot(chatbot_id) ON DELETE CASCADE,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pergunta_utilizador TEXT,
    respondido BOOLEAN
);

-- Tabela: Administrador
CREATE TABLE IF NOT EXISTS Administrador (
    admin_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: FonteResposta
CREATE TABLE IF NOT EXISTS FonteResposta (
    id SERIAL PRIMARY KEY,
    chatbot_id INT REFERENCES Chatbot(chatbot_id) ON DELETE CASCADE,
    fonte TEXT NOT NULL,
    UNIQUE(chatbot_id)
);

-- Tabela: PDF_Documents
CREATE TABLE IF NOT EXISTS PDF_Documents (
    pdf_id SERIAL PRIMARY KEY,
    chatbot_id INT REFERENCES Chatbot(chatbot_id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);