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
      }
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
      feedback: "try_rag"
    })
  })
    .then(res => res.json())
    .then(data => {
      document.querySelectorAll('.rag-btn-bar').forEach(el => el.remove());
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
      adicionarMensagem(
        "bot",
        "❌ Erro ao comunicar com o servidor (RAG)."
      );
    });
}

async function carregarChatbots() {
  try {
    const res = await fetch("/chatbots");
    const chatbots = await res.json();
    const selects = document.querySelectorAll('select[name="chatbot_id"]');
    if (selects.length) {
      const chatbotIdSelecionado = localStorage.getItem("chatbotSelecionado");
      selects.forEach(select => {
        select.innerHTML = '<option value="">Selecione o Chatbot</option>' +
          '<option value="todos">Todos os Chatbots</option>' +
          chatbots.map(bot => `<option value="${String(bot.chatbot_id)}">${bot.nome}</option>`).join('');

        const estaEmFormulario = !!select.closest("form");
        if (!estaEmFormulario && chatbotIdSelecionado && !isNaN(parseInt(chatbotIdSelecionado))) {
          select.value = chatbotIdSelecionado;
        }

        select.addEventListener("change", () => {
          const val = select.value;
          window.chatbotSelecionado = val === "todos" ? null : parseInt(val);
          if (val !== "todos") carregarTabelaFAQs(window.chatbotSelecionado, true);
        });
      });

      if (chatbotIdSelecionado && !isNaN(parseInt(chatbotIdSelecionado))) {
        window.chatbotSelecionado = parseInt(chatbotIdSelecionado);
        carregarTabelaFAQs(window.chatbotSelecionado, true);
      }
    }

    const filtro = document.getElementById("filtroChatbot");
    if (filtro) {
      filtro.innerHTML = `<option value="">Todos os Chatbots</option>` +
        chatbots.map(bot => `<option value="${String(bot.chatbot_id)}">${bot.nome}</option>`).join('');
    }
  } catch (err) {
    console.error("❌ Erro ao carregar chatbots:", err);
  }
}

async function carregarTabelaFAQsBackoffice() {
  const lista = document.getElementById("listaFAQs");
  if (!lista) return;
  lista.innerHTML = "<p>A carregar FAQs...</p>";

  const textoPesquisa = (document.getElementById("pesquisaFAQ")?.value || "").toLowerCase();
  const filtroChatbot = document.getElementById("filtroChatbot")?.value || "";
  const filtroIdioma = document.getElementById("filtroIdioma")?.value || "";

  try {
    const [faqs, chatbots, categorias] = await Promise.all([
      fetch("/faqs/detalhes").then(r => r.json()),
      fetch("/chatbots").then(r => r.json()),
      fetch("/categorias").then(r => r.json())
    ]);

    const chatbotsMap = {};
    chatbots.forEach(bot => chatbotsMap[bot.chatbot_id] = bot.nome);
    const categoriasMap = {};
    categorias.forEach(cat => categoriasMap[cat.categoria_id] = cat.nome);

    let faqsFiltradas = faqs.filter(faq => {
      let matchPesquisa = true;
      if (textoPesquisa) {
        const target =
          (faq.designacao || "") + " " +
          (faq.pergunta || "") + " " +
          (faq.resposta || "");
        matchPesquisa = target.toLowerCase().includes(textoPesquisa);
      }
      let matchChatbot = true;
      if (filtroChatbot) matchChatbot = String(faq.chatbot_id) === filtroChatbot;
      let matchIdioma = true;
      if (filtroIdioma) matchIdioma = (faq.idioma || "").toLowerCase() === filtroIdioma.toLowerCase();

      return matchPesquisa && matchChatbot && matchIdioma;
    });

    lista.innerHTML = `
      <table class="faq-tabela-backoffice">
        <thead>
          <tr>
            <th>Chatbot</th>
            <th>Descrição</th>
            <th>Pergunta</th>
            <th>Documento</th>
            <th>Idioma</th>
            <th>Categorias da FAQ</th>
            <th>Recomendações</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          ${faqsFiltradas.map(faq => {
            let docLinks = "";
            if (faq.links_documentos && faq.links_documentos.trim()) {
              docLinks = faq.links_documentos.split(",").map(link => {
                link = link.trim();
                if (!link) return "";
                return `
                  <a href="${link}" target="_blank" style="display:inline-block;">
                    <img src="images/pdf-icon.png" alt="PDF" title="Abrir documento PDF" style="width:26px;vertical-align:middle;">
                  </a>
                `;
              }).join(" ");
            }
            let flag = "-";
            if (faq.idioma === "pt" || faq.idioma?.toLowerCase() === "português") {
              flag = '<img src="/static/images/pt.jpg" style="height:20px" title="Português">';
            } else if (faq.idioma === "en" || faq.idioma?.toLowerCase() === "inglês" || faq.idioma?.toLowerCase() === "english") {
              flag = '<img src="/static/images/en.png" style="height:20px" title="English">';
            } else if (faq.idioma) {
              flag = faq.idioma;
            }
            let recomendacao = faq.recomendado
              ? '<span style="color:green;font-size:18px;">✅ Sim</span>'
              : '<span style="color:#cc2424;font-size:18px;">❌ Não</span>';
            return `
              <tr>
                <td>${chatbotsMap[faq.chatbot_id] || "-"}</td>
                <td>${faq.designacao || "-"}</td>
                <td>${faq.pergunta || "-"}</td>
                <td class="col-pdf">${docLinks || "-"}</td>
                <td>${flag}</td>
                <td>${faq.categoria_nome || categoriasMap[faq.categoria_id] || "-"}</td>
                <td style="text-align:center;">${recomendacao}</td>
                <td>
                  <button class="btn-remover" onclick="pedirConfirmacao(${faq.faq_id})">Remover</button>
                  <button class="btn-editar" onclick="editarFAQ(${faq.faq_id})">Editar</button>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    `;
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

  const fonte = localStorage.getItem(`fonteSelecionada_bot${chatbotId}`) || "faq";
  fetch("/obter-resposta", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pergunta, chatbot_id: chatbotId, fonte })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        adicionarMensagem("bot", data.resposta);
        obterPerguntasSemelhantes(pergunta, chatbotId);
        window.awaitingRagConfirmation = false;
      } else if (
        data.prompt_rag ||
        (data.erro &&
          data.erro.toLowerCase().includes("deseja tentar encontrar uma resposta nos documentos pdf"))
      ) {
        window.awaitingRagConfirmation = true;
        mostrarPromptRAG(pergunta, chatbotId);
      } else {
        adicionarMensagem("bot", data.erro || "❌ Nenhuma resposta encontrada.");
        window.awaitingRagConfirmation = false;
      }
    })
    .catch(() => {
      adicionarMensagem(
        "bot",
        "❌ Erro ao comunicar com o servidor."
      );
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
    body: JSON.stringify({ pergunta: perguntaOriginal, chatbot_id: chatbotId })
  })
    .then(res => res.json())
    .then(data => {
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

        data.sugestoes.forEach(pergunta => {
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

document.querySelectorAll(".faqForm").forEach(faqForm => {
  const statusDiv = document.createElement("div");
  statusDiv.className = "faqStatus";
  statusDiv.style.marginTop = "10px";
  faqForm.appendChild(statusDiv);

  faqForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const form = e.target;
    const chatbotIdRaw = form.querySelector('select[name="chatbot_id"]').value;

    const dadosBase = {
      categoria_id: parseInt(form.categoria_id.value) || null,
      designacao: form.designacao.value.trim(),
      pergunta: form.pergunta.value.trim(),
      resposta: form.resposta.value.trim(),
      documentos: form.documentos.value.trim(),
      relacionadas: form.relacionadas.value.trim(),
      recomendado: form.recomendado ? form.recomendado.checked : false
    };

    try {
      if (chatbotIdRaw === "todos") {
        const resBots = await fetch("/chatbots");
        const chatbots = await resBots.json();

        for (const bot of chatbots) {
          const data = { ...dadosBase, chatbot_id: bot.chatbot_id };
          await fetch("/faqs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
          });
        }

        statusDiv.innerHTML = "✅ FAQ adicionada a todos os chatbots!";
        statusDiv.style.color = "green";
        form.reset();
        mostrarRespostas();
      } else {
        const data = { chatbot_id: parseInt(chatbotIdRaw), ...dadosBase };
        const res = await fetch("/faqs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data)
        });

        const resultado = await res.json();

        if (res.ok && resultado.success) {
          statusDiv.innerHTML = "✅ FAQ adicionada com sucesso!";
          statusDiv.style.color = "green";
          form.reset();
          carregarTabelaFAQs(parseInt(chatbotIdRaw), true);
          mostrarRespostas();
        } else {
          statusDiv.innerHTML = `❌ Erro: ${resultado.error || resultado.erro || "Erro desconhecido."}`;
          statusDiv.style.color = "red";
        }
      }
    } catch (err) {
      statusDiv.innerHTML = "❌ Erro de comunicação com o servidor.";
      statusDiv.style.color = "red";
      console.error(err);
    }
  });
});

document.querySelectorAll(".uploadForm").forEach(uploadForm => {
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const uploadStatus = 
      uploadForm.querySelector(".uploadStatusPDF") ||
      uploadForm.querySelector(".uploadStatus") ||
      document.getElementById("uploadStatus");

    if (!uploadStatus) {
      alert("⚠️ Erro: Não foi encontrado nenhum elemento para mostrar o status do upload!");
      return;
    }

    const formData = new FormData(uploadForm);
    let rota = "upload-faq-docx";
    let isPDF = false;

    const pdfInput = uploadForm.querySelector('input[type="file"][accept=".pdf"]');
    const docxInput = uploadForm.querySelector('input[type="file"][accept=".docx"]');

    if (pdfInput && pdfInput.files.length > 0) {
      rota = "upload-pdf";
      isPDF = true;
      formData.delete("file");
      Array.from(pdfInput.files).forEach(file => formData.append("file", file));
    } else if (docxInput && docxInput.files.length > 1) {
      rota = "upload-faq-docx-multiplos";
      formData.delete("files");
      Array.from(docxInput.files).forEach(file => formData.append("files", file));
    }

    const chatbotId = uploadForm.querySelector('input[name="chatbot_id"]')?.value;
    if (!chatbotId) {
      uploadStatus.innerHTML = "❌ Selecione um chatbot antes de enviar.";
      uploadStatus.style.color = "red";
      return;
    }
    formData.set("chatbot_id", chatbotId);

    try {
      const res = await fetch(`/${rota}`, {
        method: "POST",
        body: formData
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
        uploadStatus.innerHTML = `❌ Erro: ${resultado.error || "Erro ao carregar o documento."}`;
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
    const faqResp = await fetch(`/faqs/${faq_id}`).then(r => r.json());
    if (!faqResp.success || !faqResp.faq) {
      alert("Erro ao carregar dados da FAQ.");
      return;
    }
    faqAEditar = faqResp.faq;

    const categorias = await fetch(`/chatbots/${faqAEditar.chatbot_id}/categorias`).then(r => r.json());
    categoriasDisponiveis = categorias;

    document.getElementById('editarPergunta').value = faqAEditar.pergunta || "";
    document.getElementById('editarResposta').value = faqAEditar.resposta || "";
    document.getElementById('editarIdioma').value = faqAEditar.idioma || "pt";
    if (document.getElementById('editarRecomendado'))
      document.getElementById('editarRecomendado').checked = !!faqAEditar.recomendado;

    const catContainer = document.getElementById('editarCategoriasContainer');
    let categoriasMarcadas = [];
    if (Array.isArray(faqAEditar.categorias)) {
      categoriasMarcadas = faqAEditar.categorias.map(Number);
    } else if (faqAEditar.categoria_id) {
      categoriasMarcadas = [Number(faqAEditar.categoria_id)];
    }
    catContainer.innerHTML = categorias.map(cat => {
      const checked = categoriasMarcadas.includes(Number(cat.categoria_id));
      return `<label style="display:inline-flex;align-items:center;gap:3px;">
        <input type="checkbox" value="${cat.categoria_id}" ${checked ? "checked" : ""} />${cat.nome}
      </label>`;
    }).join("");

    document.getElementById("modalEditarFAQ").style.display = "flex";
    document.getElementById("editarStatusFAQ").textContent = "";
  } catch (err) {
    alert("Erro ao carregar dados da FAQ.");
  }
}  

const formEditarFAQ = document.getElementById("formEditarFAQ");
if (formEditarFAQ) {
  formEditarFAQ.onsubmit = async function(e) {
    e.preventDefault();
    const status = document.getElementById("editarStatusFAQ");
    status.textContent = "";

    if (!faqAEditar) return;

    const pergunta = document.getElementById('editarPergunta').value.trim();
    const resposta = document.getElementById('editarResposta').value.trim();
    const idioma = document.getElementById('editarIdioma').value;
    const recomendado = document.getElementById('editarRecomendado') ? document.getElementById('editarRecomendado').checked : false;

    const categoriasSel = Array.from(document.querySelectorAll('#editarCategoriasContainer input[type="checkbox"]:checked'))
      .map(cb => parseInt(cb.value));

    try {
      const res = await fetch(`/faqs/${faqAEditar.faq_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pergunta,
          resposta,
          idioma,
          recomendado,
          categorias: categoriasSel
        })
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
    btnCancelar.onclick = function(e) {
      e.preventDefault();
      document.getElementById("modalEditarFAQ").style.display = "none";
      const status = document.getElementById("editarStatusFAQ");
      if (status) status.textContent = "";
    }
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

  if (pesquisaInput) pesquisaInput.addEventListener("input", carregarTabelaFAQsBackoffice);
  if (filtroChatbot) filtroChatbot.addEventListener("change", carregarTabelaFAQsBackoffice);
  if (filtroIdioma) filtroIdioma.addEventListener("change", carregarTabelaFAQsBackoffice);

  ligarBotaoCancelarEditarFAQ();
});