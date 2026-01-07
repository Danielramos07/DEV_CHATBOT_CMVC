let botIdAEliminar = null;
let botIdCategorias = null;

window.abrirModalEliminarBot = function (chatbot_id) {
  botIdAEliminar = chatbot_id;
  const modal = document.getElementById("modalConfirmarEliminarBot");
  if (modal) modal.style.display = "flex";
};

window.fecharModalEliminarBot = function () {
  botIdAEliminar = null;
  const modal = document.getElementById("modalConfirmarEliminarBot");
  if (modal) modal.style.display = "none";
};

window.abrirModalCategorias = async function (chatbot_id) {
  botIdCategorias = chatbot_id;
  await renderizarCategoriasChatbot(chatbot_id);
  const modal = document.getElementById("modalCategorias");
  if (modal) modal.style.display = "flex";
  // If edit modal is open for this chatbot, refresh the view-only list
  try {
    const editarForm = document.getElementById("editarChatbotForm");
    const editId = editarForm ? editarForm.getAttribute("data-edit-id") : null;
    if (editId && String(editId) === String(chatbot_id)) {
      await mostrarModalEditarChatbot(chatbot_id);
    }
  } catch (e) {}
};

window.fecharModalCategorias = function () {
  const modal = document.getElementById("modalCategorias");
  if (modal) modal.style.display = "none";
  botIdCategorias = null;
};

async function renderizarCategoriasChatbot(chatbot_id) {
  const container = document.getElementById("categoriasContainer");
  if (!container) return;
  container.innerHTML =
    "<span style='color:#888;'>A carregar categorias...</span>";

  try {
    const associadas = await fetch(`/chatbots/${chatbot_id}/categorias`).then(
      (r) => r.json()
    );

    let categoriasHtml = "";
    if (associadas && associadas.length > 0) {
      categoriasHtml = associadas
        .map(
          (cat) => `
        <div class="categoria-row">
          <span>${cat.nome}</span>
          <button class="btn-eliminar-cat" onclick="removerAssociacaoCategoria(${chatbot_id}, ${cat.categoria_id})" title="Remover">Eliminar</button>
        </div>
      `
        )
        .join("");
    } else {
      categoriasHtml = `<span style='color:#888;'>Nenhuma categoria associada a este chatbot.</span>`;
    }

    const adicionarHtml = `
      <div class="adicionar-categoria-row" style="margin-top:18px;">
        <input type="text" id="novaCategoriaInput" placeholder="Nova categoria" maxlength="50">
        <button class="btn-adicionar-categoria" onclick="adicionarCategoriaDireta()">Adicionar Nova Categoria</button>
      </div>
    `;

    container.innerHTML = categoriasHtml + adicionarHtml;
  } catch (err) {
    container.innerHTML = `<span style='color:red;'>Erro ao carregar categorias: ${err.message}</span>`;
  }
}

window.toggleAssociacaoCategoria = async function (
  chatbot_id,
  categoria_id,
  checked
) {
  try {
    if (checked) {
      await fetch(`/chatbots/${chatbot_id}/categorias`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ categoria_id }),
      });
    } else {
      await fetch(`/chatbots/${chatbot_id}/categorias/${categoria_id}`, {
        method: "DELETE",
      });
    }
    await renderizarCategoriasChatbot(chatbot_id);
    // Keep edit modal categories view in sync
    try {
      const editarForm = document.getElementById("editarChatbotForm");
      const editId = editarForm
        ? editarForm.getAttribute("data-edit-id")
        : null;
      if (editId && String(editId) === String(chatbot_id)) {
        await mostrarModalEditarChatbot(chatbot_id);
      }
    } catch (e) {}
  } catch (err) {
    alert("Erro ao atualizar associação de categoria: " + err.message);
  }
};

window.removerAssociacaoCategoria = async function (chatbot_id, categoria_id) {
  try {
    await fetch(`/chatbots/${chatbot_id}/categorias/${categoria_id}`, {
      method: "DELETE",
    });
    await renderizarCategoriasChatbot(chatbot_id);
    // Keep edit modal categories view in sync
    try {
      const editarForm = document.getElementById("editarChatbotForm");
      const editId = editarForm
        ? editarForm.getAttribute("data-edit-id")
        : null;
      if (editId && String(editId) === String(chatbot_id)) {
        await mostrarModalEditarChatbot(chatbot_id);
      }
    } catch (e) {}
  } catch (err) {
    alert("Erro ao remover associação de categoria: " + err.message);
  }
};

window.adicionarCategoriaDireta = async function () {
  const input = document.getElementById("novaCategoriaInput");
  const nome = input.value.trim();
  if (!nome) return;

  try {
    let categoria_id = null;
    let res = await fetch("/categorias", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome }),
    });

    if (res.status === 409) {
      let cats = await fetch("/categorias").then((r) => r.json());
      let cat = cats.find((c) => c.nome.toLowerCase() === nome.toLowerCase());
      if (cat) categoria_id = cat.categoria_id;
      else {
        alert("Erro inesperado ao encontrar categoria existente!");
        return;
      }
    } else if (!res.ok) {
      throw new Error("Erro ao criar categoria!");
    } else {
      let cat = await res.json();
      categoria_id = cat.categoria_id;
    }

    await fetch(`/chatbots/${botIdCategorias}/categorias`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ categoria_id }),
    });
    input.value = "";
    await renderizarCategoriasChatbot(botIdCategorias);
  } catch (err) {
    alert("Erro ao adicionar categoria: " + err.message);
  }
};

async function eliminarChatbotConfirmado(chatbot_id) {
  try {
    const res = await fetch(`/chatbots/${chatbot_id}`, { method: "DELETE" });
    if (res.ok) {
      // If the deleted chatbot was the active one, clear it from localStorage
      const ativoId = localStorage.getItem("chatbotAtivo");
      if (ativoId && String(ativoId) === String(chatbot_id)) {
        localStorage.removeItem("chatbotAtivo");
        localStorage.removeItem("videoGreetingPath");
        localStorage.removeItem("videoIdlePath");
        // Reset color to default
        localStorage.setItem("corChatbot", "#d4af37");
        // Update chat UI to show default/fallback
        if (typeof window.atualizarNomeChatHeader === "function") {
          await window.atualizarNomeChatHeader();
        }
        if (typeof window.atualizarCorChatbot === "function") {
          window.atualizarCorChatbot();
        }
        if (typeof window.setupAvatarVideo === "function") {
          window.setupAvatarVideo();
        }
      }
      carregarTabelaBots();
    } else {
      const result = await res.json();
      alert(
        "Erro ao eliminar o chatbot: " +
          (result.error || result.erro || res.statusText)
      );
    }
  } catch (err) {
    alert("Erro ao comunicar com o servidor: " + err.message);
  }
}

async function carregarTabelaBots() {
  const container = document.getElementById("botsTabelaContainer");
  if (!container) return;
  container.innerHTML = "<p>A carregar bots...</p>";

  try {
    const res = await fetch("/chatbots");
    let bots = await res.json();
    if (!Array.isArray(bots) || bots.length === 0) {
      container.innerHTML = "<p>Nenhum bot encontrado.</p>";
      return;
    }

    for (const bot of bots) {
      try {
        const fonteRes = await fetch(`/fonte/${bot.chatbot_id}`);
        const fonteData = await fonteRes.json();
        bot.fonte = fonteData.fonte || "faq";
      } catch {
        bot.fonte = "faq";
      }
    }

    bots = aplicarFiltrosBots(bots);

    if (!Array.isArray(bots) || bots.length === 0) {
      container.innerHTML = "<p>Nenhum bot encontrado.</p>";
      return;
    }

    container.innerHTML = `
      <table class="bots-tabela">
        <thead>
          <tr>
            <th>Nome</th>
            <th>Descrição</th>
            <th>Data de Criação</th>
            <th>Estado</th>
            <th>Fonte</th>
            <th>Cor</th>
            <th>Ícone</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          ${bots
            .map(
              (bot) => `
            <tr data-chatbot-id="${bot.chatbot_id}">
              <td>${bot.nome || "-"}</td>
              <td>${bot.descricao || "-"}</td>
              <td>${formatarData(bot.data_criacao)}</td>
              <td>
                <span class="estado-indicador ${
                  isAtivo(bot.chatbot_id) ? "ativo" : "inativo"
                }">
                  ${isAtivo(bot.chatbot_id) ? "Ativo" : "Não Publicado"}
                </span>
              </td>
              <td>
                <span class="fonte-indicador">${obterNomeFonte(
                  bot.fonte
                )}</span>
              </td>
              <td class="cor">
                <span class="cor-bot-preview" style="background:${
                  bot.cor || "#d4af37"
                }"></span>
              </td>
              <td class="icone">
                <img src="${
                  bot.icon_path || "/static/images/chatbot/chatbot-icon.png"
                }" alt="Ícone do Bot" style="width:24px; height:24px; border-radius:4px; object-fit:cover;">
              </td>
              <td>
                <button class="btn-ativo" onclick="tornarBotAtivo(${
                  bot.chatbot_id
                }, this)">
                  ${isAtivo(bot.chatbot_id) ? "Ativo" : "Tornar Ativo"}
                </button>
                <button class="btn-editar" onclick="abrirModalAtualizar(${
                  bot.chatbot_id
                })">Atualizar</button>
                <button class="btn-categorias" onclick="abrirModalCategorias(${
                  bot.chatbot_id
                })">Categorias</button>
                <button class="btn-eliminar" onclick="abrirModalEliminarBot(${
                  bot.chatbot_id
                })">Eliminar</button>
                <button class="btn-adicionar-faq" onclick="abrirModalAdicionarFAQ(${
                  bot.chatbot_id
                })">Adicionar FAQ</button>
              </td>
            </tr>
          `
            )
            .join("")}
        </tbody>
      </table>
    `;
  } catch (e) {
    container.innerHTML = `<p style="color:red;">Erro ao carregar bots: ${e.message}</p>`;
  }
}

function aplicarFiltrosBots(bots) {
  const nomeFiltro =
    document.getElementById("filtroNomeBot")?.value?.trim().toLowerCase() || "";
  const estadoFiltro =
    document.getElementById("filtroEstadoBot")?.value || "todos";
  const dataFiltro =
    document.getElementById("filtroDataCriacaoBot")?.value || "";

  return bots.filter((bot) => {
    if (nomeFiltro && !(bot.nome || "").toLowerCase().includes(nomeFiltro))
      return false;
    const ativo = isAtivo(bot.chatbot_id);
    if (estadoFiltro === "ativo" && !ativo) return false;
    if (estadoFiltro === "nao_publicado" && ativo) return false;
    if (dataFiltro) {
      const dataBot = bot.data_criacao ? new Date(bot.data_criacao) : null;
      const dataSelecionada = new Date(dataFiltro + "T00:00:00");
      if (!dataBot || dataBot < dataSelecionada) return false;
    }
    return true;
  });
}

function formatarData(dataStr) {
  if (!dataStr) return "-";
  const data = new Date(dataStr);
  if (isNaN(data.getTime())) return "-";
  return data.toLocaleDateString("pt-PT");
}

function obterNomeFonte(fonte) {
  if (fonte === "faq") return "Baseado em Regras (FAQ)";
  if (fonte === "faiss") return "Só FAISS";
  if (fonte === "faq+raga") return "FAQ + fallback RAG";
  return fonte;
}

function obterEstadoVideo(bot) {
  if (bot.video_enabled) {
    return "Vídeo ON";
  }
  return "Vídeo OFF";
}

function isAtivo(chatbot_id) {
  return String(localStorage.getItem("chatbotAtivo")) === String(chatbot_id);
}

window.tornarBotAtivo = async function (chatbot_id, btn) {
  localStorage.setItem("chatbotAtivo", chatbot_id);
  try {
    window.chatbotAtivo = parseInt(chatbot_id);
  } catch (e) {}

  // Persist globally (server-side) so public users/new browsers inherit it.
  try {
    await fetch(`/chatbots/${chatbot_id}/active`, { method: "PUT" });
  } catch (e) {}

  // Garantir que localStorage tem o nome/icon/cor do bot ativo ANTES de reiniciar o chat
  try {
    const res = await fetch(`/chatbots/${chatbot_id}`);
    const data = await res.json();
    if (data && data.success) {
      if (data.nome) localStorage.setItem("nomeBot", data.nome);
      if (data.cor) localStorage.setItem("corChatbot", data.cor);
      if (data.icon) localStorage.setItem("iconBot", data.icon);
      if (data.genero !== undefined)
        localStorage.setItem("generoBot", data.genero || "");
      if (data.video_greeting_path)
        localStorage.setItem("videoGreetingPath", data.video_greeting_path);
      if (data.video_idle_path)
        localStorage.setItem("videoIdlePath", data.video_idle_path);
    }
  } catch (e) {}

  // Only update chat UI if chat sidebar is actually open/visible
  const chatSidebar = document.getElementById("chatSidebar");
  const isChatOpen = chatSidebar && chatSidebar.style.display !== "none";

  if (isChatOpen) {
    try {
      if (typeof window.atualizarNomeChatHeader === "function") {
        await window.atualizarNomeChatHeader();
      }
      if (typeof window.reiniciarConversa === "function") {
        try {
          if (typeof hasPlayedGreeting !== "undefined") {
            hasPlayedGreeting = false;
          }
        } catch (e) {}
        await window.reiniciarConversa();
      }
    } catch (e) {}
  }

  carregarTabelaBots();
};

document.addEventListener("DOMContentLoaded", function () {
  // NOTE: criação de chatbot (modal Novo Bot) é tratada por `AdicionarBot.js`
  // para suportar upload de icon + video_enabled via multipart/form-data.

  const editarForm = document.getElementById("editarChatbotForm");
  if (editarForm) {
    editarForm.onsubmit = async function (e) {
      e.preventDefault();
      const chatbot_id = this.getAttribute("data-edit-id");
      const nome = document.getElementById("editarNomeChatbot").value.trim();
      const descricao = document
        .getElementById("editarDescricaoChatbot")
        .value.trim();
      const fonte = document.getElementById("editarFonteResposta").value;
      const cor = document.getElementById("editarCorChatbot").value.trim();
      const mensagem_sem_resposta = document
        .getElementById("editarMensagemSemResposta")
        .value.trim();
      const genero = document.getElementById("editarGeneroChatbot").value;
      const video_enabled = document.getElementById("editarVideoEnabledChatbot")
        ? document.getElementById("editarVideoEnabledChatbot").checked
        : false;
      const iconInput = document.getElementById("editarIconChatbot");
      const iconFile = iconInput.files[0];

      if (!nome) {
        alert("Nome obrigatório");
        return;
      }

      const formData = new FormData();
      formData.append("nome", nome);
      formData.append("descricao", descricao);
      formData.append("fonte", fonte);
      formData.append("cor", cor);
      formData.append("mensagem_sem_resposta", mensagem_sem_resposta);
      formData.append("genero", genero);
      formData.append("video_enabled", video_enabled ? "true" : "false");
      if (iconFile) formData.append("icon", iconFile);

      try {
        const res = await fetch(`/chatbots/${chatbot_id}`, {
          method: "PUT",
          body: formData,
        });
        if (!res.ok && res.status === 409) {
          const result = await res.json().catch(() => ({}));
          // When a FAQ video job of this chatbot is running, backend blocks editing.
          if (result && result.busy) {
            const statusDiv = document.getElementById("editarChatbotStatus");
            if (statusDiv) {
              statusDiv.textContent =
                result.error ||
                "Não é possível editar este chatbot enquanto um vídeo está a ser gerado.";
              statusDiv.style.color = "#b91c1c";
            }
            return;
          }
        }
        if (res.ok) {
          const result = await res.json().catch(() => ({}));

          // Refresh categories view-only list (it may have changed in the categories modal)
          try {
            await mostrarModalEditarChatbot(chatbot_id);
          } catch (e) {}

          // Mostrar modal se o backend não conseguiu enfileirar por já existir um job.
          if (result && result.video_busy) {
            if (typeof mostrarModalVideoBusy === "function") {
              mostrarModalVideoBusy(
                result.error ||
                  "Já existe um vídeo a ser gerado neste momento. Aguarde que termine."
              );
            } else {
              const m = document.getElementById("modalVideoBusy");
              if (m) m.style.display = "flex";
            }
          }

          // Só ligar polling se o backend realmente enfileirou a geração.
          if (result && result.video_queued) {
            try {
              localStorage.setItem("videoJobPolling", "1");
            } catch (e) {}
            if (typeof window.startVideoStatusPolling === "function") {
              window.startVideoStatusPolling();
            }
          }

          localStorage.setItem(`fonteSelecionada_bot${chatbot_id}`, fonte);
          const ativoId = localStorage.getItem("chatbotAtivo");
          if (ativoId && String(ativoId) === String(chatbot_id)) {
            localStorage.setItem("generoBot", genero || "");
            localStorage.setItem("nomeBot", nome);
            localStorage.setItem("corChatbot", cor || "#d4af37");
            if (window.atualizarNomeChatHeader) {
              await window.atualizarNomeChatHeader();
            }
            if (window.reiniciarConversa) {
              await window.reiniciarConversa();
            }
          }
          window.fecharModalEditarChatbot();
          carregarTabelaBots();
        } else {
          const result = await res.json().catch(() => ({}));
          alert(
            "Erro ao atualizar chatbot: " +
              (result.error || result.erro || res.statusText)
          );
        }
      } catch (err) {
        alert("Erro ao atualizar chatbot: " + err.message);
      }
    };
  }

  const btnSim = document.getElementById("btnConfirmarEliminarBot");
  const btnNao = document.getElementById("btnCancelarEliminarBot");
  if (btnSim) {
    btnSim.onclick = async function () {
      if (botIdAEliminar !== null) {
        await eliminarChatbotConfirmado(botIdAEliminar);
      }
      window.fecharModalEliminarBot();
    };
  }
  if (btnNao) {
    btnNao.onclick = window.fecharModalEliminarBot;
  }

  carregarTabelaBots();

  ["filtroNomeBot", "filtroEstadoBot", "filtroDataCriacaoBot"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", carregarTabelaBots);
      el.addEventListener("change", carregarTabelaBots);
    }
  });

  const iconInput = document.getElementById("editarIconChatbot");
  if (iconInput) {
    iconInput.onchange = function (e) {
      const file = e.target.files[0];
      const preview = document.getElementById("previewIcon");
      if (file && file.type.startsWith("image/")) {
        preview.src = URL.createObjectURL(file);
        preview.style.display = "block";
      } else {
        preview.src = "/static/images/chatbot/chatbot-icon.png";
        preview.style.display = "none";
        alert("Por favor, selecione um arquivo de imagem válido.");
        iconInput.value = "";
      }
    };
  }

  // Handle video_enabled checkbox to block/unblock nome, icon, genero fields
  const videoEnabledCheckbox = document.getElementById(
    "editarVideoEnabledChatbot"
  );
  if (videoEnabledCheckbox) {
    const toggleFieldsBasedOnVideoEnabled = () => {
      const isVideoEnabled = videoEnabledCheckbox.checked;
      const nomeInput = document.getElementById("editarNomeChatbot");
      const iconInput = document.getElementById("editarIconChatbot");
      const generoSelect = document.getElementById("editarGeneroChatbot");

      if (nomeInput) {
        nomeInput.disabled = isVideoEnabled;
        nomeInput.style.opacity = isVideoEnabled ? "0.6" : "1";
        nomeInput.style.cursor = isVideoEnabled ? "not-allowed" : "text";
      }
      if (iconInput) {
        iconInput.disabled = isVideoEnabled;
        iconInput.style.opacity = isVideoEnabled ? "0.6" : "1";
        iconInput.style.cursor = isVideoEnabled ? "not-allowed" : "pointer";
      }
      if (generoSelect) {
        generoSelect.disabled = isVideoEnabled;
        generoSelect.style.opacity = isVideoEnabled ? "0.6" : "1";
        generoSelect.style.cursor = isVideoEnabled ? "not-allowed" : "pointer";
      }
    };

    videoEnabledCheckbox.addEventListener(
      "change",
      toggleFieldsBasedOnVideoEnabled
    );
    // Also call on modal open (handled in abrirModalAtualizar)
  }
});

window.abrirModalAtualizar = async function (chatbot_id) {
  try {
    const res = await fetch(`/chatbots`);
    const bots = await res.json();
    const bot = bots.find((b) => String(b.chatbot_id) === String(chatbot_id));
    if (!bot) {
      alert("Chatbot não encontrado!");
      return;
    }
    document.getElementById("editarNomeChatbot").value = bot.nome || "";
    document.getElementById("editarDescricaoChatbot").value =
      bot.descricao || "";
    document.getElementById("editarDataCriacao").value = bot.data_criacao
      ? new Date(bot.data_criacao).toLocaleDateString("pt-PT")
      : "";
    document.getElementById("editarFonteResposta").value = bot.fonte || "faq";
    document.getElementById("editarCorChatbot").value = bot.cor || "#d4af37";
    document.getElementById("editarMensagemSemResposta").value =
      bot.mensagem_sem_resposta || "";
    document.getElementById("editarGeneroChatbot").value = bot.genero || "";
    const cbVideo = document.getElementById("editarVideoEnabledChatbot");
    if (cbVideo) cbVideo.checked = !!bot.video_enabled;

    // Block/unblock fields based on video_enabled state
    const isVideoEnabled = !!bot.video_enabled;
    const nomeInput = document.getElementById("editarNomeChatbot");
    const iconInput = document.getElementById("editarIconChatbot");
    const generoSelect = document.getElementById("editarGeneroChatbot");

    if (nomeInput) {
      nomeInput.disabled = isVideoEnabled;
      nomeInput.style.opacity = isVideoEnabled ? "0.6" : "1";
      nomeInput.style.cursor = isVideoEnabled ? "not-allowed" : "text";
    }
    if (iconInput) {
      iconInput.disabled = isVideoEnabled;
      iconInput.style.opacity = isVideoEnabled ? "0.6" : "1";
      iconInput.style.cursor = isVideoEnabled ? "not-allowed" : "pointer";
    }
    if (generoSelect) {
      generoSelect.disabled = isVideoEnabled;
      generoSelect.style.opacity = isVideoEnabled ? "0.6" : "1";
      generoSelect.style.cursor = isVideoEnabled ? "not-allowed" : "pointer";
    }

    document.getElementById("previewIcon").src =
      bot.icon_path || "/static/images/chatbot/chatbot-icon.png";
    document.getElementById("previewIcon").style.display = bot.icon_path
      ? "block"
      : "none";
    document
      .getElementById("editarChatbotForm")
      .setAttribute("data-edit-id", chatbot_id);

    await mostrarModalEditarChatbot(chatbot_id);
    document.getElementById("modalEditarChatbot").style.display = "flex";
  } catch (e) {
    alert("Erro ao carregar dados do chatbot: " + e.message);
  }
};

async function mostrarModalEditarChatbot(chatbot_id) {
  const catView = document.getElementById("editarCategoriasChatbotView");
  if (!catView) return;

  try {
    const categoriasAssociadas = await fetch(
      `/chatbots/${chatbot_id}/categorias`
    ).then((r) => r.json());
    if (!categoriasAssociadas || categoriasAssociadas.length === 0) {
      catView.innerHTML =
        '<div style="color:#777;">Nenhuma categoria associada a este chatbot.</div>';
      return;
    }
    catView.innerHTML = categoriasAssociadas
      .map((c) => `<div class="cat-item">${c.nome}</div>`)
      .join("");
  } catch (err) {
    catView.innerHTML = `<div style="color:#b91c1c;">Erro ao carregar categorias: ${err.message}</div>`;
  }
}

async function atualizarCategoriasDoChatbot(chatbot_id) {
  // Categories are managed via the dedicated "Gerir Categorias" modal now.
  return;

  try {
    // noop
  } catch (err) {
    // noop
  }
}

window.abrirModalAdicionarFAQ = async function (chatbot_id) {
  const modal = document.getElementById("modalAdicionarFAQ");
  if (!modal) {
    console.error("Modal not found");
    return;
  }

  modal.setAttribute("data-chatbot-id", chatbot_id);
  document.getElementById("faqChatbotId").value = chatbot_id;
  document.getElementById("docxChatbotId").value = chatbot_id;
  document.getElementById("pdfChatbotId").value = chatbot_id;
  resetarCamposLinksFAQ();

  modal.style.display = "flex";

  await new Promise((resolve) => setTimeout(resolve, 50));

  await atualizarCategoriasFAQForm(chatbot_id);
  await carregarFAQsRelacionadasModal(chatbot_id);
  document.getElementById("mensagemFAQ").textContent = "";
};

async function atualizarCategoriasFAQForm(chatbot_id) {
  const select = document.getElementById("faqCategoriaSelect");
  if (!select) return;
  select.innerHTML = '<option value="">Escolha a categoria</option>';

  try {
    if (!chatbot_id) return;
    const cats = await fetch(`/chatbots/${chatbot_id}/categorias`).then((r) =>
      r.json()
    );
    cats.forEach((cat) => {
      const opt = document.createElement("option");
      opt.value = cat.categoria_id;
      opt.textContent = cat.nome;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error("Erro ao carregar categorias para FAQ:", err);
  }
}

async function carregarFAQsRelacionadasModal(chatbot_id) {
  const select = document.getElementById("faqRelacionadasSelect");
  if (!select) {
    console.error("Select element #faqRelacionadasSelect not found");
    return;
  }

  try {
    if (!chatbot_id) {
      console.error("No chatbot_id provided");
      return;
    }

    console.log("Loading FAQs for chatbot:", chatbot_id);
    const response = await fetch(`/faqs/chatbot/${chatbot_id}`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const faqs = await response.json();
    console.log("FAQs loaded:", faqs);

    if (!Array.isArray(faqs)) {
      console.error("Expected array but got:", typeof faqs, faqs);
      return;
    }

    let wasInitialized = false;
    if (typeof $ !== "undefined" && $(select).length) {
      const $select = $(select);
      if ($select.hasClass("select2-hidden-accessible")) {
        wasInitialized = true;
        $select.select2("destroy");
        console.log("Select2 destroyed before updating options");
      }
    }

    select.innerHTML = "";

    // Adicionar FAQs como opções
    if (faqs.length === 0) {
      console.log("No FAQs found for this chatbot");
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "Nenhuma FAQ disponível";
      option.disabled = true;
      select.appendChild(option);
    } else {
      faqs.forEach((faq) => {
        const option = document.createElement("option");
        option.value = faq.faq_id;
        const pergunta = faq.pergunta || `FAQ ${faq.faq_id}`;
        const label = (faq.identificador || "").trim();
        const truncatedPergunta =
          pergunta.length > 60 ? pergunta.substring(0, 60) + "..." : pergunta;
        option.textContent = label || truncatedPergunta;
        option.title = label ? `${label} — ${pergunta}` : pergunta;
        select.appendChild(option);
      });
      console.log(`Added ${faqs.length} FAQ options to select`);
    }

    await new Promise((resolve) => setTimeout(resolve, 100));

    // Inicializar Select2 (sempre reinicializar para garantir que está atualizado)
    if (typeof $ !== "undefined") {
      const $select = $(select);
      if ($select.length) {
        try {
          const $modal = $("#modalAdicionarFAQ");
          $select.select2({
            placeholder: "Escolha uma ou mais FAQs relacionadas",
            width: "100%",
            allowClear: true,
            dropdownParent: $modal.length ? $modal : $("body"),
            language: {
              noResults: function () {
                return "Nenhum resultado encontrado";
              },
            },
          });
          console.log("Select2 initialized successfully");
        } catch (select2Error) {
          console.error("Error initializing Select2:", select2Error);
        }
      } else {
        console.error("jQuery selector returned no elements");
      }
    } else {
      console.error("jQuery is not defined");
    }
  } catch (err) {
    console.error("Erro ao carregar FAQs relacionadas para modal:", err);
    const select = document.getElementById("faqRelacionadasSelect");
    if (select) {
      select.innerHTML = '<option value="">Erro ao carregar FAQs</option>';
    }
  }
}

function resetarCamposLinksFAQ() {
  const container = document.getElementById("faqLinksContainer");
  if (!container) return;
  container.innerHTML = "";
  adicionarCampoLink(container);
}

function adicionarCampoLink(container) {
  const row = document.createElement("div");
  row.className = "link-doc-row";
  row.style.display = "flex";
  row.style.gap = "8px";

  const input = document.createElement("input");
  input.type = "url";
  input.name = "links_documentos[]";
  input.className = "link-doc-input";
  input.placeholder = "https://exemplo.com/documento.pdf";
  input.style.flex = "1";

  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.textContent = "×";
  removeBtn.className = "btn-remover-link";
  removeBtn.style.minWidth = "90px";
  removeBtn.onclick = () => {
    const rows = container.querySelectorAll(".link-doc-row");
    if (rows.length > 1) {
      row.remove();
    } else {
      input.value = "";
    }
  };

  row.appendChild(input);
  row.appendChild(removeBtn);
  container.appendChild(row);
}

document.addEventListener("DOMContentLoaded", () => {
  const addLinkBtn = document.getElementById("faqAddLinkBtn");
  const container = document.getElementById("faqLinksContainer");
  if (addLinkBtn && container) {
    addLinkBtn.onclick = () => adicionarCampoLink(container);
  }
});

const formAdicionarFAQ = document.getElementById("formAdicionarFAQ");
if (formAdicionarFAQ) {
  formAdicionarFAQ.onsubmit = async function (e) {
    e.preventDefault();
    const chatbot_id = document.getElementById("faqChatbotId").value;
    const designacao = this.elements["designacao"].value.trim();
    const identificador = this.elements["identificador"]?.value?.trim() || "";
    const pergunta = this.elements["pergunta"].value.trim();
    const serve_text = this.elements["serve_text"]
      ? this.elements["serve_text"].value.trim()
      : "";
    const resposta = this.elements["resposta"].value.trim();
    const categoria_id = this.elements["categoria_id"].value;
    const idioma = this.elements["idioma"].value;
    const links_documentos = Array.from(
      this.querySelectorAll('input[name="links_documentos[]"]')
    )
      .map((input) => input.value.trim())
      .filter(Boolean)
      .join(",");

    // Obter valores selecionados do select múltiplo
    const relacionadasSelect = this.elements["relacionadas[]"];
    let relacionadas = "";
    if (relacionadasSelect && relacionadasSelect.selectedOptions) {
      const selectedValues = Array.from(relacionadasSelect.selectedOptions).map(
        (opt) => opt.value
      );
      relacionadas = selectedValues.join(",");
    }

    if (!designacao || !pergunta || !resposta || !categoria_id || !idioma) {
      document.getElementById("mensagemFAQ").textContent =
        "Preencha todos os campos obrigatórios!";
      document.getElementById("mensagemFAQ").style.color = "red";
      return;
    }

    const body = {
      chatbot_id,
      designacao,
      identificador,
      pergunta,
      serve_text,
      resposta,
      categoria_id,
      idioma,
      links_documentos,
      relacionadas,
    };
    try {
      const res = await fetch("/faqs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const result = await res.json();
      if (res.ok) {
        document.getElementById("mensagemFAQ").textContent =
          "FAQ adicionada com sucesso!";
        document.getElementById("mensagemFAQ").style.color = "green";
        this.reset();
        setTimeout(() => {
          window.fecharModalAdicionarFAQ();
          carregarTabelaBots();
        }, 1000);
      } else {
        document.getElementById("mensagemFAQ").textContent =
          "Erro: " + (result.error || result.erro);
        document.getElementById("mensagemFAQ").style.color = "red";
      }
    } catch (err) {
      document.getElementById("mensagemFAQ").textContent =
        "Erro ao comunicar com o servidor: " + err.message;
      document.getElementById("mensagemFAQ").style.color = "red";
    }
  };
}

const formUploadDocxFAQ = document.getElementById("formUploadDocxFAQ");
if (formUploadDocxFAQ) {
  formUploadDocxFAQ.onsubmit = async function (e) {
    e.preventDefault();
    const chatbot_id = document.getElementById("docxChatbotId").value;
    const formData = new FormData(this);
    formData.append("chatbot_id", chatbot_id);

    try {
      const res = await fetch("/upload-faq-docx-multiplos", {
        method: "POST",
        body: formData,
      });
      const result = await res.json();
      if (res.ok) {
        document.querySelector("#formUploadDocxFAQ .uploadStatus").textContent =
          "Upload bem-sucedido!";
        document.querySelector("#formUploadDocxFAQ .uploadStatus").style.color =
          "green";
        this.reset();
        try {
          if (chatbot_id !== "todos") {
            carregarTabelaFAQs(parseInt(chatbot_id), true);
          }
        } catch (e) {}
      } else if (res.status === 409 && result && result.busy) {
        // Show global busy modal (same UX as FAQ video busy)
        if (typeof mostrarModalVideoBusy === "function") {
          mostrarModalVideoBusy(
            result.error ||
              "Já existe um vídeo a ser gerado neste momento. Aguarde que termine."
          );
        } else {
          const m = document.getElementById("modalVideoBusy");
          if (m) m.style.display = "flex";
        }
      } else {
        document.querySelector("#formUploadDocxFAQ .uploadStatus").textContent =
          "Erro: " + (result.error || result.erro);
        document.querySelector("#formUploadDocxFAQ .uploadStatus").style.color =
          "red";
      }
    } catch (err) {
      document.querySelector("#formUploadDocxFAQ .uploadStatus").textContent =
        "Erro ao enviar: " + err.message;
      document.querySelector("#formUploadDocxFAQ .uploadStatus").style.color =
        "red";
    }
  };
}
const formUploadPDFFAQ = document.getElementById("formUploadPDFFAQ");
if (formUploadPDFFAQ) {
  formUploadPDFFAQ.onsubmit = async function (e) {
    e.preventDefault();
    const chatbot_id = document.getElementById("pdfChatbotId").value;
    const formData = new FormData(this);
    formData.append("chatbot_id", chatbot_id);

    try {
      const res = await fetch("/upload-pdf", {
        method: "POST",
        body: formData,
      });
      const result = await res.json();
      if (res.ok) {
        document.querySelector(
          "#formUploadPDFFAQ .uploadStatusPDF"
        ).textContent = "Upload bem-sucedido!";
        document.querySelector(
          "#formUploadPDFFAQ .uploadStatusPDF"
        ).style.color = "green";
        this.reset();
      } else {
        document.querySelector(
          "#formUploadPDFFAQ .uploadStatusPDF"
        ).textContent = "Erro: " + (result.error || result.erro);
        document.querySelector(
          "#formUploadPDFFAQ .uploadStatusPDF"
        ).style.color = "red";
      }
    } catch (err) {
      document.querySelector("#formUploadPDFFAQ .uploadStatusPDF").textContent =
        "Erro ao enviar: " + err.message;
      document.querySelector("#formUploadPDFFAQ .uploadStatusPDF").style.color =
        "red";
    }
  };
}

window.fecharModalAdicionarFAQ = function () {
  const modal = document.getElementById("modalAdicionarFAQ");
  if (modal) modal.style.display = "none";
};

window.fecharModalEditarChatbot = function () {
  const modal = document.getElementById("modalEditarChatbot");
  if (modal) modal.style.display = "none";
  document.getElementById("previewIcon").style.display = "none";
};

window.fecharModalNovoBot = function () {
  const modal = document.getElementById("modalNovoBot");
  if (modal) modal.style.display = "none";
};
