# SadTalker (vendorizado) para geração de vídeo do avatar

Este diretório contém uma versão vendorizada/embutida do SadTalker (sem Gradio/WebUI) usada pela aplicação Flask para gerar:

- vídeos de FAQ: resposta → vídeo “falado”
- vídeos do chatbot: `greeting.mp4` e `idle.mp4`

O “orquestrador” que chama este módulo é o serviço:

- `backoffice/app/services/video_service.py`

---

## Como é usado na app

A app não usa isto como projeto standalone. Em runtime, o `video_service.py` chama:

- `python -m src.inference` dentro de `backoffice/app/video/` (via `subprocess`)
- Piper TTS via wrapper Python (`backoffice/app/video/src/piper_tts.py`)

O serviço define o layout de resultados e faz cleanup de temporários.

---

## Outputs e layout

Por defeito (configurado pelo `.env` na raiz do projeto):

- FAQs: `RESULTS_DIR/faq_<faq_id>/final.mp4`
- Chatbot: `RESULTS_DIR/chatbot_<chatbot_id>/greeting.mp4` e `idle.mp4`

O pipeline cria um workspace temporário em:

- `RESULTS_DIR/<entity>/_tmp/...`

No fim, **apaga `_tmp/` e deixa apenas o MP4 final**.

---

## Modelos e assets

Este folder inclui o código, mas os assets de modelo são geridos por `setup.py` na raiz do repo:

- `models/checkpoints/` (weights SadTalker)
- `models/voices/` (Piper voices)
- `models/gfpgan/weights/` (opcional, enhancer)

O diretório `results/` deve ser considerado output e **não deve ir para git**.

---

## Configuração (via `.env` na raiz do projeto)

Variáveis relevantes (ver `env.example`):

- `RESULTS_DIR`
- `PIPER_VOICES_DIR`
- `PIPER_VOICE_MALE`, `PIPER_VOICE_FEMALE`, `PIPER_VOICE_DEFAULT`
- `SADTALKER_PREPROCESS_DEFAULT` (`crop|full|extfull`)
- `SADTALKER_SIZE_DEFAULT` (`256|512`)
- `SADTALKER_BATCH_SIZE_DEFAULT` (recomendado `1`)
- `SADTALKER_ENHANCER_DEFAULT` (vazio ou `gfpgan`)
- `SADTALKER_IDLE_SECONDS` (duração do idle)

Notas:

- Em macOS, para acelerar e reduzir problemas, o enhancer pode ficar desativado por defeito (`SADTALKER_ENHANCER_DEFAULT=`).
- O avatar (imagem fonte) vem do `icon_path` do chatbot (normalmente `/static/icons/<nome>_<id>.ext`), resolvido para o ficheiro real pelo `video_service.py`.

---

## Execução manual (debug)

Isto é útil para debug, mas não é o caminho normal da app.

Exemplo:

```bash
cd backoffice/app/video
python -m src.inference \
  --driven_audio /path/to/audio.wav \
  --source_image /path/to/image.png \
  --result_dir ./results \
  --save_dir ./results/debug-run \
  --size 256 \
  --batch_size 1 \
  --preprocess crop
```

---

## Cancelamento

O cancelamento é gerido a nível da app (não aqui):

- endpoint: `POST /video/cancel`
- serviço: `backoffice/app/services/video_service.py`

O serviço tenta terminar o processo SadTalker em curso e faz cleanup (ex.: apagar `results/faq_<id>/` ou `results/chatbot_<id>/` quando aplicável).

---

## Troubleshooting

### `functional_tensor` vs `functional`

Algumas combinações de `torchvision` podem quebrar dependências (ex.: `basicsr`) por causa de `functional_tensor`.
O `setup.py` na raiz inclui um patch para corrigir imports incompatíveis.

### `GFPGANer __init__ unexpected keyword argument 'model_rootpath'`

A correção foi aplicada no código vendorizado em `src/utils/face_enhancer.py` para compatibilidade com a versão instalada.

### Performance

- `batch_size=1` é o mais estável para macOS/CPU.
- Se estiveres em Apple Silicon e usares PyTorch com MPS, o ganho pode variar; o pipeline atual privilegia estabilidade.
