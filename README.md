## AI4APGovernance / Chatbot Municipal (Flask)

Este repositório contém um backoffice em Flask para gerir chatbots (assistentes virtuais) com:

- FAQs (regras) + pesquisa vetorial (FAISS) e embeddings
- Chat web embutido no backoffice
- Avatares com geração de vídeo (SadTalker + Piper TTS) por FAQ e vídeos do chatbot (greeting + idle)
- STT (Vosk) para transcrição de voz
- Distribuição segura de media via URLs assinadas (HMAC + expiração)

---

## Estrutura do projeto

Principais pastas/ficheiros:

- `wsgi.py`: entrypoint da app Flask
- `backoffice/app/`: aplicação Flask (blueprints, templates, static, services)
- `backoffice/db/init.sql`: schema da DB (PostgreSQL)
- `backoffice/requirements.txt`: dependências Python do backoffice
- `setup.py`: helper para instalar deps e descarregar modelos (SadTalker/Piper/Vosk) e aplicar patches
- `env.example`: template de variáveis de ambiente

Video/Avatar:

- `backoffice/app/video/`: SadTalker “vendorizado” (sem UI Gradio) + `src/inference.py`
- `backoffice/app/video/models/`: checkpoints/voices/weights (normalmente descarregados por `setup.py`)
- `backoffice/app/video/results/`: outputs do pipeline (ignorado pelo git)

Static/UI:

- `backoffice/app/templates/`: HTML do backoffice (`base_admin.html`, `recursos.html`, etc.)
- `backoffice/app/static/js/`: frontend (chat, tabela de bots, FAQs, status de vídeo, modais)
- `backoffice/app/static/icons/`: ícones enviados pelo utilizador (ignorado pelo git)

---

## Requisitos

- Python 3.9+ (recomendado 3.9–3.10 para compatibilidade com ML deps)
- PostgreSQL
- `ffmpeg` no PATH (recomendado para escrita de vídeo)

macOS (Homebrew):

```bash
brew install ffmpeg
```

---

## Setup rápido (local)

### 1) Criar DB e importar schema

```bash
psql -U postgres -c "CREATE DATABASE ai4governance;"
psql -U postgres -d ai4governance -f backoffice/db/init.sql
```

### 2) Configurar `.env`

Copiar `env.example` para `.env` na raiz do projeto e ajustar:

```bash
cp env.example .env
```

Variáveis principais:

- **DB**: `PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER`, `PG_PASS`
- **Paths**: `INDEX_PATH`, `FAQ_EMB_PATH`, `PDF_PATH`, `ICON_PATH`
- **Vídeo**: `RESULTS_DIR`, `SADTALKER_*`, `PIPER_*`
- **Segurança de media**: `REQUIRE_SIGNED_MEDIA`, `MEDIA_SIGNING_KEY`

### 3) Virtualenv + dependências

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backoffice/requirements.txt
```

### 4) Setup de modelos (SadTalker + Piper + Vosk) e patches

```bash
python3 setup.py
```

Opções úteis:

```bash
python3 setup.py --requirements-only
python3 setup.py --models-only
python3 setup.py --vosk-only
python3 setup.py --verify
python3 setup.py --patch-only
```

---

## Correr o servidor

```bash
export FLASK_APP=wsgi.py
flask run --debug
```

A app fica disponível em:

- `http://127.0.0.1:5000/` (redirect para `/login` se não estiver autenticado)
- `http://127.0.0.1:5000/login`

Nota: em dev, a app não deve forçar cookies `Secure` em HTTP. Existe override via env:

- `SESSION_COOKIE_SECURE=0` (forçar off em dev)
- `SESSION_COOKIE_SECURE=1` (forçar on, para https/prod)

---

## Criar utilizador admin (login)

O login valida a password com `werkzeug.security.check_password_hash`, portanto a password na DB deve estar **hashed**.

Em alguns ambientes, `werkzeug` não consegue usar `scrypt`; por isso usa-se PBKDF2.

### 1) Apagar admin existente (opcional)

```bash
psql -U postgres -d ai4governance -c "DELETE FROM administrador WHERE username='admin';"
```

### 2) Gerar hash PBKDF2

```bash
python3 - <<'PY'
from werkzeug.security import generate_password_hash
print(generate_password_hash("admin", method="pbkdf2:sha256", salt_length=16))
PY
```

### 3) Inserir admin (usar heredoc para não haver problemas com `$` no hash)

Substitui `HASH_AQUI` pelo valor gerado:

```bash
psql -U postgres -d ai4governance <<'SQL'
INSERT INTO administrador (username,email,password)
VALUES ('admin','admin@local','HASH_AQUI');
SQL
```

Depois entra com:

- username: `admin`
- password: `admin`

---

## Funcionalidades principais

### Gestão de Chatbots (Recursos)

- Criar/editar/eliminar chatbots
- Upload de ícone/avatar (guardado em `static/icons/`)
- Definir chatbot ativo (o chat passa a usar nome/cor/ícone do bot ativo)
- Toggle “Ativar vídeos do avatar” (gera automaticamente `greeting + idle`)

### FAQs e vídeos por FAQ

- Criar/editar/eliminar FAQs
- Quando vídeos estão ativos, uma FAQ pode gerar vídeo (um job global de cada vez)
- Status `queued / processing / ready / failed` refletido no backoffice e no chat

### Cancelamento de geração de vídeo

- Existe um indicador de progresso no topo do backoffice
- Cancelar FAQ apaga a pasta `results/faq_<id>/`
- Cancelar job de chatbot (greeting+idle) elimina o chatbot e faz cleanup associado

---

## Layout de outputs e limpeza

Os outputs finais ficam em:

- FAQs: `RESULTS_DIR/faq_<faq_id>/final.mp4`
- Chatbot: `RESULTS_DIR/chatbot_<chatbot_id>/greeting.mp4` e `idle.mp4`

O pipeline é desenhado para:

- manter apenas o MP4 final
- apagar ficheiros temporários (workspace `_tmp/`)

---

## Segurança de media (URLs assinadas)

Quando `REQUIRE_SIGNED_MEDIA=1`, os endpoints `/video/...` exigem:

- `exp` (epoch seconds)
- `nonce` (anti-cache)
- `sig` (HMAC SHA-256)

Chave:

- `MEDIA_SIGNING_KEY` (recomendado)
- fallback para `SECRET_KEY` da app

---

## Vosk (STT)

- O modelo é descarregado automaticamente por `setup.py` para `backoffice/app/extras/models/`
- A pasta do modelo deve estar ignorada pelo git (já configurado no `.gitignore`)

---

## Git hygiene: o que é ignorado

Por defeito, ficam ignorados:

- `backoffice/app/video/results/` (outputs de vídeo)
- `backoffice/app/extras/models/vosk-model-*/` (modelos grandes)
- `backoffice/app/static/icons/` (uploads do utilizador)

Se já tinhas ficheiros desses folders trackados, precisas de os remover do index:

```bash
git rm -r --cached backoffice/app/static/icons
git rm -r --cached backoffice/app/video/results
```

---

## Troubleshooting

### Não consigo fazer login

Verifica:

- password está hashed (PBKDF2) e não plaintext
- cookie de sessão não está `Secure` em HTTP (em dev, usar `SESSION_COOKIE_SECURE=0`)

### Chatbot ativo não atualiza no chat

O frontend depende de `GET /chatbots/<id>` para atualizar `nome/cor/icon` e paths de vídeo.
Se o endpoint falhar, o chat usa defaults.

### Erros de dependências `functional_tensor`

O `setup.py` inclui um patch “best-effort” para substituir `torchvision.transforms.functional_tensor` por `torchvision.transforms.functional` em bibliotecas que falham com certas combinações de torch/torchvision.

---

## Licenças e “vendor code”

O diretório `backoffice/app/video/` contém SadTalker vendorizado e dependências relacionadas.
Se voltares a reorganizar esta parte (submodule/vendor), garante que:

- `src/inference.py` continua acessível
- o serviço de geração (`backoffice/app/services/video_service.py`) continua a apontar para o `VIDEO_ROOT` correto


