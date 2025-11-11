document.addEventListener("DOMContentLoaded", () => {
  const publicarBtn = document.getElementById("publicarBtn");
  if (publicarBtn) {
    publicarBtn.addEventListener("click", () => {
      const botItem = document.querySelector(".bot-item.expanded");
      if (!botItem) return;

      const statusSpan = botItem.querySelector(".status");
      const dataAtual = new Date().toLocaleDateString('pt-PT', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      });

      statusSpan.textContent = `Estado: Publicado - Município • ${dataAtual}`;
      botItem.classList.remove("nao-publicado");
    });
  }

  const chatbotId = localStorage.getItem("chatbotSelecionado");
  const chatbotAtivo = localStorage.getItem("chatbotAtivo");

  if (chatbotAtivo) {
    window.chatbotAtivo = parseInt(chatbotAtivo);
    console.log("✅ Inicializando com chatbotAtivo:", chatbotAtivo);

    const botAtivoBtn = document.querySelector(`.bot-ativo-btn[onclick*="${chatbotAtivo}"]`);
    if (botAtivoBtn) {
      botAtivoBtn.classList.add("ativo");
      botAtivoBtn.textContent = "Ativo"; 
    }

    document.querySelectorAll(".bot-ativo-btn").forEach(btn => {
      if (btn !== botAtivoBtn) btn.textContent = "Ficar Ativo";
    });

    const indicador = document.getElementById("indicadorAtivo");
    if (indicador) {
      indicador.style.display = "block";
      indicador.textContent = "";
    }

    const ativoLabel = document.querySelector(`.bot-item[data-chatbot-id="${chatbotAtivo}"] .ativo-label`);
    if (ativoLabel) ativoLabel.style.display = "inline";
  }

  if (chatbotId) {
    window.chatbotSelecionado = parseInt(chatbotId);
    const fonte = localStorage.getItem(`fonteSelecionada_bot${chatbotId}`) || "faq";
    window.fonteSelecionada = fonte;

    const dropdown = document.querySelector(`.bot-item[data-chatbot-id="${chatbotId}"]`)
      ?.parentElement?.querySelector(".bot-dropdown");
    if (dropdown) {
      selecionarFonte(fonte, dropdown);
    }
  } else {
    window.chatbotSelecionado = null;
    window.fonteSelecionada = "faq";
  }

  const panel = document.querySelector(".panel");
  if (panel) {
    panel.style.display = "flex";
    panel.style.overflow = "visible";
  }

  if (typeof carregarChatbots === "function") {
    carregarChatbots();
  }

  if (window.location.pathname.includes("respostas.html") && typeof mostrarRespostas === "function") {
    mostrarRespostas();
  }
  
  if (window.location.pathname.includes("recursos.html") && chatbotId && typeof mostrarRespostas === "function") {
    mostrarRespostas();
  }
});