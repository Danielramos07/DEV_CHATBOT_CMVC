let esperandoConfirmacaoRAG = false;
window.awaitingRagConfirmation = false;

function adicionarMensagem(tipo, texto) {
  const chat = document.getElementById("chatBody");
  if (!chat) return;
  const div = document.createElement("div");
  div.className = `message ${tipo}`;
  div.textContent = texto;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function mostrarPromptRAG(perguntaOriginal, chatbotId) {
  window.perguntaRAG = perguntaOriginal;
  window.chatbotIdRAG = chatbotId;
  window.awaitingRagConfirmation = true;

  const chat = document.getElementById("chatBody");

  const wrapper = document.createElement("div");
  wrapper.className = "message-wrapper bot";

  const authorDiv = document.createElement("div");
  authorDiv.className = "chat-author bot";
  authorDiv.textContent = "Assistente Municipal";
  wrapper.appendChild(authorDiv);

  const messageContent = document.createElement("div");
  messageContent.className = "message-content";

  const bubbleCol = document.createElement("div");
  bubbleCol.style.display = "flex";
  bubbleCol.style.flexDirection = "column";
  bubbleCol.style.alignItems = "flex-start";

  const msgDiv = document.createElement("div");
  msgDiv.className = "message bot";
  msgDiv.style.whiteSpace = "pre-line";
  let corBot = localStorage.getItem("corChatbot") || "#d4af37";
  msgDiv.style.backgroundColor = corBot;
  msgDiv.style.color = "#fff";

  msgDiv.innerHTML = `
    Pergunta não encontrada nas FAQs.<br>
    Deseja tentar encontrar uma resposta nos documentos PDF? 
    <a href="#" id="linkPesquisarRAG" style="color:#ffe082;font-weight:bold;text-decoration:underline;margin-left:5px;">
      Clique aqui para pesquisar
    </a>
  `;

  bubbleCol.appendChild(msgDiv);

  const timestampDiv = document.createElement("div");
  timestampDiv.className = "chat-timestamp";
  timestampDiv.textContent = gerarDataHoraFormatada();
  bubbleCol.appendChild(timestampDiv);

  messageContent.appendChild(bubbleCol);
  wrapper.appendChild(messageContent);
  chat.appendChild(wrapper);
  chat.scrollTop = chat.scrollHeight;

  setTimeout(() => {
    const link = document.getElementById("linkPesquisarRAG");
    if (link) {
      link.onclick = function (e) {
        e.preventDefault();
        enviarPerguntaRAG();
        link.textContent = "A pesquisar...";
        link.style.pointerEvents = "none";
        window.awaitingRagConfirmation = false;
      };
    }
  }, 80);
}

function enviarPerguntaRAG() {
  const pergunta = window.perguntaRAG;
  const chatbotId = window.chatbotIdRAG;

  fetch("/obter-resposta", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pergunta,
      chatbot_id: chatbotId,
      fonte: "faq+raga",
      feedback: "try_rag",
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      document.querySelectorAll(".rag-btn-bar").forEach((el) => el.remove());
      window.awaitingRagConfirmation = false;
      if (data.success) {
        adicionarMensagem("bot", data.resposta || "");
      } else {
        adicionarMensagem(
          "bot",
          data.erro || "❌ Nenhuma resposta encontrada nos documentos PDF."
        );
      }
    })
    .catch(() => {
      window.awaitingRagConfirmation = false;
      adicionarMensagem("bot", "❌ Erro ao comunicar com o servidor (RAG).");
    });
}

async function carregarChatbots() {
  try {
    const res = await fetch("/chatbots");
    const chatbots = await res.json();
    const selects = document.querySelectorAll('select[name="chatbot_id"]');
    if (selects.length) {
      const chatbotIdSelecionado = localStorage.getItem("chatbotSelecionado");
      selects.forEach((select) => {
        select.innerHTML =
          '<option value="">Selecione o Chatbot</option>' +
          '<option value="todos">Todos os Chatbots</option>' +
          chatbots
            .map(
              (bot) =>
                `<option value="${String(bot.chatbot_id)}">${bot.nome}</option>`
            )
            .join("");

        const estaEmFormulario = !!select.closest("form");
        if (
          !estaEmFormulario &&
          chatbotIdSelecionado &&
          !isNaN(parseInt(chatbotIdSelecionado))
        ) {
          select.value = chatbotIdSelecionado;
        }

        select.addEventListener("change", () => {
          const val = select.value;
          window.chatbotSelecionado = val === "todos" ? null : parseInt(val);
          if (val !== "todos")
            carregarTabelaFAQs(window.chatbotSelecionado, true);
        });
      });

      if (chatbotIdSelecionado && !isNaN(parseInt(chatbotIdSelecionado))) {
        window.chatbotSelecionado = parseInt(chatbotIdSelecionado);
        carregarTabelaFAQs(window.chatbotSelecionado, true);
      }
    }

    const filtro = document.getElementById("filtroChatbot");
    if (filtro) {
      filtro.innerHTML =
        `<option value="">Todos os Chatbots</option>` +
        chatbots
          .map(
            (bot) =>
              `<option value="${String(bot.chatbot_id)}">${bot.nome}</option>`
          )
          .join("");
    }
  } catch (err) {
    console.error("❌ Erro ao carregar chatbots:", err);
  }
}

async function carregarTabelaFAQsBackoffice() {
  const lista = document.getElementById("listaFAQs");
  if (!lista) return;
  lista.innerHTML = "<p>A carregar FAQs...</p>";

  const textoPesquisa = (
    document.getElementById("pesquisaFAQ")?.value || ""
  ).toLowerCase();
  const filtroChatbot = document.getElementById("filtroChatbot")?.value || "";
  const filtroIdioma = document.getElementById("filtroIdioma")?.value || "";

  try {
    const [faqs, chatbots, categorias] = await Promise.all([
      fetch("/faqs/detalhes").then((r) => r.json()),
      fetch("/chatbots").then((r) => r.json()),
      fetch("/categorias").then((r) => r.json()),
    ]);

    const chatbotsMap = {};
    chatbots.forEach((bot) => (chatbotsMap[bot.chatbot_id] = bot.nome));
    const categoriasMap = {};
    categorias.forEach((cat) => (categoriasMap[cat.categoria_id] = cat.nome));

    let faqsFiltradas = faqs.filter((faq) => {
      let matchPesquisa = true;
      if (textoPesquisa) {
        const target =
          (faq.identificador || "") +
          (faq.designacao || "") +
          " " +
          (faq.pergunta || "") +
          " " +
          (faq.resposta || "");
        matchPesquisa = target.toLowerCase().includes(textoPesquisa);
      }
      let matchChatbot = true;
      if (filtroChatbot)
        matchChatbot = String(faq.chatbot_id) === filtroChatbot;
      let matchIdioma = true;
      if (filtroIdioma)
        matchIdioma =
          (faq.idioma || "").toLowerCase() === filtroIdioma.toLowerCase();

      return matchPesquisa && matchChatbot && matchIdioma;
    });

    lista.innerHTML = `
      <table class="faq-tabela-backoffice">
        <thead>
          <tr>
            <th>Chatbot</th>
            <th>Identificador</th>
            <th>Descrição</th>
            <th>Pergunta</th>
            <th>Documento</th>
            <th>Idioma</th>
            <th>Categorias da FAQ</th>
            <th>Recomendações</th>
            <th>Vídeo</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          ${faqsFiltradas
            .map((faq) => {
              let docLinks = "";
              if (faq.links_documentos && faq.links_documentos.trim()) {
                docLinks = faq.links_documentos
                  .split(",")
                  .map((link) => {
                    link = link.trim();
                    if (!link) return "";
                    return `
                  <a href="${link}" target="_blank" style="display:inline-block;">
                    <img src="/static/images/ui/pdf-icon.png" alt="PDF" title="Abrir documento PDF" style="width:26px;vertical-align:middle;">
                  </a>
                `;
                  })
                  .join(" ");
              }
              let flag = "-";
              if (
                faq.idioma === "pt" ||
                faq.idioma?.toLowerCase() === "português"
              ) {
                flag =
                  '<img src="/static/images/flags/pt.jpg" style="height:20px" title="Português">';
              } else if (
                faq.idioma === "en" ||
                faq.idioma?.toLowerCase() === "inglês" ||
                faq.idioma?.toLowerCase() === "english"
              ) {
                flag =
                  '<img src="/static/images/flags/en.png" style="height:20px" title="English">';
              } else if (faq.idioma) {
                flag = faq.idioma;
              }
              let recomendacao = faq.recomendado
                ? '<span style="color:green;font-size:18px;">✅ Sim</span>'
                : '<span style="color:#cc2424;font-size:18px;">❌ Não</span>';

              let videoCol = "-";
              // Only show video status if video_status is actually set (not null/undefined)
              if (faq.video_status) {
                if (
                  faq.video_status === "processing" ||
                  faq.video_status === "queued"
                ) {
                  videoCol = '<span style="color:#d97706;">⏳ a processar</span>';
                } else if (faq.video_status === "ready" && faq.video_path) {
                  videoCol = `<a href="/video/faq/${faq.faq_id}" target="_blank" style="color:#2563eb;">▶ Ver vídeo</a>`;
                } else if (faq.video_status === "failed") {
                  videoCol = '<span style="color:#b91c1c;">❌ falhou</span>';
                }
              }
              return `
              <tr>
                <td>${chatbotsMap[faq.chatbot_id] || "-"}</td>
                <td>${faq.identificador || "-"}</td>
                <td>${faq.designacao || "-"}</td>
                <td>${faq.pergunta || "-"}</td>
                <td class="col-pdf">${docLinks || "-"}</td>
                <td>${flag}</td>
                <td>${
                  faq.categoria_nome || categoriasMap[faq.categoria_id] || "-"
                }</td>
                <td style="text-align:center;">${recomendacao}</td>
                <td style="text-align:center;">${videoCol}</td>
                <td>
                  <button class="btn-remover" onclick="pedirConfirmacao(${
                    faq.faq_id
                  })">Remover</button>
                  <button class="btn-editar" onclick="editarFAQ(${
                    faq.faq_id
                  })">Editar</button>
                </td>
              </tr>
            `;
            })
            .join("")}
        </tbody>
      </table>
    `;

    // Auto-refresh enquanto houver FAQs com vídeo em processamento/queued
    try {
      if (
        Array.isArray(faqsFiltradas) &&
        faqsFiltradas.some(
          (f) => f.video_status === "processing" || f.video_status === "queued"
        )
      ) {
        setTimeout(() => {
          try {
            carregarTabelaFAQsBackoffice();
          } catch (e) {}
        }, 15000);
      }
    } catch (e) {}
  } catch (err) {
    lista.innerHTML = "<p style='color:red;'>Erro ao carregar FAQs.</p>";
  }
}

async function carregarTabelaFAQs(chatbotId, paraDropdown = false) {
  if (paraDropdown) {
    const container = document.getElementById(`faqTabelaBot-${chatbotId}`);
    if (container) container.innerHTML = "";
    return;
  }
  carregarTabelaFAQsBackoffice();
}

async function mostrarRespostas() {
  carregarTabelaFAQsBackoffice();
}

function pedirConfirmacao(faq_id) {
  window.faqIdAEliminar = faq_id;
  document.getElementById("modalConfirmacao").style.display = "flex";
}

function responderPergunta(pergunta) {
  const chatbotId = parseInt(localStorage.getItem("chatbotAtivo"));
  if (!chatbotId || isNaN(chatbotId)) {
    adicionarMensagem(
      "bot",
      "⚠️ Nenhum chatbot ativo. Por favor, selecione um chatbot ativo no menu de recursos."
    );
    return;
  }

  if (window.awaitingRagConfirmation) {
    adicionarMensagem(
      "bot",
      "Por favor, utilize o link apresentado acima para confirmar se pretende pesquisar nos documentos PDF."
    );
    return;
  }

  const fonte =
    localStorage.getItem(`fonteSelecionada_bot${chatbotId}`) || "faq";
  fetch("/obter-resposta", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pergunta, chatbot_id: chatbotId, fonte }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        adicionarMensagem("bot", data.resposta);
        obterPerguntasSemelhantes(pergunta, chatbotId);
        window.awaitingRagConfirmation = false;
      } else if (
        data.prompt_rag ||
        (data.erro &&
          data.erro
            .toLowerCase()
            .includes(
              "deseja tentar encontrar uma resposta nos documentos pdf"
            ))
      ) {
        window.awaitingRagConfirmation = true;
        mostrarPromptRAG(pergunta, chatbotId);
      } else {
        adicionarMensagem(
          "bot",
          data.erro || "❌ Nenhuma resposta encontrada."
        );
        window.awaitingRagConfirmation = false;
      }
    })
    .catch(() => {
      adicionarMensagem("bot", "❌ Erro ao comunicar com o servidor.");
      window.awaitingRagConfirmation = false;
    });
}

function obterPerguntasSemelhantes(perguntaOriginal, chatbotId) {
  if (!chatbotId || isNaN(chatbotId)) {
    console.warn("⚠️ Chatbot ID inválido para buscar perguntas semelhantes.");
    return;
  }
  fetch("/perguntas-semelhantes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pergunta: perguntaOriginal, chatbot_id: chatbotId }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success && data.sugestoes.length > 0) {
        const chat = document.getElementById("chatBody");
        const divTitulo = document.createElement("div");
        divTitulo.className = "message bot";
        divTitulo.textContent = "🔎 Também lhe pode interessar:";
        chat.appendChild(divTitulo);

        const btnContainer = document.createElement("div");
        btnContainer.style.display = "flex";
        btnContainer.style.gap = "10px";
        btnContainer.style.marginTop = "6px";
        btnContainer.style.flexWrap = "wrap";

        data.sugestoes.forEach((pergunta) => {
          const btn = document.createElement("button");
          btn.className = "btn-similar";
          btn.textContent = pergunta;
          btn.onclick = () => {
            adicionarMensagem("user", pergunta);
            responderPergunta(pergunta);
          };
          btnContainer.appendChild(btn);
        });

        chat.appendChild(btnContainer);
        chat.scrollTop = chat.scrollHeight;
      }
    });
}

document.querySelectorAll(".faqForm").forEach((faqForm) => {
  // Remove any existing handlers to prevent duplicate submissions
  const newForm = faqForm.cloneNode(true);
  faqForm.parentNode.replaceChild(newForm, faqForm);
  const form = newForm;
  
  const statusDiv = document.createElement("div");
  statusDiv.className = "faqStatus";
  statusDiv.style.marginTop = "10px";
  form.appendChild(statusDiv);

  // Prevent duplicate submissions
  let isSubmitting = false;
  
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    e.stopPropagation(); // Prevent other handlers from firing
    
    if (isSubmitting) {
      return; // Already submitting, ignore
    }
    isSubmitting = true;

    const form = e.target;
    const chatbotIdEl =
      form.querySelector('select[name="chatbot_id"]') ||
      form.querySelector('[name="chatbot_id"]');
    const chatbotIdRaw = chatbotIdEl ? chatbotIdEl.value : "";

    const dadosBase = {
      categoria_id: (() => {
        const el = form.querySelector('[name="categoria_id"]');
        return el ? parseInt(el.value) || null : null;
      })(),
      designacao: (() => {
        const el = form.querySelector('[name="designacao"]');
        return el ? el.value.trim() : "";
      })(),
      identificador: (() => {
        const el = form.querySelector('[name="identificador"]');
        return el ? el.value.trim() : "";
      })(),
      pergunta: (() => {
        const el = form.querySelector('[name="pergunta"]');
        return el ? el.value.trim() : "";
      })(),
      resposta: (() => {
        const el = form.querySelector('[name="resposta"]');
        return el ? el.value.trim() : "";
      })(),
      documentos: (() => {
        const el = form.querySelector('[name="documentos"]');
        return el ? el.value.trim() : "";
      })(),
      relacionadas: (() => {
        const el = form.querySelector('[name="relacionadas"]');
        return el ? el.value.trim() : "";
      })(),
      recomendado: (() => {
        const el = form.querySelector('[name="recomendado"]');
        return el ? el.checked : false;
      })(),
      idioma: (() => {
        const el = form.querySelector('[name="idioma"]');
        return el ? el.value.trim() || "pt" : "pt";
      })(),
      gerar_video: (() => {
        const el = form.querySelector('[name="gerar_video"]');
        return el ? el.checked : false;
      })(),
    };

    if (!chatbotIdRaw) {
      statusDiv.innerHTML = "❌ Chatbot não selecionado.";
      statusDiv.style.color = "red";
      return;
    }

    try {
      if (chatbotIdRaw === "todos") {
        const resBots = await fetch("/chatbots");
        const chatbots = await resBots.json();

        for (const bot of chatbots) {
          const data = { ...dadosBase, chatbot_id: bot.chatbot_id };
          await fetch("/faqs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
          });
        }

        statusDiv.innerHTML = "✅ FAQ adicionada a todos os chatbots!";
        statusDiv.style.color = "green";
        form.reset();
        mostrarRespostas();
      } else {
        const data = { chatbot_id: parseInt(chatbotIdRaw), ...dadosBase };

        // Fail-safe: mesmo que o checkbox venha marcado, não pedir vídeo se o chatbot não tiver vídeo ativo.
        try {
          const resBots = await fetch("/chatbots");
          const bots = await resBots.json();
          const botAtual = bots.find(
            (b) => String(b.chatbot_id) === String(data.chatbot_id)
          );
          if (!botAtual || !botAtual.video_enabled) {
            data.gerar_video = false;
          }
        } catch (e) {
          // Se falhar, por segurança não pedir vídeo.
          data.gerar_video = false;
        }

        const res = await fetch("/faqs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });

        const resultado = await res.json();

        if (res.ok && resultado.success) {
          statusDiv.innerHTML = "✅ FAQ adicionada com sucesso!";
          statusDiv.style.color = "green";
          form.reset();
          carregarTabelaFAQs(parseInt(chatbotIdRaw), true);
          mostrarRespostas();

          // Se foi pedido vídeo E o resultado indica que foi colocado em fila, ligar o polling global do indicador.
          // Só iniciar polling se realmente houver um vídeo a ser gerado (video_queued === true)
          if (dadosBase.gerar_video && resultado.video_queued === true) {
            try {
              localStorage.setItem("videoJobPolling", "1");
            } catch (e) {}
            if (typeof window.startVideoStatusPolling === "function") {
              window.startVideoStatusPolling();
            }
          }
        } else {
          if (res.status === 409 && resultado && resultado.busy) {
            if (typeof mostrarModalVideoBusy === "function") {
              mostrarModalVideoBusy(
                resultado.error ||
                  "Já existe um vídeo a ser gerado neste momento. Aguarde que termine."
              );
            }
            // Não duplicar a mensagem em texto abaixo do botão quando o modal abre
            statusDiv.innerHTML = "";
            statusDiv.style.color = "";
            isSubmitting = false;
            return;
          }
          statusDiv.innerHTML = `❌ Erro: ${
            resultado.error || resultado.erro || "Erro desconhecido."
          }`;
          statusDiv.style.color = "red";
        }
      }
    } catch (err) {
      statusDiv.innerHTML = "❌ Erro de comunicação com o servidor.";
      statusDiv.style.color = "red";
      console.error(err);
    } finally {
      isSubmitting = false;
    }
  });
});

document.querySelectorAll(".uploadForm").forEach((uploadForm) => {
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const uploadStatus =
      uploadForm.querySelector(".uploadStatusPDF") ||
      uploadForm.querySelector(".uploadStatus") ||
      document.getElementById("uploadStatus");

    if (!uploadStatus) {
      alert(
        "⚠️ Erro: Não foi encontrado nenhum elemento para mostrar o status do upload!"
      );
      return;
    }

    const formData = new FormData(uploadForm);
    let rota = "upload-faq-docx";
    let isPDF = false;

    const pdfInput = uploadForm.querySelector(
      'input[type="file"][accept=".pdf"]'
    );
    const docxInput = uploadForm.querySelector(
      'input[type="file"][accept=".docx"]'
    );

    if (pdfInput && pdfInput.files.length > 0) {
      rota = "upload-pdf";
      isPDF = true;
      formData.delete("file");
      Array.from(pdfInput.files).forEach((file) =>
        formData.append("file", file)
      );
    } else if (docxInput && docxInput.files.length > 0) {
      // Always use the multi endpoint for docx uploads (works for 1+ files and avoids file/files mismatches)
      rota = "upload-faq-docx-multiplos";
      formData.delete("files");
      formData.delete("file");
      Array.from(docxInput.files).forEach((file) => formData.append("files", file));
    }

    const chatbotId = uploadForm.querySelector(
      'input[name="chatbot_id"]'
    )?.value;
    if (!chatbotId) {
      uploadStatus.innerHTML = "❌ Selecione um chatbot antes de enviar.";
      uploadStatus.style.color = "red";
      return;
    }
    formData.set("chatbot_id", chatbotId);

    try {
      const res = await fetch(`/${rota}`, {
        method: "POST",
        body: formData,
      });
      const resultado = await res.json();

      if (resultado.success) {
        uploadStatus.innerHTML = "✅ Documento carregado com sucesso!";
        uploadStatus.style.color = "green";
        mostrarRespostas();
        uploadForm.reset();
        if (chatbotId !== "todos") {
          carregarTabelaFAQs(parseInt(chatbotId), true);
        }
      } else {
        uploadStatus.innerHTML = `❌ Erro: ${
          resultado.error || "Erro ao carregar o documento."
        }`;
        uploadStatus.style.color = "red";
      }
    } catch (err) {
      uploadStatus.innerHTML = "❌ Erro de comunicação com o servidor.";
      uploadStatus.style.color = "red";
      console.error("Erro no upload:", err);
    }
  });
});

let faqAEditar = null;
let categoriasDisponiveis = [];

async function editarFAQ(faq_id) {
  try {
    const faqResp = await fetch(`/faqs/${faq_id}`).then((r) => r.json());
    if (!faqResp.success || !faqResp.faq) {
      alert("Erro ao carregar dados da FAQ.");
      return;
    }
    faqAEditar = faqResp.faq;

    // Block editing if the FAQ video is being generated
    if (
      faqAEditar.video_status === "queued" ||
      faqAEditar.video_status === "processing"
    ) {
      alert(
        "Não é possível editar esta FAQ enquanto o vídeo desta FAQ está a ser gerado."
      );
      return;
    }

    // Block editing FAQs that already have video when any other video job is running
    try {
      const vs = await fetch("/video/status").then((r) => r.json());
      const job = (vs && vs.job) || {};
      const isActive = job.status === "queued" || job.status === "processing";
      if (isActive && faqAEditar.video_status === "ready") {
        alert(
          "Não é possível editar FAQs com vídeo já gerado enquanto existe outro vídeo a ser gerado."
        );
        return;
      }
    } catch (e) {}

    const categorias = await fetch(
      `/chatbots/${faqAEditar.chatbot_id}/categorias`
    ).then((r) => r.json());
    categoriasDisponiveis = categorias;

    document.getElementById("editarPergunta").value = faqAEditar.pergunta || "";
    document.getElementById("editarResposta").value = faqAEditar.resposta || "";
    const editarIdentificador = document.getElementById("editarIdentificador");
    if (editarIdentificador) {
      editarIdentificador.value = faqAEditar.identificador || "";
    }
    document.getElementById("editarIdioma").value = faqAEditar.idioma || "pt";
    if (document.getElementById("editarRecomendado"))
      document.getElementById("editarRecomendado").checked =
        !!faqAEditar.recomendado;
    // Preencher FAQs relacionadas
    await carregarFAQsRelacionadasEditar(
      faqAEditar.chatbot_id,
      faqAEditar.relacionadas || [],
      faqAEditar.faq_id
    );

    const catSelect = document.getElementById("editarCategoriaSelect");
    if (catSelect) {
      const selectedId = faqAEditar.categoria_id ? String(faqAEditar.categoria_id) : "";
      catSelect.innerHTML =
        '<option value="">Sem categoria</option>' +
        categorias
          .map(
            (cat) =>
              `<option value="${cat.categoria_id}">${cat.nome}</option>`
          )
          .join("");
      catSelect.value = selectedId;
    }

    document.getElementById("modalEditarFAQ").style.display = "flex";
    const statusDiv = document.getElementById("editarStatusFAQ");
    if (statusDiv) {
      let texto = "";
      if (
        faqAEditar.video_status === "processing" ||
        faqAEditar.video_status === "queued"
      ) {
        texto = "Vídeo desta FAQ está em processamento.";
        statusDiv.style.color = "#d97706";
      } else if (faqAEditar.video_status === "ready" && faqAEditar.video_path) {
        texto = `Vídeo disponível para esta FAQ. Clique em 'Ver vídeo' na listagem para o abrir.`;
        statusDiv.style.color = "#16a34a";
      } else if (faqAEditar.video_status === "failed") {
        texto = "A geração de vídeo para esta FAQ falhou.";
        statusDiv.style.color = "#b91c1c";
      } else {
        texto = "Esta FAQ ainda não tem vídeo associado.";
        statusDiv.style.color = "#4b5563";
      }
      statusDiv.textContent = texto;
    }
  } catch (err) {
    alert("Erro ao carregar dados da FAQ.");
  }
}

const formEditarFAQ = document.getElementById("formEditarFAQ");
if (formEditarFAQ) {
  formEditarFAQ.onsubmit = async function (e) {
    e.preventDefault();
    const status = document.getElementById("editarStatusFAQ");
    status.textContent = "";

    if (!faqAEditar) return;

    const pergunta = document.getElementById("editarPergunta").value.trim();
    const resposta = document.getElementById("editarResposta").value.trim();
    const idioma = document.getElementById("editarIdioma").value;
    const identificador = document
      .getElementById("editarIdentificador")
      ?.value.trim();
    const recomendado = document.getElementById("editarRecomendado")
      ? document.getElementById("editarRecomendado").checked
      : false;

    const categoriaSel = document.getElementById("editarCategoriaSelect")
      ? parseInt(document.getElementById("editarCategoriaSelect").value || "")
      : null;
    const relacionadasSel = Array.from(
      document.querySelectorAll(
        '#editarFaqRelacionadasSelect option:checked'
      )
    ).map((opt) => parseInt(opt.value));

    try {
      const res = await fetch(`/faqs/${faqAEditar.faq_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pergunta,
          resposta,
          idioma,
          identificador,
          recomendado,
          categoria_id: Number.isFinite(categoriaSel) ? categoriaSel : null,
          relacionadas: relacionadasSel,
        }),
      });
      const out = await res.json();
      if (out.success) {
        status.textContent = "✅ FAQ atualizada com sucesso!";
        status.style.color = "green";
        setTimeout(() => {
          document.getElementById("modalEditarFAQ").style.display = "none";
          mostrarRespostas();
        }, 800);
      } else {
        if (res.status === 409 && out && out.busy) {
          status.textContent = out.error || "Não é possível editar agora.";
          status.style.color = "#b91c1c";
          return;
        }
        status.textContent = out.error || "Erro ao atualizar.";
        status.style.color = "red";
      }
    } catch (err) {
      status.textContent = "Erro de comunicação com o servidor.";
      status.style.color = "red";
    }
  };
}

function ligarBotaoCancelarEditarFAQ() {
  const btnCancelar = document.getElementById("btnCancelarFAQ");
  if (btnCancelar) {
    btnCancelar.onclick = function (e) {
      e.preventDefault();
      document.getElementById("modalEditarFAQ").style.display = "none";
      const status = document.getElementById("editarStatusFAQ");
      if (status) status.textContent = "";
      const relSelect = document.getElementById("editarFaqRelacionadasSelect");
      if (relSelect && typeof $ !== "undefined" && $(relSelect).length) {
        try {
          $(relSelect).val(null).trigger("change").select2("close");
        } catch (err) {}
      }
    };
  }
}

async function carregarFAQsRelacionadasEditar(
  chatbotId,
  selecionadas = [],
  faqAtualId = null
) {
  const select = document.getElementById("editarFaqRelacionadasSelect");
  if (!select || !chatbotId) return;

  try {
    const response = await fetch(`/faqs/chatbot/${chatbotId}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const faqs = await response.json();

    let wasInitialized = false;
    if (typeof $ !== "undefined" && $(select).length) {
      const $select = $(select);
      if ($select.hasClass("select2-hidden-accessible")) {
        wasInitialized = true;
        $select.select2("destroy");
      }
    }

    select.innerHTML = "";
    const filtered = Array.isArray(faqs)
      ? faqs.filter((f) => String(f.faq_id) !== String(faqAtualId))
      : [];

    if (!filtered.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Nenhuma FAQ disponível";
      opt.disabled = true;
      select.appendChild(opt);
    } else {
      filtered.forEach((faq) => {
        const opt = document.createElement("option");
        opt.value = faq.faq_id;
        const pergunta = faq.pergunta || `FAQ ${faq.faq_id}`;
        const truncated =
          pergunta.length > 60 ? pergunta.slice(0, 60) + "..." : pergunta;
        const label = (faq.identificador || "").trim();
        opt.textContent = label || truncated;
        opt.title = label ? `${label} — ${pergunta}` : pergunta;
        if (
          selecionadas.includes(faq.faq_id) ||
          selecionadas.includes(+faq.faq_id)
        ) {
          opt.selected = true;
        }
        select.appendChild(opt);
      });
    }

    if (typeof $ !== "undefined" && $(select).length) {
      try {
        const $modal = $("#modalEditarFAQ");
        $(select).select2({
          placeholder: "Escolha FAQs relacionadas",
          width: "100%",
          allowClear: true,
          dropdownParent: $modal.length ? $modal : $("body"),
          language: {
            noResults: () => "Nenhum resultado encontrado",
          },
        });
      } catch (err) {
        console.error("Erro ao iniciar select2 no editar FAQ:", err);
      }
    }
  } catch (err) {
    console.error("Erro ao carregar FAQs relacionadas (editar):", err);
  }
}

async function eliminarFAQ(faq_id) {
  try {
    const res = await fetch(`/faqs/${faq_id}`, { method: "DELETE" });
    if (res.ok) mostrarRespostas();
    else alert("❌ Erro ao eliminar FAQ.");
  } catch {
    alert("❌ Erro de comunicação com o servidor.");
  }
}

window.carregarChatbots = carregarChatbots;
window.carregarTabelaFAQs = carregarTabelaFAQs;
window.carregarTabelaFAQsBackoffice = carregarTabelaFAQsBackoffice;
window.mostrarRespostas = mostrarRespostas;
window.eliminarFAQ = eliminarFAQ;
window.responderPergunta = responderPergunta;
window.obterPerguntasSemelhantes = obterPerguntasSemelhantes;
window.pedirConfirmacao = pedirConfirmacao;
document.addEventListener("DOMContentLoaded", () => {
  carregarChatbots();
  carregarTabelaFAQsBackoffice();

  const pesquisaInput = document.getElementById("pesquisaFAQ");
  const filtroChatbot = document.getElementById("filtroChatbot");
  const filtroIdioma = document.getElementById("filtroIdioma");

  if (pesquisaInput)
    pesquisaInput.addEventListener("input", carregarTabelaFAQsBackoffice);
  if (filtroChatbot)
    filtroChatbot.addEventListener("change", carregarTabelaFAQsBackoffice);
  if (filtroIdioma)
    filtroIdioma.addEventListener("change", carregarTabelaFAQsBackoffice);

  ligarBotaoCancelarEditarFAQ();

  // Polling para atualizar status dos vídeos a cada 30 segundos
  setInterval(() => {
    // Só recarrega se a página estiver visível e se houver vídeos em processamento
    if (document.visibilityState === "visible") {
      carregarTabelaFAQsBackoffice();
    }
  }, 30000);
});
