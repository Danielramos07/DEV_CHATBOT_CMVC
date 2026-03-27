document.addEventListener("DOMContentLoaded", async () => {
  const chatbotId = localStorage.getItem("chatbotSelecionado");

  // Sync global active chatbot from server (avoid stale localStorage across admins).
  try {
    const res = await fetch("/chatbots");
    const bots = await res.json();
    if (Array.isArray(bots)) {
      const activeBot = bots.find((b) => !!b.ativo);
      if (activeBot && activeBot.chatbot_id != null) {
        localStorage.setItem("chatbotAtivo", String(activeBot.chatbot_id));
        window.chatbotAtivo = parseInt(activeBot.chatbot_id);
      }
    }
  } catch (e) {}

  if (chatbotId) {
    window.chatbotSelecionado = parseInt(chatbotId);
    const fonte =
      localStorage.getItem(`fonteSelecionada_bot${chatbotId}`) || "faq";
    window.fonteSelecionada = fonte;

    const dropdown = document
      .querySelector(`.bot-item[data-chatbot-id="${chatbotId}"]`)
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

  if (
    window.location.pathname.includes("respostas.html") &&
    typeof mostrarRespostas === "function"
  ) {
    mostrarRespostas();
  }

  if (
    window.location.pathname.includes("recursos.html") &&
    chatbotId &&
    typeof mostrarRespostas === "function"
  ) {
    mostrarRespostas();
  }
});
