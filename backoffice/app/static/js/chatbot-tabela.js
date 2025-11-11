let botIdAEliminar = null;
let botIdCategorias = null;

window.abrirModalEliminarBot = function(chatbot_id) {
  botIdAEliminar = chatbot_id;
  const modal = document.getElementById('modalConfirmarEliminarBot');
  if (modal) modal.style.display = 'flex';
};

window.fecharModalEliminarBot = function() {
  botIdAEliminar = null;
  const modal = document.getElementById('modalConfirmarEliminarBot');
  if (modal) modal.style.display = 'none';
};

window.abrirModalCategorias = async function(chatbot_id) {
  botIdCategorias = chatbot_id;
  await renderizarCategoriasChatbot(chatbot_id);
  const modal = document.getElementById("modalCategorias");
  if (modal) modal.style.display = "flex";
};

window.fecharModalCategorias = function() {
  const modal = document.getElementById("modalCategorias");
  if (modal) modal.style.display = "none";
  botIdCategorias = null;
};

async function renderizarCategoriasChatbot(chatbot_id) {
  const container = document.getElementById("categoriasContainer");
  if (!container) return;
  container.innerHTML = "<span style='color:#888;'>A carregar categorias...</span>";

  try {
    const associadas = await fetch(`/chatbots/${chatbot_id}/categorias`).then(r => r.json());

    let categoriasHtml = '';
    if (associadas && associadas.length > 0) {
      categoriasHtml = associadas.map(cat => `
        <div class="categoria-row">
          <span>${cat.nome}</span>
          <button class="btn-eliminar-cat" onclick="removerAssociacaoCategoria(${chatbot_id}, ${cat.categoria_id})" title="Remover">Eliminar</button>
        </div>
      `).join("");
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

window.toggleAssociacaoCategoria = async function(chatbot_id, categoria_id, checked) {
  try {
    if (checked) {
      await fetch(`/chatbots/${chatbot_id}/categorias`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ categoria_id })
      });
    } else {
      await fetch(`/chatbots/${chatbot_id}/categorias/${categoria_id}`, { method: "DELETE" });
    }
    await renderizarCategoriasChatbot(chatbot_id);
  } catch (err) {
    alert("Erro ao atualizar associação de categoria: " + err.message);
  }
};

window.removerAssociacaoCategoria = async function(chatbot_id, categoria_id) {
  try {
    await fetch(`/chatbots/${chatbot_id}/categorias/${categoria_id}`, { method: "DELETE" });
    await renderizarCategoriasChatbot(chatbot_id);
  } catch (err) {
    alert("Erro ao remover associação de categoria: " + err.message);
  }
};

window.adicionarCategoriaDireta = async function() {
  const input = document.getElementById("novaCategoriaInput");
  const nome = input.value.trim();
  if (!nome) return;

  try {
    let categoria_id = null;
    let res = await fetch("/categorias", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome })
    });

    if (res.status === 409) {
      let cats = await fetch("/categorias").then(r => r.json());
      let cat = cats.find(c => c.nome.toLowerCase() === nome.toLowerCase());
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
      body: JSON.stringify({ categoria_id })
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
      carregarTabelaBots();
    } else {
      const result = await res.json();
      alert("Erro ao eliminar o chatbot: " + (result.error || result.erro || res.statusText));
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
          ${bots.map(bot => `
            <tr data-chatbot-id="${bot.chatbot_id}">
              <td>${bot.nome || "-"}</td>
              <td>${bot.descricao || "-"}</td>
              <td>${formatarData(bot.data_criacao)}</td>
              <td>
                <span class="estado-indicador ${isAtivo(bot.chatbot_id) ? "ativo" : "inativo"}">
                  ${isAtivo(bot.chatbot_id) ? "Ativo" : "Não Publicado"}
                </span>
              </td>
              <td>
                <span class="fonte-indicador">${obterNomeFonte(bot.fonte)}</span>
              </td>
              <td class="cor">
                <span class="cor-bot-preview" style="background:${bot.cor || '#d4af37'}"></span>
              </td>
              <td class="icone">
                <img src="${bot.icon_path || '/static/images/chatbot-icon.png'}" alt="Ícone do Bot" style="width:24px; height:24px; border-radius:4px; object-fit:cover;">
              </td>
              <td>
                <button class="btn-ativo" onclick="tornarBotAtivo(${bot.chatbot_id}, this)">
                  ${isAtivo(bot.chatbot_id) ? "Ativo" : "Tornar Ativo"}
                </button>
                <button class="btn-editar" onclick="abrirModalAtualizar(${bot.chatbot_id})">Atualizar</button>
                <button class="btn-categorias" onclick="abrirModalCategorias(${bot.chatbot_id})">Categorias</button>
                <button class="btn-eliminar" onclick="abrirModalEliminarBot(${bot.chatbot_id})">Eliminar</button>
                <button class="btn-adicionar-faq" onclick="abrirModalAdicionarFAQ(${bot.chatbot_id})">Ad+</button>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  } catch (e) {
    container.innerHTML = `<p style="color:red;">Erro ao carregar bots: ${e.message}</p>`;
  }
}

function aplicarFiltrosBots(bots) {
  const nomeFiltro = document.getElementById("filtroNomeBot")?.value?.trim().toLowerCase() || "";
  const estadoFiltro = document.getElementById("filtroEstadoBot")?.value || "todos";
  const dataFiltro = document.getElementById("filtroDataCriacaoBot")?.value || "";

  return bots.filter(bot => {
    if (nomeFiltro && !(bot.nome || "").toLowerCase().includes(nomeFiltro)) return false;
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
  return data.toLocaleDateString('pt-PT');
}

function obterNomeFonte(fonte) {
  if (fonte === "faq") return "Baseado em Regras (FAQ)";
  if (fonte === "faiss") return "Só FAISS";
  if (fonte === "faq+raga") return "FAQ + fallback RAG";
  return fonte;
}

function isAtivo(chatbot_id) {
  return String(localStorage.getItem("chatbotAtivo")) === String(chatbot_id);
}

window.tornarBotAtivo = function(chatbot_id, btn) {
  localStorage.setItem("chatbotAtivo", chatbot_id);
  carregarTabelaBots();
};

document.addEventListener("DOMContentLoaded", function () {
  const novoBotForm = document.getElementById("novoBotForm");
  if (novoBotForm) {
    novoBotForm.onsubmit = async function(e) {
      e.preventDefault();
      const nome = novoBotForm.elements["nome"].value.trim();
      const descricao = novoBotForm.elements["descricao"].value.trim();
      const mensagem_sem_resposta = novoBotForm.elements["mensagem_sem_resposta"].value.trim();
      const cor = novoBotForm.elements["cor"].value.trim();
      if (!nome) {
        alert("Nome obrigatório");
        return;
      }
      const body = { nome, descricao, mensagem_sem_resposta, cor };
      try {
        const res = await fetch(`/chatbots`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });
        if (res.ok) {
          window.fecharModalNovoBot();
          carregarTabelaBots();
        } else {
          const result = await res.json().catch(() => ({}));
          alert("Erro ao criar chatbot: " + (result.error || result.erro || res.statusText));
        }
      } catch (err) {
        alert("Erro ao criar chatbot: " + err.message);
      }
    };
  }

  const editarForm = document.getElementById("editarChatbotForm");
  if (editarForm) {
    editarForm.onsubmit = async function(e) {
      e.preventDefault();
      const chatbot_id = this.getAttribute("data-edit-id");
      const nome = document.getElementById("editarNomeChatbot").value.trim();
      const descricao = document.getElementById("editarDescricaoChatbot").value.trim();
      const fonte = document.getElementById("editarFonteResposta").value;
      const cor = document.getElementById("editarCorChatbot").value.trim();
      const mensagem_sem_resposta = document.getElementById("editarMensagemSemResposta").value.trim();
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
      if (iconFile) formData.append("icon", iconFile);

      try {
        const res = await fetch(`/chatbots/${chatbot_id}`, {
          method: "PUT",
          body: formData
        });
        await atualizarCategoriasDoChatbot(chatbot_id);
        if (res.ok) {
          localStorage.setItem(`fonteSelecionada_bot${chatbot_id}`, fonte);
          window.fecharModalEditarChatbot();
          carregarTabelaBots();
        } else {
          const result = await res.json().catch(() => ({}));
          alert("Erro ao atualizar chatbot: " + (result.error || result.erro || res.statusText));
        }
      } catch (err) {
        alert("Erro ao atualizar chatbot: " + err.message);
      }
    };
  }

  const btnSim = document.getElementById('btnConfirmarEliminarBot');
  const btnNao = document.getElementById('btnCancelarEliminarBot');
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

  ["filtroNomeBot", "filtroEstadoBot", "filtroDataCriacaoBot"].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", carregarTabelaBots);
      el.addEventListener("change", carregarTabelaBots);
    }
  });

  const iconInput = document.getElementById("editarIconChatbot");
  if (iconInput) {
    iconInput.onchange = function(e) {
      const file = e.target.files[0];
      const preview = document.getElementById("previewIcon");
      if (file && file.type.startsWith('image/')) {
        preview.src = URL.createObjectURL(file);
        preview.style.display = "block";
      } else {
        preview.src = "/static/images/chatbot-icon.png";
        preview.style.display = "none";
        alert("Por favor, selecione um arquivo de imagem válido.");
        iconInput.value = "";
      }
    };
  }
});

window.abrirModalAtualizar = async function(chatbot_id) {
  try {
    const res = await fetch(`/chatbots`);
    const bots = await res.json();
    const bot = bots.find(b => String(b.chatbot_id) === String(chatbot_id));
    if (!bot) {
      alert("Chatbot não encontrado!");
      return;
    }
    document.getElementById("editarNomeChatbot").value = bot.nome || "";
    document.getElementById("editarDescricaoChatbot").value = bot.descricao || "";
    document.getElementById("editarDataCriacao").value = bot.data_criacao ? new Date(bot.data_criacao).toLocaleDateString('pt-PT') : "";
    document.getElementById("editarFonteResposta").value = bot.fonte || "faq";
    document.getElementById("editarCorChatbot").value = bot.cor || "#d4af37";
    document.getElementById("editarMensagemSemResposta").value = bot.mensagem_sem_resposta || "";
    document.getElementById("previewIcon").src = bot.icon_path || "/static/images/chatbot-icon.png";
    document.getElementById("previewIcon").style.display = bot.icon_path ? "block" : "none";
    document.getElementById("editarChatbotForm").setAttribute("data-edit-id", chatbot_id);

    await mostrarModalEditarChatbot(chatbot_id);
    document.getElementById("modalEditarChatbot").style.display = "flex";
  } catch (e) {
    alert("Erro ao carregar dados do chatbot: " + e.message);
  }
};

async function mostrarModalEditarChatbot(chatbot_id) {
  const catDiv = document.getElementById("editarCategoriasChatbot");
  if (!catDiv) return;

  try {
    const categoriasAssociadas = await fetch(`/chatbots/${chatbot_id}/categorias`).then(r => r.json());
    if (categoriasAssociadas.length === 0) {
      catDiv.innerHTML = `<span style="color:#888;">Nenhuma categoria associada a este chatbot.</span>`;
    } else {
      catDiv.innerHTML = categoriasAssociadas.map(cat => `
        <label style="display:flex;align-items:center;gap:4px;">
          <input type="checkbox" name="categorias[]" value="${cat.categoria_id}" checked>
          ${cat.nome}
        </label>
      `).join("");
    }
  } catch (err) {
    catDiv.innerHTML = `<span style="color:red;">Erro ao carregar categorias: ${err.message}</span>`;
  }
}

async function atualizarCategoriasDoChatbot(chatbot_id) {
  const catDiv = document.getElementById("editarCategoriasChatbot");
  if (!catDiv) return;

  try {
    const checks = Array.from(catDiv.querySelectorAll("input[type=checkbox]"));
    const selecionadas = checks.filter(cb => cb.checked).map(cb => parseInt(cb.value));

    const associadasResp = await fetch(`/chatbots/${chatbot_id}/categorias`);
    const associadas = await associadasResp.json();
    const associadasIds = associadas.map(c => c.categoria_id);

    const toAdd = selecionadas.filter(id => !associadasIds.includes(id));
    const toRemove = associadasIds.filter(id => !selecionadas.includes(id));

    for (const catId of toAdd) {
      await fetch(`/chatbots/${chatbot_id}/categorias`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ categoria_id: catId })
      });
    }
    for (const catId of toRemove) {
      await fetch(`/chatbots/${chatbot_id}/categorias/${catId}`, { method: "DELETE" });
    }
  } catch (err) {
    alert("Erro ao atualizar categorias: " + err.message);
  }
}

window.abrirModalAdicionarFAQ = async function(chatbot_id) {
  const modal = document.getElementById("modalAdicionarFAQ");
  if (!modal) return;
  modal.setAttribute("data-chatbot-id", chatbot_id);
  document.getElementById("faqChatbotId").value = chatbot_id;
  document.getElementById("docxChatbotId").value = chatbot_id;
  document.getElementById("pdfChatbotId").value = chatbot_id;
  await atualizarCategoriasFAQForm(chatbot_id);
  modal.style.display = "flex";
  document.getElementById("mensagemFAQ").textContent = "";
};

async function atualizarCategoriasFAQForm(chatbot_id) {
  const select = document.getElementById("faqCategoriaSelect");
  if (!select) return;
  select.innerHTML = '<option value="">Escolha a categoria</option>';

  try {
    if (!chatbot_id) return;
    const cats = await fetch(`/chatbots/${chatbot_id}/categorias`).then(r => r.json());
    cats.forEach(cat => {
      const opt = document.createElement("option");
      opt.value = cat.categoria_id;
      opt.textContent = cat.nome;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error("Erro ao carregar categorias para FAQ:", err);
  }
}

document.getElementById("formAdicionarFAQ").onsubmit = async function(e) {
  e.preventDefault();
  const chatbot_id = document.getElementById("faqChatbotId").value;
  const designacao = this.elements["designacao"].value.trim();
  const pergunta = this.elements["pergunta"].value.trim();
  const resposta = this.elements["resposta"].value.trim();
  const categoria_id = this.elements["categoria_id"].value;
  const idioma = this.elements["idioma"].value;
  const links_documentos = this.elements["links_documentos"].value.trim();
  const relacionadas = this.elements["relacionadas"].value.trim();

  if (!designacao || !pergunta || !resposta || !categoria_id || !idioma) {
    document.getElementById("mensagemFAQ").textContent = "Preencha todos os campos obrigatórios!";
    document.getElementById("mensagemFAQ").style.color = "red";
    return;
  }

  const body = { chatbot_id, designacao, pergunta, resposta, categoria_id, idioma, links_documentos, relacionadas };
  try {
    const res = await fetch("/faqs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const result = await res.json();
    if (res.ok) {
      document.getElementById("mensagemFAQ").textContent = "FAQ adicionada com sucesso!";
      document.getElementById("mensagemFAQ").style.color = "green";
      this.reset();
      setTimeout(() => {
        window.fecharModalAdicionarFAQ();
        carregarTabelaBots();
      }, 1000);
    } else {
      document.getElementById("mensagemFAQ").textContent = "Erro: " + (result.error || result.erro);
      document.getElementById("mensagemFAQ").style.color = "red";
    }
  } catch (err) {
    document.getElementById("mensagemFAQ").textContent = "Erro ao comunicar com o servidor: " + err.message;
    document.getElementById("mensagemFAQ").style.color = "red";
  }
};

document.getElementById("formUploadDocxFAQ").onsubmit = async function(e) {
  e.preventDefault();
  const chatbot_id = document.getElementById("docxChatbotId").value;
  const formData = new FormData(this);
  formData.append("chatbot_id", chatbot_id);

  try {
    const res = await fetch("/upload-faq-docx", {
      method: "POST",
      body: formData
    });
    const result = await res.json();
    if (res.ok) {
      document.querySelector("#formUploadDocxFAQ .uploadStatus").textContent = "Upload bem-sucedido!";
      document.querySelector("#formUploadDocxFAQ .uploadStatus").style.color = "green";
      this.reset();
    } else {
      document.querySelector("#formUploadDocxFAQ .uploadStatus").textContent = "Erro: " + (result.error || result.erro);
      document.querySelector("#formUploadDocxFAQ .uploadStatus").style.color = "red";
    }
  } catch (err) {
    document.querySelector("#formUploadDocxFAQ .uploadStatus").textContent = "Erro ao enviar: " + err.message;
    document.querySelector("#formUploadDocxFAQ .uploadStatus").style.color = "red";
  }
};

document.getElementById("formUploadPDFFAQ").onsubmit = async function(e) {
  e.preventDefault();
  const chatbot_id = document.getElementById("pdfChatbotId").value;
  const formData = new FormData(this);
  formData.append("chatbot_id", chatbot_id);

  try {
    const res = await fetch("/upload-pdf", {
      method: "POST",
      body: formData
    });
    const result = await res.json();
    if (res.ok) {
      document.querySelector("#formUploadPDFFAQ .uploadStatusPDF").textContent = "Upload bem-sucedido!";
      document.querySelector("#formUploadPDFFAQ .uploadStatusPDF").style.color = "green";
      this.reset();
    } else {
      document.querySelector("#formUploadPDFFAQ .uploadStatusPDF").textContent = "Erro: " + (result.error || result.erro);
      document.querySelector("#formUploadPDFFAQ .uploadStatusPDF").style.color = "red";
    }
  } catch (err) {
    document.querySelector("#formUploadPDFFAQ .uploadStatusPDF").textContent = "Erro ao enviar: " + err.message;
    document.querySelector("#formUploadPDFFAQ .uploadStatusPDF").style.color = "red";
  }
};

window.fecharModalAdicionarFAQ = function() {
  const modal = document.getElementById("modalAdicionarFAQ");
  if (modal) modal.style.display = "none";
};

window.fecharModalEditarChatbot = function() {
  const modal = document.getElementById("modalEditarChatbot");
  if (modal) modal.style.display = "none";
  document.getElementById("previewIcon").style.display = "none";
};

window.fecharModalNovoBot = function() {
  const modal = document.getElementById("modalNovoBot");
  if (modal) modal.style.display = "none";
};