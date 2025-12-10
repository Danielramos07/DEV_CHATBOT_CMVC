-- Tabela: categoria
CREATE TABLE IF NOT EXISTS categoria (
    categoria_id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE
);

-- Tabela: chatbot
CREATE TABLE IF NOT EXISTS chatbot (
    chatbot_id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cor VARCHAR(16) NOT NULL DEFAULT '#d4af37',
    icon_path TEXT,
    mensagem_sem_resposta TEXT,
    genero VARCHAR(20)
);

-- Tabela: chatbot_categoria
CREATE TABLE IF NOT EXISTS chatbot_categoria (
    chatbot_id INT REFERENCES chatbot(chatbot_id) ON DELETE CASCADE,
    categoria_id INT REFERENCES categoria(categoria_id) ON DELETE CASCADE,
    PRIMARY KEY (chatbot_id, categoria_id)
);

-- Tabela: faq
CREATE TABLE IF NOT EXISTS faq (
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

-- Tabela: faq_documento
CREATE TABLE IF NOT EXISTS faq_documento (
    faq_id INT REFERENCES faq(faq_id) ON DELETE CASCADE,
    link TEXT NOT NULL,
    PRIMARY KEY (faq_id, link)
);

-- Tabela: faq_relacionadas
CREATE TABLE IF NOT EXISTS faq_relacionadas (
    faq_id INT REFERENCES faq(faq_id) ON DELETE CASCADE,
    faq_relacionada_id INT REFERENCES faq(faq_id) ON DELETE CASCADE,
    PRIMARY KEY (faq_id, faq_relacionada_id)
);

-- Tabela: log
CREATE TABLE IF NOT EXISTS log (
    log_id SERIAL PRIMARY KEY,
    chatbot_id INT REFERENCES Chatbot(chatbot_id) ON DELETE CASCADE,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pergunta_utilizador TEXT,
    respondido BOOLEAN
);

-- Tabela: administrador
CREATE TABLE IF NOT EXISTS administrador (
    admin_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: fonte_resposta
CREATE TABLE IF NOT EXISTS fonte_resposta (
    id SERIAL PRIMARY KEY,
    chatbot_id INT REFERENCES chatbot(chatbot_id) ON DELETE CASCADE,
    fonte TEXT NOT NULL,
    UNIQUE(chatbot_id)
);

-- Tabela: perguntanaorespondida
CREATE TABLE IF NOT EXISTS perguntanaorespondida (
    id SERIAL PRIMARY KEY,
    chatbot_id INT REFERENCES chatbot(chatbot_id) ON DELETE CASCADE,
    pergunta TEXT NOT NULL,
    fonte TEXT,
    max_score NUMERIC,
    estado VARCHAR(50) DEFAULT 'pendente',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: pdf_documents
CREATE TABLE IF NOT EXISTS pdf_documents (
    pdf_id SERIAL PRIMARY KEY,
    chatbot_id INT REFERENCES chatbot(chatbot_id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);