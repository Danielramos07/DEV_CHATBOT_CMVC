async function carregarBots() {
  const container = document.getElementById("botsTabelaContainer");
  if (!container) return;
  container.innerHTML = "<p>A carregar bots...</p>";
  try {
    const res = await fetch("/chatbots");
    const bots = await res.json();
    if (!Array.isArray(bots) || bots.length === 0) {
      container.innerHTML = "<p>Nenhum bot encontrado.</p>";
      return;
    }

    // Sync global active chatbot from server (avoid stale localStorage across admins).
    try {
      const activeBot = bots.find((b) => !!b.ativo);
      if (activeBot && activeBot.chatbot_id != null) {
        localStorage.setItem("chatbotAtivo", String(activeBot.chatbot_id));
        window.chatbotAtivo = parseInt(activeBot.chatbot_id);
      }
    } catch (e) {}

    container.innerHTML = bots.map((bot) => criarBotHTML(bot, bots)).join("");
    if (typeof adicionarListenersFormulariosFAQ === "function")
      adicionarListenersFormulariosFAQ(bots);
    if (typeof adicionarListenersUploadDocx === "function")
      adicionarListenersUploadDocx(bots);
  } catch (e) {
    container.innerHTML = `<p style="color:red;">Erro ao carregar bots: ${e.message}</p>`;
  }
}

function adicionarCampoLink(btnOrContainer) {
  const container =
    btnOrContainer
      .closest?.(".links-docs-group")
      ?.querySelector(".links-docs-container") ||
    btnOrContainer.querySelector?.(".links-docs-container") ||
    null;
  if (!container) return;

  const row = document.createElement("div");
  row.className = "link-doc-row";

  const input = document.createElement("input");
  input.type = "url";
  input.name = "links_documentos[]";
  input.className = "link-doc-input";
  input.placeholder = "https://exemplo.com/documento.pdf";

  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.className = "btn-remover-link";
  removeBtn.textContent = "×";
  removeBtn.onclick = () => removerCampoLink(removeBtn);

  row.appendChild(input);
  row.appendChild(removeBtn);
  container.appendChild(row);
}

function removerCampoLink(btn) {
  const row = btn.closest(".link-doc-row");
  const container = btn.closest(".links-docs-container");
  if (!row || !container) return;
  const rows = container.querySelectorAll(".link-doc-row");
  if (rows.length > 1) {
    row.remove();
  } else {
    const input = row.querySelector("input");
    if (input) input.value = "";
  }
}

function carregarFAQsRelacionadas(chatbotId) {
  const selectId = `#faqRelacionadasSelect-${chatbotId}`;
  const $select = $(selectId);

  if (!$select.length) return;

  fetch(`/faqs/chatbot/${chatbotId}`)
    .then((resp) => resp.json())
    .then((data) => {
      if ($select.hasClass("select2-hidden-accessible")) {
        $select.select2("destroy");
      }

      $select.empty();

      data.forEach((faq) => {
        // Mostrar identificador prioritário; se não existir, usar pergunta truncada
        const pergunta = faq.pergunta || `FAQ ${faq.faq_id}`;
        const label = (faq.identificador || "").trim();
        const truncatedPergunta =
          pergunta.length > 60 ? pergunta.substring(0, 60) + "..." : pergunta;
        const option = new Option(
          label || truncatedPergunta,
          faq.faq_id,
          false,
          false
        );
        option.title = label ? `${label} — ${pergunta}` : pergunta; // Mostrar info completa no hover
        $select.append(option);
      });

      const $modal = $select
        .closest(".bot-dropdown")
        .closest(".bot-wrapper")
        .find(".bot-dropdown");
      const dropdownParent = $modal.length ? $modal : $("body");

      $select.select2({
        placeholder: "Escolha uma ou mais FAQs relacionadas",
        width: "100%",
        allowClear: true,
        dropdownParent: dropdownParent,
      });
    })
    .catch((err) => {
      console.error("Erro ao carregar FAQs relacionadas:", err);
    });
}

function gerarOptionsChatbotSelect(allBots) {
  let options = `<option value="" disabled selected hidden>Escolha o chatbot</option>`;
  options += `<option value="todos">Todos os Chatbots</option>`;
  for (const bot of allBots) {
    options += `<option value="${bot.chatbot_id}">${bot.nome}</option>`;
  }
  return options;
}

function gerarOptionsIdiomaSelect() {
  return `
    <select name="idioma" required>
      <option value="pt" selected>Português</option>
      <option value="en">Inglês</option>
    </select>
  `;
}

function criarBotHTML(bot, allBots) {
  const dataCriacao = bot.data_criacao
    ? new Date(bot.data_criacao).toLocaleDateString("pt-PT", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      })
    : "-";
  const optionsHtml = gerarOptionsChatbotSelect(allBots);
  const idiomaSelectHtml = gerarOptionsIdiomaSelect();
  const isActive = !!bot.ativo;
  return `
    <div class="bot-wrapper">
      <div class="bot-item nao-publicado" data-chatbot-id="${bot.chatbot_id}" onclick="toggleBotDropdown(this)">
        <div>
          ${bot.nome}
          <span class="status">
            Estado: Não Publicado - Município • ${dataCriacao}
          </span>
          <span class="ativo-label" style="display: ${isActive ? "inline" : "none"}; margin-left: 10px; color: #3c763d; font-weight: bold;">
            • Chatbot Ativo
          </span>
        </div>
        <span class="dropdown-icon">▼</span>
      </div>
      <div class="bot-dropdown" style="display: none;">
        <button class="bot-ativo-btn ${isActive ? "ativo" : ""}" onclick="definirAtivo(event, ${bot.chatbot_id})">${isActive ? "Ativo" : "Ficar Ativo"}</button>
        <button class="bot-editar-btn" onclick="event.stopPropagation(); abrirModalEditarChatbot(${bot.chatbot_id});" style="margin-left: 10px;">Atualizar</button>
        <button class="bot-eliminar-btn" onclick="event.stopPropagation(); abrirModalEliminarBot(${bot.chatbot_id});" style="margin-left: 10px; background: #ea4d4d; color: #fff;">Eliminar</button>
        <h3>Escolha a fonte para as respostas do chatbot</h3>
        <div class="resources">
          <div class="card" data-fonte="faq" onclick="selecionarFonte('faq', this.closest('.bot-dropdown'))">
            <h4>Baseado em Regras (FAQ)</h4>
            <p>Responde com base nas perguntas frequentes registadas.</p>
          </div>
          <div class="card" data-fonte="faiss" onclick="selecionarFonte('faiss', this.closest('.bot-dropdown'))">
            <h4>Só FAISS</h4>
            <p>Respostas aproximadas com base vetorial.</p>
          </div>
          <div class="card" data-fonte="faq+raga" onclick="selecionarFonte('faq+raga', this.closest('.bot-dropdown'))">
            <h4>FAQ + fallback RAG</h4>
            <p>Tenta responder com regras e usa RAG se falhar.</p>
          </div>
        </div>
        <hr class="linha-separadora">
        <h3>Gestão de FAQs</h3>
        <button id="faqAddBtn-${bot.chatbot_id}" class="btn-faq-add" onclick="mostrarFormulario()">Adicionar FAQ</button>
        <div id="faqContainer" style="display: none; margin-top: 10px;">
          <form id="faqForm-${bot.chatbot_id}" class="faqForm">
            <select name="chatbot_id" required>
              ${optionsHtml}
            </select>
            ${idiomaSelectHtml}
            <input type="text" name="identificador" placeholder="Identificador (ex: APO-AIC-AM)" maxlength="120">
            <input type="text" name="designacao" placeholder="Designação" required>
            <input type="text" name="pergunta" placeholder="Pergunta" required>
            <textarea name="serve_text" placeholder="Serve / A quem se destina..."></textarea>
            <textarea name="resposta" placeholder="Resposta" required></textarea>
            <select name="categoria_id" required>
              <option value="">Escolha a categoria</option>
              <option value="1">Educação</option>
              <option value="2">Ação Social</option>
              <option value="3">Habitação</option>
              <option value="4">Cultura</option>
              <option value="5">Desporto</option>
              <option value="6">Ambiente</option>
            </select>
            <div class="links-docs-group">
              <label style="display:block; margin-bottom:4px;">Links de documentos</label>
              <div class="links-docs-container">
                <div class="link-doc-row">
                  <input type="url" name="links_documentos[]" class="link-doc-input" placeholder="https://exemplo.com/documento.pdf">
                  <button type="button" class="btn-remover-link" onclick="removerCampoLink(this)">Remover</button>
                </div>
              </div>
              <button type="button" class="btn-adicionar-link" onclick="adicionarCampoLink(this)">+ Adicionar link</button>
              <small class="form-text">Um link por campo. Não é preciso vírgulas.</small>
            </div>
            <label style="display:block; margin-top:6px; font-size: 0.9rem;">
  FAQs relacionadas
</label>
<select id="faqRelacionadasSelect-${bot.chatbot_id}"
        name="relacionadas[]"
        class="faq-relacionadas-select"
        multiple
        style="width: 100%;">
</select>
<small style="font-size: 0.8rem; color: #666;">
  Pode selecionar várias FAQs e escrever para pesquisar.
</small>
            <button type="submit">Adicionar FAQ</button>
            <div id="mensagemFAQ"></div>
          </form>
          <div>
            <label>Ou carregar ficheiro .docx/.odt</label>
            <form id="uploadForm-${bot.chatbot_id}" class="uploadForm" enctype="multipart/form-data">
              <select name="chatbot_id" required>
                ${optionsHtml}
              </select>
              <input type="file" name="file" accept=".docx,.odt" required>
              <button type="submit">Adicionar Documento</button>
              <div class="uploadStatus"></div>
            </form>
          </div>
        </div>
        <div id="faqTabelaBot-${bot.chatbot_id}"></div>
      </div>
    </div>
  `;
}

function toggleBotDropdown(botItem) {
  const chatbotId = parseInt(botItem.getAttribute("data-chatbot-id"));
  const dropdown = botItem.parentElement.querySelector(".bot-dropdown");
  const isCurrentlyOpen = botItem.classList.contains("expanded");

  document
    .querySelectorAll(".bot-dropdown")
    .forEach((el) => (el.style.display = "none"));
  document
    .querySelectorAll(".bot-item")
    .forEach((el) => el.classList.remove("expanded"));

  if (isCurrentlyOpen) {
    window.chatbotSelecionado = null;
    localStorage.removeItem("chatbotSelecionado");
  } else {
    botItem.classList.add("expanded");
    dropdown.style.display = "block";

    // ← AQUI: carregar FAQs relacionadas para este bot
    carregarFAQsRelacionadas(chatbotId);

    requestAnimationFrame(() => {
      if (typeof carregarChatbots === "function") {
        carregarChatbots();
      }
    });

    window.chatbotSelecionado = chatbotId;
    localStorage.setItem("chatbotSelecionado", chatbotId);
    const fonteSalva =
      localStorage.getItem(`fonteSelecionada_bot${chatbotId}`) || "faq";
    selecionarFonte(fonteSalva, dropdown);
    if (typeof carregarTabelaFAQs === "function") {
      carregarTabelaFAQs(chatbotId, true);
    }
    const botWrapper = botItem.closest(".bot-wrapper");
    const ativoBtn = botWrapper.querySelector(".bot-ativo-btn");
    if (ativoBtn) ativoBtn.style.display = "inline-block";
  }
}

function selecionarFonte(fonte, dropdown = null) {
  window.fonteSelecionada = fonte;
  if (window.chatbotSelecionado) {
    localStorage.setItem(
      `fonteSelecionada_bot${window.chatbotSelecionado}`,
      fonte
    );
  }
  if (!dropdown) {
    dropdown = document
      .querySelector(
        `.bot-item[data-chatbot-id="${window.chatbotSelecionado}"]`
      )
      ?.parentElement?.querySelector(".bot-dropdown");
  }
  if (!dropdown) {
    return;
  }
  dropdown.querySelectorAll(".card").forEach((card) => {
    card.classList.toggle("active", card.dataset.fonte === fonte);
  });
}

function mostrarFormulario() {
  const dropdownVisivel = document.querySelector(
    ".bot-dropdown[style*='block']"
  );
  if (!dropdownVisivel) return;
  const container = dropdownVisivel.querySelector("#faqContainer");
  if (container) {
    container.style.display =
      container.style.display === "none" ? "block" : "none";
  }
}

async function definirAtivo(event, chatbotId) {
  event.stopPropagation();
  localStorage.setItem("chatbotAtivo", chatbotId);
  window.chatbotAtivo = chatbotId;
  // Persist globally (server-side) so public users/new browsers inherit it.
  try {
    const r = await fetch(`/chatbots/${chatbotId}/active`, { method: "PUT" });
    if (!r.ok) {
      throw new Error("Falha ao ativar chatbot.");
    }
  } catch (e) {}
  document.querySelectorAll(".bot-ativo-btn").forEach((btn) => {
    btn.classList.remove("ativo");
    btn.textContent = "Ficar Ativo";
  });
  const botAtivoBtn = event.target
    .closest(".bot-dropdown")
    .querySelector(".bot-ativo-btn");
  if (botAtivoBtn) {
    botAtivoBtn.classList.add("ativo");
    botAtivoBtn.textContent = "Ativo";
  }
  const indicador = document.getElementById("indicadorAtivo");
  if (indicador) {
    indicador.style.display = "block";
    indicador.textContent = "";
  }
  document
    .querySelectorAll(".ativo-label")
    .forEach((el) => (el.style.display = "none"));
  const label = document.querySelector(
    `.bot-item[data-chatbot-id="${chatbotId}"] .ativo-label`
  );
  if (label) label.style.display = "inline";
  const fonte =
    localStorage.getItem(`fonteSelecionada_bot${chatbotId}`) || "faq";
  window.fonteSelecionada = fonte;
  const dropdown = document
    .querySelector(`.bot-item[data-chatbot-id="${chatbotId}"]`)
    ?.parentElement?.querySelector(".bot-dropdown");
  if (dropdown) {
    selecionarFonte(fonte, dropdown);
  }
  if (typeof carregarTabelaFAQs === "function") {
    carregarTabelaFAQs(chatbotId, true);
  }
  if (document.getElementById("listaFAQs")) {
    if (typeof carregarFAQsDoBotSelecionado === "function")
      carregarFAQsDoBotSelecionado();
  }

  // Sync chat UI/avatar immediately when active bot changes
  try {
    if (typeof atualizarNomeChatHeader === "function") {
      await atualizarNomeChatHeader();
    }
    // Forçar refresh da conversa para aplicar nome/mensagem do chatbot ativo
    if (typeof reiniciarConversa === "function") {
      try {
        // reset greeting playback (chat.js)
        if (typeof hasPlayedGreeting !== "undefined") {
          hasPlayedGreeting = false;
        }
      } catch (e) {}
      await reiniciarConversa();
    }
  } catch (e) {}
}

window.carregarBots = carregarBots;
window.toggleBotDropdown = toggleBotDropdown;
window.selecionarFonte = selecionarFonte;
window.definirAtivo = definirAtivo;
window.mostrarFormulario = mostrarFormulario;
